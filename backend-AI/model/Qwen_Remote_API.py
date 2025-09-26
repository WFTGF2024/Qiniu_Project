# llm_api_chat_only.py
# -*- coding: utf-8 -*-
"""
Flask 封装 ModelScope(OpenAI兼容) LLM 功能：
只包含：
- /api/chat       : 非流式对话
- /api/chat/stream: 流式对话
"""

import json
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from openai import OpenAI

# ---------------- 固定配置 ----------------
MODEL_BASE_URL = "https://api-inference.modelscope.cn/v1"
MODEL_API_KEY  = "ms-fb4f7a45-0e56-4d01-a136-013064aece63"  # 直接写死在代码中
MODEL_ID       = "Qwen/Qwen3-Coder-480B-A35B-Instruct"

# 初始化 Flask 与 OpenAI 客户端
app = Flask(__name__)
CORS(app)

client = OpenAI(base_url=MODEL_BASE_URL, api_key=MODEL_API_KEY)

# ---------------- 健康检查 ----------------
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "model": MODEL_ID})

# ---------------- Chat（非流式） ----------------
@app.route("/api/chat", methods=["POST"])
def chat():
    """
    输入 JSON:
    {
      "messages": [{"role":"system","content":"You are..."},{"role":"user","content":"你好"}],
      "model": "可选"
    }
    """
    data = request.get_json(force=True) or {}
    messages = data.get("messages")
    model = data.get("model", MODEL_ID)

    if not messages:
        return jsonify({"error": "messages 不能为空"}), 400

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            stream=False
        )
        return jsonify({
            "model": model,
            "content": resp.choices[0].message.content,
            "raw": resp.dict()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------------- Chat（流式） ----------------
@app.route("/api/chat/stream", methods=["POST"])
def chat_stream():
    """
    输入 JSON:
    {
      "messages": [{"role":"user","content":"请用一句话总结量子计算"}],
      "model": "可选"
    }
    """
    data = request.get_json(force=True) or {}
    messages = data.get("messages")
    model = data.get("model", MODEL_ID)

    if not messages:
        return jsonify({"error": "messages 不能为空"}), 400

    def generate():
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True
            )
            for chunk in resp:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield json.dumps({"delta": delta}, ensure_ascii=False) + "\n"
            yield json.dumps({"event": "done"}) + "\n"
        except Exception as e:
            yield json.dumps({"error": str(e)}) + "\n"

    return Response(generate(), mimetype="text/plain; charset=utf-8")

# ---------------- 启动 ----------------
if __name__ == "__main__":
    print(f"* Serving on http://0.0.0.0:8000")
    print(f"* Model base: {MODEL_BASE_URL}")
    print(f"* Model id  : {MODEL_ID}")
    app.run(host="0.0.0.0", port=7207, threaded=True)
