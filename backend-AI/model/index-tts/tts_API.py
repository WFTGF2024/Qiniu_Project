# -*- coding: utf-8 -*-
import os
import time
import tempfile
from flask import Flask,request, jsonify, send_file
from indextts.infer_v2 import IndexTTS2

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

# ============ Ĭ�ϲο���Ƶ·�� ============
DEFAULT_REFS = {
    "style1": "./default_refs/style1.wav",
    "style2": "./default_refs/style2.wav",
    "style3": "./default_refs/style3.wav"
}
DEFAULT_STYLE = "style1"  # Ĭ�Ϸ��


# ============ TTS Endpoint ============
@app.route("/synthesize", methods=["POST"])
def synthesize():
    text = None
    prompt_audio_path = None
    temp_files = []

    # ֻ֧�� multipart/form-data
    if not request.content_type or "multipart/form-data" not in request.content_type:
        return jsonify({"error": "Only multipart/form-data is supported"}), 400

    # ��ȡ�ı�
    text = request.form.get("text")
    if not text:
        return jsonify({"error": "Missing required parameter: text"}), 400

    # ��ȡ������
    style = request.form.get("style", DEFAULT_STYLE)
    if style not in DEFAULT_REFS:
        style = DEFAULT_STYLE

    # ����û��ϴ�����Ƶ�����û��ģ�������Ĭ�Ϸ�����Ƶ
    if "prompt_audio" in request.files:
        f = request.files["prompt_audio"]
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        f.save(tmp.name)
        prompt_audio_path = tmp.name
        temp_files.append(tmp.name)
    else:
        prompt_audio_path = DEFAULT_REFS[style]

    # ������ѡ����
    emo_control = int(request.form.get("emo_control_method", 0))
    emo_audio = None
    emo_weight = float(request.form.get("emo_weight", 0.65))
    emo_vec = None
    emo_text = None
    emo_random = False

    kwargs = dict(
        do_sample=True,
        temperature=float(request.form.get("temperature", 0.8)),
        top_p=float(request.form.get("top_p", 0.8)),
        top_k=int(request.form.get("top_k", 30)) or None,
        num_beams=int(request.form.get("num_beams", 3)),
        repetition_penalty=float(request.form.get("repetition_penalty", 10.0)),
        length_penalty=float(request.form.get("length_penalty", 0.0)),
        max_mel_tokens=int(request.form.get("max_mel_tokens", 1500)),
    )
    max_text_tokens_per_segment = int(request.form.get("max_text_tokens_per_segment", 120))

    # ���·��
    os.makedirs("outputs", exist_ok=True)
    output_path = os.path.join("outputs", f"tts_{int(time.time())}.wav")

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
