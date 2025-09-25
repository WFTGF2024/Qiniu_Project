# -*- coding: utf-8 -*-
import os
import time
from flask import Flask, request, jsonify, send_file
from indextts.infer_v2 import IndexTTS2
import tempfile

# ============ Model Initialization ============
MODEL_DIR = "./checkpoints"
REQUIRED_FILES = ["bpe.model", "gpt.pth", "config.yaml", "s2mel.pth", "wav2vec2bert_stats.pt"]

for f in REQUIRED_FILES:
    if not os.path.exists(os.path.join(MODEL_DIR, f)):
        raise FileNotFoundError(f"Missing model file {f}, please check {MODEL_DIR}")

tts = IndexTTS2(
    model_dir=MODEL_DIR,
    cfg_path=os.path.join(MODEL_DIR, "config.yaml"),
    use_fp16=True,
    use_deepspeed=False,
    use_cuda_kernel=False,
)

app = Flask(__name__)

# ============ TTS Endpoint ============
@app.route("/synthesize", methods=["POST"])
def synthesize():
    text = None
    prompt_audio_path = None
    temp_files = []

    # ���� multipart/form-data
    if request.content_type and "multipart/form-data" in request.content_type:
        text = request.form.get("text")
        if not text:
            return jsonify({"error": "Missing required parameter: text"}), 400

        if "prompt_audio" in request.files:
            f = request.files["prompt_audio"]
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            f.save(tmp.name)
            prompt_audio_path = tmp.name
            temp_files.append(tmp.name)

        # ������ѡ����
        emo_control = int(request.form.get("emo_control_method", 0))
        emo_audio = None
        emo_weight = float(request.form.get("emo_weight", 0.65))
        emo_vec = None
        emo_text = None
        emo_random = False

        kwargs = dict(
            do_sample=True,
            temperature=0.8,
            top_p=0.8,
            top_k=30,
            num_beams=3,
            repetition_penalty=10.0,
            length_penalty=0.0,
            max_mel_tokens=1500,
        )
        max_text_tokens_per_segment = 120

    else:
        # ���� application/json
        data = request.get_json(force=True)
        if not data or "text" not in data:
            return jsonify({"error": "Missing required parameter: text"}), 400

        text = data["text"]
        prompt_audio_path = data.get("prompt_audio")
        emo_control = int(data.get("emo_control_method", 0))
        emo_audio = data.get("emo_audio")
        emo_weight = float(data.get("emo_weight", 0.65))
        emo_vec = data.get("emo_vec")
        emo_text = data.get("emo_text") or None
        emo_random = bool(data.get("emo_random", False))

        kwargs = dict(
            do_sample=bool(data.get("do_sample", True)),
            temperature=float(data.get("temperature", 0.8)),
            top_p=float(data.get("top_p", 0.8)),
            top_k=int(data.get("top_k", 30)) or None,
            num_beams=int(data.get("num_beams", 3)),
            repetition_penalty=float(data.get("repetition_penalty", 10.0)),
            length_penalty=float(data.get("length_penalty", 0.0)),
            max_mel_tokens=int(data.get("max_mel_tokens", 1500)),
        )
        max_text_tokens_per_segment = int(data.get("max_text_tokens_per_segment", 120))

    # Output path
    os.makedirs("outputs", exist_ok=True)
    output_path = os.path.join("outputs", f"tts_{int(time.time())}.wav")

    # Emotion vector normalization
    if emo_control == 2 and emo_vec:
        emo_vec = tts.normalize_emo_vec(emo_vec, apply_bias=True)
    else:
        emo_vec = None

    # Run inference
    out = tts.infer(
        spk_audio_prompt=prompt_audio_path,
        text=text,
        output_path=output_path,
        emo_audio_prompt=emo_audio if emo_control == 1 else None,
        emo_alpha=emo_weight,
        emo_vector=emo_vec,
        use_emo_text=(emo_control == 3),
        emo_text=emo_text,
        use_random=emo_random,
        verbose=False,
        max_text_tokens_per_segment=max_text_tokens_per_segment,
        **kwargs,
    )

    # ������ʱ�ļ�
    for f in temp_files:
        try:
            os.remove(f)
        except:
            pass

    return send_file(out, mimetype="audio/wav")


# ============ Health Check ============
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7206)
