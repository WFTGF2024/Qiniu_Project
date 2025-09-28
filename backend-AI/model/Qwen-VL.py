# app.py
# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify, Response
from openai import OpenAI
import json

app = Flask(__name__)

# 初始化 ModelScope 客户端
client = OpenAI(
    base_url="https://api-inference.modelscope.cn/v1",
    api_key="ms-xxxxxxxx-xxxxxxxx",  # 替换成你的 ModelScope Token
)


@app.route("/describe_image", methods=["POST"])
def describe_image():
    """
    普通接口：一次性返回完整结果
    """
    data = request.get_json()
    text = data.get("text", "")
    image_url = data.get("image_url", "")

    response = client.chat.completions.create(
        model="Qwen/Qwen3-VL-235B-A22B-Instruct",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": text},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }
        ],
        stream=False,
    )

    result_text = response.choices[0].message.content
    return jsonify({"result": result_text})


@app.route("/describe_image_stream", methods=["POST"])
def describe_image_stream():
    """
    流式接口：逐步返回结果
    """

    def generate():
        data = request.get_json()
        text = data.get("text", "")
        image_url = data.get("image_url", "")

        response = client.chat.completions.create(
            model="Qwen/Qwen3-VL-235B-A22B-Instruct",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": text},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                }
            ],
            stream=True,
        )

        for chunk in response:
            delta = chunk.choices[0].delta.get("content", "")
            if delta:
                yield delta

    return Response(generate(), mimetype="text/plain")


if __name__ == "__main__":
    # 运行 Flask 服务
    app.run(host="0.0.0.0", port=7208, debug=True)
