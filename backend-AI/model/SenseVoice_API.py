from flask import Flask, request, Response, jsonify
from funasr import AutoModel
from funasr.utils.postprocess_utils import rich_transcription_postprocess
import json
from flask_cors import CORS

# 先创建 app
app = Flask(__name__)
# 然后启用 CORS
CORS(app)

# 初始化模型（只加载一次，避免每次请求都加载）
model_dir = "./SenseVoiceSmall"
model = AutoModel(
    model=model_dir,
    trust_remote_code=True,
    remote_code="./model.py",
    vad_model="fsmn-vad",
    vad_kwargs={"max_single_segment_time": 30000},
    device="cuda:0",
)


@app.route("/asr", methods=["POST"])
def asr_full():
    """
    整段识别接口
    输入：multipart/form-data 里传一个 'file'
    输出：JSON，包含识别结果
    """
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    audio_path = "/tmp/upload.wav"
    file.save(audio_path)

    res = model.generate(
        input=audio_path,
        cache={},
        language="auto",
        use_itn=True,
        batch_size_s=60,
        merge_vad=True,
        merge_length_s=15,
    )
    text = rich_transcription_postprocess(res[0]["text"])
    return jsonify({"text": text})


@app.route("/asr/stream", methods=["POST"])
def asr_stream():
    """
    流式识别接口
    输入：multipart/form-data 里传一个 'file'
    输出：流式返回 JSON 行
    """
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    audio_path = "/tmp/upload_stream.wav"
    file.save(audio_path)

    def generate_stream():
        res = model.generate(
            input=audio_path,
            cache={},
            language="auto",
            use_itn=True,
            batch_size_s=10,   # 更小的窗口，模拟流式
            merge_vad=True,
            merge_length_s=5,
        )
        for r in res:
            text = rich_transcription_postprocess(r["text"])
            yield json.dumps({"partial_text": text}, ensure_ascii=False) + "\n"

    return Response(generate_stream(), mimetype="application/json")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7205)
