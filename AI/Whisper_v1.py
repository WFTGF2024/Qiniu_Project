from flask import Flask, request, jsonify, Response
from faster_whisper import WhisperModel
import tempfile
import os

# 初始化模型（medium，fp16 适合 GPU）

model = WhisperModel("./faster-whisper-medium", device="cuda", compute_type="float16")

app = Flask(__name__)

# -------------------------
# 整段识别（同步模式）
# -------------------------
@app.route("/transcribe", methods=["POST"])
def transcribe():
    if "file" not in request.files:
        return jsonify({"error": "No audio file uploaded"}), 400

    file = request.files["file"]
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        file.save(tmp.name)
        segments, info = model.transcribe(tmp.name, beam_size=5)

    result = {
        "language": info.language,
        "text": " ".join([seg.text for seg in segments])
    }

    os.unlink(tmp.name)
    return jsonify(result)

# -------------------------
# 流式识别（Server-Sent Events）
# -------------------------
@app.route("/transcribe_stream", methods=["POST"])
def transcribe_stream():
    if "file" not in request.files:
        return jsonify({"error": "No audio file uploaded"}), 400

    file = request.files["file"]
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        file.save(tmp.name)

    def generate():
        segments, info = model.transcribe(tmp.name, beam_size=5)
        yield f"data: language={info.language}\n\n"
        for seg in segments:
            yield f"data: [{seg.start:.2f}s -> {seg.end:.2f}s] {seg.text}\n\n"

        os.unlink(tmp.name)

    return Response(generate(), mimetype="text/event-stream")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7205)
