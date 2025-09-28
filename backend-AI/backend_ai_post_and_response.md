这里详细地介绍API接口的调用示例以及对应的返回结果
# <font color="red">语音识别模块</font>
## Whisper_v1
暂不使用，cnn库冲突，后续调明白会使用，因为它是SOTA

## SenseVoice_v1
* `/asr`（非流式）


```bash
curl -X POST http://127.0.0.1:7205/asr ^
     -F "file=@test.wav"
```
```bash
{"text":"\u4f60\u597d\uff0c\u8fd9\u662f\u9ed8\u8ba4\u98ce\u683c\u7684\u6d4b\u8bd5\u3002"}
```

* `/asr/stream`（流式）
```bash
curl -N -X POST http://127.0.0.1:7205/asr/stream ^
     -F "file=@test.wav"
```
```
{"partial_text": "你好，这是默认风格的测试。"}
```

# <font color="red">LLM模块</font>
* `/health`
* `/api/chat`（非流式）
* `/api/chat/stream`（流式）

##  健康检查  `/health`

```bash
curl http://127.0.0.1:7207/health
```
```
{"model":"Qwen/Qwen3-Coder-480B-A35B-Instruct","status":"ok"}
```
## 非流式对话 `/api/chat`

### 最简单对话

```bash
curl -X POST http://127.0.0.1:7207/api/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"messages\":[{\"role\":\"user\",\"content\":\"你好，给我一句鸡汤\"}]}"
```
```
{"content":"\u4f60\u597d\uff01\u8fd9\u91cc\u6709\u4e00\u53e5\u6e29\u6696\u7684\u9e21\u6c64\u9001\u7ed9\u4f60\uff1a\n\n**\"\u6bcf\u4e00\u4e2a\u5e73\u51e1\u7684\u65e5\u5b50\uff0c\u90fd\u85cf\u7740\u4e0d\u5e73\u51e1\u7684\u53ef\u80fd\u3002\"**\n\n\u613f\u4f60\u4eca\u5929\u8fc7\u5f97\u5145\u5b9e\u7f8e\u597d\uff01\u2728","model":"Qwen/Qwen3-Coder-480B-A35B-Instruct","raw":{"choices":[{"delta":{"content":"","function_calls":null,"reasoning_content":"","role":null,"tool_calls":null},"finish_reason":"stop","index":0,"logprobs":null,"message":{"annotations":null,"audio":null,"content":"\u4f60\u597d\uff01\u8fd9\u91cc\u6709\u4e00\u53e5\u6e29\u6696\u7684\u9e21\u6c64\u9001\u7ed9\u4f60\uff1a\n\n**\"\u6bcf\u4e00\u4e2a\u5e73\u51e1\u7684\u65e5\u5b50\uff0c\u90fd\u85cf\u7740\u4e0d\u5e73\u51e1\u7684\u53ef\u80fd\u3002\"**\n\n\u613f\u4f60\u4eca\u5929\u8fc7\u5f97\u5145\u5b9e\u7f8e\u597d\uff01\u2728","function_call":null,"function_calls":null,"reasoning_content":"","refusal":null,"role":"assistant","tool_calls":null}}],"created":1758968053760,"id":"chatcmpl-47c483ec-ff8d-4fd1-ad1a-86dc36805546","model":"Qwen/Qwen3-Coder-480B-A35B-Instruct","object":"chat.completion","service_tier":null,"system_fingerprint":"","usage":{"completion_tokens":34,"completion_tokens_details":null,"prompt_tokens":13,"prompt_tokens_details":null,"total_tokens":47}}}
```
### 带 system 提示

```bash
curl -X POST http://127.0.0.1:7207/api/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"messages\":[{\"role\":\"system\",\"content\":\"你是一个精简的助手\"},{\"role\":\"user\",\"content\":\"请用一句话总结人工智能\"}]}"
```
```
{"content":"\u4eba\u5de5\u667a\u80fd\u662f\u8ba9\u673a\u5668\u6a21\u62df\u4eba\u7c7b\u667a\u80fd\u884c\u4e3a\u7684\u6280\u672f\u3002","model":"Qwen/Qwen3-Coder-480B-A35B-Instruct","raw":{"choices":[{"delta":{"content":"","function_calls":null,"reasoning_content":"","role":null,"tool_calls":null},"finish_reason":"stop","index":0,"logprobs":null,"message":{"annotations":null,"audio":null,"content":"\u4eba\u5de5\u667a\u80fd\u662f\u8ba9\u673a\u5668\u6a21\u62df\u4eba\u7c7b\u667a\u80fd\u884c\u4e3a\u7684\u6280\u672f\u3002","function_call":null,"function_calls":null,"reasoning_content":"","refusal":null,"role":"assistant","tool_calls":null}}],"created":1758968084004,"id":"chatcmpl-7f92ebbd-c078-4c52-b1bd-40fdfdabf65e","model":"Qwen/Qwen3-Coder-480B-A35B-Instruct","object":"chat.completion","service_tier":null,"system_fingerprint":"","usage":{"completion_tokens":10,"completion_tokens_details":null,"prompt_tokens":24,"prompt_tokens_details":null,"total_tokens":34}}}
```
### 指定模型

```bash
curl -X POST http://127.0.0.1:7207/api/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"model\":\"Qwen/Qwen3-Coder-480B-A35B-Instruct\",\"messages\":[{\"role\":\"user\",\"content\":\"Python 适合初学者吗？\"}]}"
```
```
{"content":"\u662f\u7684\uff0cPython \u975e\u5e38\u9002\u5408\u521d\u5b66\u8005\uff01\u4ee5\u4e0b\u662f\u4e3b\u8981\u539f\u56e0\uff1a\n\n## \ud83c\udfaf **\u8bed\u6cd5\u7b80\u6d01\u6613\u61c2**\n```python\n# Python \u4ee3\u7801\u793a\u4f8b\nprint(\"Hello, World!\")\nname = input(\"\u4f60\u7684\u540d\u5b57\uff1a\")\nprint(f\"\u4f60\u597d\uff0c{name}\uff01\")\n```\n\n## \ud83c\udf1f **Python \u7684\u4f18\u52bf**\n\n### 1. **\u8bed\u6cd5\u63a5\u8fd1\u81ea\u7136\u8bed\u8a00**\n- \u4ee3\u7801\u53ef\u8bfb\u6027\u5f3a\n- \u5b66\u4e60\u66f2\u7ebf\u5e73\u7f13\n- \u51cf\u5c11\u521d\u5b66\u8005\u7684\u8ba4\u77e5\u8d1f\u62c5\n\n### 2. **\u4e30\u5bcc\u7684\u5b66\u4e60\u8d44\u6e90**\n- \u5927\u91cf\u514d\u8d39\u6559\u7a0b\u548c\u6587\u6863\n- \u6d3b\u8dc3\u7684\u793e\u533a\u652f\u6301\n- \u4e30\u5bcc\u7684\u7b2c\u4e09\u65b9\u5e93\n\n### 3. **\u5e94\u7528\u9886\u57df\u5e7f\u6cdb**\n- Web \u5f00\u53d1\n- \u6570\u636e\u5206\u6790\n- \u4eba\u5de5\u667a\u80fd\n- \u81ea\u52a8\u5316\u811a\u672c\n- \u6e38\u620f\u5f00\u53d1\n\n### 4. **\u5f00\u53d1\u73af\u5883\u53cb\u597d**\n- \u89e3\u91ca\u578b\u8bed\u8a00\uff0c\u5373\u65f6\u53cd\u9988\n- \u5f3a\u5927\u7684 IDE \u652f\u6301\n- \u8be6\u7ec6\u7684\u9519\u8bef\u63d0\u793a\n\n## \ud83d\ude80 **\u5b66\u4e60\u5efa\u8bae**\n\n1. **\u4ece\u57fa\u7840\u5f00\u59cb**\uff1a\u53d8\u91cf\u3001\u5faa\u73af\u3001\u51fd\u6570\n2. **\u52a8\u624b\u5b9e\u8df5**\uff1a\u591a\u5199\u4ee3\u7801\uff0c\u591a\u505a\u7ec3\u4e60\n3. **\u5faa\u5e8f\u6e10\u8fdb**\uff1a\u4ece\u7b80\u5355\u9879\u76ee\u5f00\u59cb\n4. **\u5584\u7528\u8d44\u6e90**\uff1a\u5229\u7528\u5728\u7ebf\u6559\u7a0b\u548c\u793e\u533a\n\nPython \u7684\u8bbe\u8ba1\u7406\u5ff5\u5c31\u662f\"\u7b80\u6d01\u4f18\u96c5\"\uff0c\u8fd9\u8ba9\u5b83\u6210\u4e3a\u7f16\u7a0b\u5165\u95e8\u7684\u7edd\u4f73\u9009\u62e9\uff01","model":"Qwen/Qwen3-Coder-480B-A35B-Instruct","raw":{"choices":[{"delta":{"content":"","function_calls":null,"reasoning_content":"","role":null,"tool_calls":null},"finish_reason":"stop","index":0,"logprobs":null,"message":{"annotations":null,"audio":null,"content":"\u662f\u7684\uff0cPython \u975e\u5e38\u9002\u5408\u521d\u5b66\u8005\uff01\u4ee5\u4e0b\u662f\u4e3b\u8981\u539f\u56e0\uff1a\n\n## \ud83c\udfaf **\u8bed\u6cd5\u7b80\u6d01\u6613\u61c2**\n```python\n# Python \u4ee3\u7801\u793a\u4f8b\nprint(\"Hello, World!\")\nname = input(\"\u4f60\u7684\u540d\u5b57\uff1a\")\nprint(f\"\u4f60\u597d\uff0c{name}\uff01\")\n```\n\n## \ud83c\udf1f **Python \u7684\u4f18\u52bf**\n\n### 1. **\u8bed\u6cd5\u63a5\u8fd1\u81ea\u7136\u8bed\u8a00**\n- \u4ee3\u7801\u53ef\u8bfb\u6027\u5f3a\n- \u5b66\u4e60\u66f2\u7ebf\u5e73\u7f13\n- \u51cf\u5c11\u521d\u5b66\u8005\u7684\u8ba4\u77e5\u8d1f\u62c5\n\n### 2. **\u4e30\u5bcc\u7684\u5b66\u4e60\u8d44\u6e90**\n- \u5927\u91cf\u514d\u8d39\u6559\u7a0b\u548c\u6587\u6863\n- \u6d3b\u8dc3\u7684\u793e\u533a\u652f\u6301\n- \u4e30\u5bcc\u7684\u7b2c\u4e09\u65b9\u5e93\n\n### 3. **\u5e94\u7528\u9886\u57df\u5e7f\u6cdb**\n- Web \u5f00\u53d1\n- \u6570\u636e\u5206\u6790\n- \u4eba\u5de5\u667a\u80fd\n- \u81ea\u52a8\u5316\u811a\u672c\n- \u6e38\u620f\u5f00\u53d1\n\n### 4. **\u5f00\u53d1\u73af\u5883\u53cb\u597d**\n- \u89e3\u91ca\u578b\u8bed\u8a00\uff0c\u5373\u65f6\u53cd\u9988\n- \u5f3a\u5927\u7684 IDE \u652f\u6301\n- \u8be6\u7ec6\u7684\u9519\u8bef\u63d0\u793a\n\n## \ud83d\ude80 **\u5b66\u4e60\u5efa\u8bae**\n\n1. **\u4ece\u57fa\u7840\u5f00\u59cb**\uff1a\u53d8\u91cf\u3001\u5faa\u73af\u3001\u51fd\u6570\n2. **\u52a8\u624b\u5b9e\u8df5**\uff1a\u591a\u5199\u4ee3\u7801\uff0c\u591a\u505a\u7ec3\u4e60\n3. **\u5faa\u5e8f\u6e10\u8fdb**\uff1a\u4ece\u7b80\u5355\u9879\u76ee\u5f00\u59cb\n4. **\u5584\u7528\u8d44\u6e90**\uff1a\u5229\u7528\u5728\u7ebf\u6559\u7a0b\u548c\u793e\u533a\n\nPython \u7684\u8bbe\u8ba1\u7406\u5ff5\u5c31\u662f\"\u7b80\u6d01\u4f18\u96c5\"\uff0c\u8fd9\u8ba9\u5b83\u6210\u4e3a\u7f16\u7a0b\u5165\u95e8\u7684\u7edd\u4f73\u9009\u62e9\uff01","function_call":null,"function_calls":null,"reasoning_content":"","refusal":null,"role":"assistant","tool_calls":null}}],"created":1758968114624,"id":"chatcmpl-1a64fca7-28f3-429b-b35b-bfd4487ca272","model":"Qwen/Qwen3-Coder-480B-A35B-Instruct","object":"chat.completion","service_tier":null,"system_fingerprint":"","usage":{"completion_tokens":288,"completion_tokens_details":null,"prompt_tokens":15,"prompt_tokens_details":null,"total_tokens":303}}}
```

## 流式对话 `/api/chat/stream`

### 简单对话

```bash
curl -N -X POST http://127.0.0.1:7207/api/chat/stream ^
  -H "Content-Type: application/json" ^
  -d "{\"messages\":[{\"role\":\"user\",\"content\":\"请用一句话总结量子计算\"}]}"
```
```bash
{"delta": "量子"}
{"delta": "计算是"}
{"delta": "利用量子力学"}
{"delta": "原理，"}
{"delta": "通过量子比特的"}
{"delta": "叠加和纠缠特性"}
{"delta": "，实现并行"}
{"delta": "计算和"}
{"delta": "指数级加速的"}
{"delta": "新型计算范式"}
{"delta": "。"}
{"event": "done"}
```
### 带 system 提示

```bash
curl -N -X POST http://127.0.0.1:7207/api/chat/stream ^
  -H "Content-Type: application/json" ^
  -d "{\"messages\":[{\"role\":\"system\",\"content\":\"你是一位数学家\"},{\"role\":\"user\",\"content\":\"解释勾股定理\"}]}"
```
```bash
{"delta": "勾"}
{"delta": "股定理是"}
{"delta": "几何"}
#(太长了，这里省略中间的)
{"event": "done"}
```

# <font color="red">TTS模块</font>
模型权重和源码不再下载，重构源代码的 webui.py 为 Flask API 接口，直接放在源码的根目录下，按照根目录的 README.md 配置环境。uv 安装一下 flask 模块然后运行 flask.py 即可。
```bash
uv pip install flask
python3 flask_v2.py
```
## flaskapi_v1
可以正常基于说话人声音和文本进行语音合成，目前还有些小问题。

## flaskapi_v2
可以正常基于说话人声音和文本进行语音合成，并且可以返回合成后的语音文件。也可以根据参考音频生成对应风格的语音。

### 使用默认风格音频

```bash
curl -X POST http://127.0.0.1:7206/synthesize ^
  -F "text=你好，这是默认风格的测试" ^
  -F "style=style2" ^
  --output output.wav
```
```bash
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100  182k  100  182k  100   293  28289     44  0:00:06  0:00:06 --:--:-- 52952
```
### 上传用户参考音频

```cmd
curl -X POST http://127.0.0.1:7206/synthesize ^
  -F "text=你好，这是用我自己的录音做参考的测试" ^
  -F "prompt_audio=@test.wav" ^
  --output output.wav
```
```bash
与使用默认风格音频的响应相同
```

* 这里的 `test.wav` 必须是你 **本地 cmd 工作目录**下的文件；


### 带调参的请求

```bash
curl -X POST http://127.0.0.1:7206/synthesize ^
  -F "text=你好，这是调节参数后的TTS测试" ^
  -F "style=style1" ^
  -F "temperature=0.6" ^
  -F "top_p=0.9" ^
  --output output.wav
```
```bash
与使用默认风格音频的响应相同
```

### 健康检查

```bash
curl http://127.0.0.1:7206/health
```
```bash
{"status":"ok"}
```
# <font color="red">联网搜索模块</font>
这个部分由传统关系型数据库 PostgreSQL 与非关系型数据库 Qdrant 组成，如果在几年前，凭我的认知只会单单使用 MySQL 数据库。但近几年AI的兴趣和知识的爆炸，Qdrant 的独特检索机制能更好游龙于千万级数据量中。但不意味着传统关系型数据库 PostgreSQL 或 MySQL没有优势。这里是基于开源免费选的 PostgreSQL。

```bash
curl http://127.0.0.1:5080/health
```
```bash
{
  "service": "websearch-api",
  "status": "ok"
}
```
## 数据入库

### 单条 URL 入库

抓取网页 → 解析正文 → 切块 → 调你的 7202 Embedding API → 存 PostgreSQL + Qdrant

```bash
curl -X POST http://127.0.0.1:5080/ingest ^
  -H "Content-Type: application/json" ^
  -d "{\"url\":\"https://www.python.org/\"}"
```
```bash
{
  "chunks": 1,
  "page_id": 1,
  "published_at": null,
  "title": "Welcome to Python.org",
  "url": "https://www.python.org/"
}
```

### 批量 URL 入库

```bash
curl -X POST http://127.0.0.1:5080/bulk_ingest ^
  -H "Content-Type: application/json" ^
  -d "{\"urls\":[\"https://www.python.org/\",\"https://docs.python.org/3/tutorial/index.html\"]}"
```
```bash
[
  {
    "chunks": 1,
    "ok": true,
    "page_id": 1,
    "published_at": null,
    "title": "Welcome to Python.org",
    "url": "https://www.python.org/"
  },
  {
    "chunks": 6,
    "ok": true,
    "page_id": 2,
    "published_at": null,
    "title": "The Python Tutorial \u2014 Python 3.13.7 documentation",
    "url": "https://docs.python.org/3/tutorial/index.html"
  }
]
```

## 搜索接口

### 关键词搜索（PostgreSQL trigram）

模糊匹配标题 + 内容

```bash
curl "http://127.0.0.1:5080/search/keyword?q=Python&limit=5"
```
```bash
[
  {
    "chunk_index": 0,
    "score_hint": "keyword",
    "snippet": "...ing or an experienced developer, it's easy to learn and use Python. Download Python source code and installers are available for download for all versions! Latest: Python 3.13.7 Docs Doc...",
    "title": "Welcome to Python.org",
    "url": "https://www.python.org/"
  },
  {
    "chunk_index": 0,
    "score_hint": "keyword",
    "snippet": "The Python Tutorial\u00c2\u00b6 Tip This tutorial is designed for programmers that are new to the Python language, not beginners who are new...",
    "title": "The Python Tutorial \u2014 Python 3.13.7 documentation",
    "url": "https://docs.python.org/3/tutorial/index.html"
  },
  {
    "chunk_index": 1,
    "score_hint": "keyword",
    "snippet": "inary form for all major platforms from the Python web site, https://www.python.org/, and may be freely distributed. The same site also contains distributions of and poin...",
    "title": "The Python Tutorial \u2014 Python 3.13.7 documentation",
    "url": "https://docs.python.org/3/tutorial/index.html"
  },
  {
    "chunk_index": 2,
    "score_hint": "keyword",
    "snippet": "...understanding of programming in general. It helps to have a Python interpreter handy for hands-on experience, but all examples are self-contained, so the tutorial can be read off-line as...",
    "title": "The Python Tutorial \u2014 Python 3.13.7 documentation",
    "url": "https://docs.python.org/3/tutorial/index.html"
  },
  {
    "chunk_index": 3,
    "score_hint": "keyword",
    "snippet": "...every commonly used feature. Instead, it introduces many of Python\u00e2s most noteworthy features, and will give you a good idea of the language\u00e2s flavor and style. After reading it, you wil...",
    "title": "The Python Tutorial \u2014 Python 3.13.7 documentation",
    "url": "https://docs.python.org/3/tutorial/index.html"
  }
]
```

### 语义搜索（Qdrant 向量检索）

```bash
curl "http://127.0.0.1:5080/search/semantic?q=解释器%20与%20编译器的区别&limit=5"
```
```bash
[
  {
    "chunk_index": 2,
    "score": 0.34712094,
    "score_hint": "semantic",
    "snippet": " Be aware that it expects you to have a basic understanding of programming in general. It helps to have a Python interpreter handy for hands-on experience, but all examples are sel...",
    "title": "The Python Tutorial \u2014 Python 3.13.7 documentation",
    "url": "https://docs.python.org/3/tutorial/index.html"
  },
  {
    "chunk_index": 3,
    "score": 0.31827354,
    "score_hint": "semantic",
    "snippet": "ttempt to be comprehensive and cover every single feature, or even every commonly used feature. Instead, it introduces many of Python\u00e2s most noteworthy features, and will give you ...",
    "title": "The Python Tutorial \u2014 Python 3.13.7 documentation",
    "url": "https://docs.python.org/3/tutorial/index.html"
  },
  {
    "chunk_index": 1,
    "score": 0.31330746,
    "score_hint": "semantic",
    "snippet": "inary form for all major platforms from the Python web site, https://www.python.org/, and may be freely distributed. The same site also contains distributions of and pointers to ma...",
    "title": "The Python Tutorial \u2014 Python 3.13.7 documentation",
    "url": "https://docs.python.org/3/tutorial/index.html"
  },
  {
    "chunk_index": 5,
    "score": 0.29914415,
    "score_hint": "semantic",
    "snippet": "- 10.6. Mathematics - 10.7. Internet Access - 10.8. Dates and Times - 10.9. Data Compression - 10.10. Performance Measurement - 10.11. Quality Control - 10.12. Batteries Included -...",
    "title": "The Python Tutorial \u2014 Python 3.13.7 documentation",
    "url": "https://docs.python.org/3/tutorial/index.html"
  },
  {
    "chunk_index": 0,
    "score": 0.2829848,
    "score_hint": "semantic",
    "snippet": "The Python Tutorial\u00c2\u00b6 Tip This tutorial is designed for programmers that are new to the Python language, not beginners who are new to programming. Python is an easy to learn, power...",
    "title": "The Python Tutorial \u2014 Python 3.13.7 documentation",
    "url": "https://docs.python.org/3/tutorial/index.html"
  }
]
```
### 混合搜索（关键词 + 语义）

默认 `alpha=0.7`，语义为主，关键词加权

```bash
curl "http://127.0.0.1:5080/search/hybrid?q=虚拟环境%20环境管理&limit=5&alpha=0.7"
```
```bash
[
  {
    "chunk_index": 2,
    "score": 0.23169680799999998,
    "score_hint": "hybrid",
    "snippet": " Be aware that it expects you to have a basic understanding of programming in general. It helps to have a Python interpreter handy for hands-on experience, but all examples are sel...",
    "title": "The Python Tutorial \u2014 Python 3.13.7 documentation",
    "url": "https://docs.python.org/3/tutorial/index.html"
  },
  {
    "chunk_index": 0,
    "score": 0.229880175,
    "score_hint": "hybrid",
    "snippet": "The Python Tutorial\u00c2\u00b6 Tip This tutorial is designed for programmers that are new to the Python language, not beginners who are new to programming. Python is an easy to learn, power...",
    "title": "The Python Tutorial \u2014 Python 3.13.7 documentation",
    "url": "https://docs.python.org/3/tutorial/index.html"
  },
  {
    "chunk_index": 1,
    "score": 0.22923321399999996,
    "score_hint": "hybrid",
    "snippet": "inary form for all major platforms from the Python web site, https://www.python.org/, and may be freely distributed. The same site also contains distributions of and pointers to ma...",
    "title": "The Python Tutorial \u2014 Python 3.13.7 documentation",
    "url": "https://docs.python.org/3/tutorial/index.html"
  },
  {
    "chunk_index": 3,
    "score": 0.22216139399999998,
    "score_hint": "hybrid",
    "snippet": "ttempt to be comprehensive and cover every single feature, or even every commonly used feature. Instead, it introduces many of Python\u00e2s most noteworthy features, and will give you ...",
    "title": "The Python Tutorial \u2014 Python 3.13.7 documentation",
    "url": "https://docs.python.org/3/tutorial/index.html"
  },
  {
    "chunk_index": 5,
    "score": 0.21144671799999998,
    "score_hint": "hybrid",
    "snippet": "- 10.6. Mathematics - 10.7. Internet Access - 10.8. Dates and Times - 10.9. Data Compression - 10.10. Performance Measurement - 10.11. Quality Control - 10.12. Batteries Included -...",
    "title": "The Python Tutorial \u2014 Python 3.13.7 documentation",
    "url": "https://docs.python.org/3/tutorial/index.html"
  }
]
```

##  查看原始页面记录

根据 `url` 或 `id` 查看数据库里存的页面原文（正文 + HTML 截断）

### 按 URL 查

```bash
curl "http://127.0.0.1:5080/page?url=https://www.python.org/"
```
```bash
{
  "content": "Get Started Whether you're new to programming or an experienced developer, it's easy to learn and use Python. Download Python source code and installers are available for download for all versions! Latest: Python 3.13.7 Docs Documentation for Python's standard library, along with tutorials and guides, are available online. Jobs Looking for work or have a Python related position that you're trying to hire for? Our relaunched community-run job board is the place to go. Use Python for\u2026 >>> Python Software Foundation The mission of the Python Software Foundation is to promote, protect, and advance the Python programming language, and to support and facilitate the growth of a diverse and international community of Python programmers. Learn more",
  "fetched_at": "Sat, 27 Sep 2025 10:42:09 GMT",
  "html": "<!doctype html>\n<!--[if lt IE 7]>   <html class=\"no-js ie6 lt-ie7 lt-ie8 lt-ie9\">   <![endif]-->\n<!--[if IE 7]>      <html class=\"no-js ie7 lt-ie8 lt-ie9\">          <![endif]-->\n<!--[if IE 8]>      <html class=\"no-js ie8 lt-ie9\">                 <![endif]-->\n<!--[if gt IE 8]><!--><html class=\"no-js\" lang=\"en\" dir=\"ltr\">  <!--<![endif]-->\n\n<head>\n    <script defer data-domain=\"python.org\" src=\"https://analytics.python.org/js/script.outbound-links.js\"></script>\n\n    <meta charset=\"utf-8\">\n    <meta http-equiv=\"X-UA-Compatible\" content=\"IE=edge\">\n\n    <link rel=\"prefetch\" href=\"//ajax.googleapis.com/ajax/libs/jquery/1.8.2/jquery.min.js\">\n    <link rel=\"prefetch\" href=\"//ajax.googleapis.com/ajax/libs/jqueryui/1.12.1/jquery-ui.min.js\">\n\n    <meta name=\"application-name\" content=\"Python.org\">\n    <meta name=\"msapplication-tooltip\" content=\"The official home of the Python Programming Language\">\n    <meta name=\"apple-mobile-web-app-title\" content=\"Python.org\">\n    <meta name=\"apple-mobile-web-app-capable\" content=\"yes\">\n    <meta name=\"apple-mobile-web-app-status-bar-style\" content=\"black\">\n\n    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n    <meta name=\"HandheldFriendly\" content=\"True\">\n    <meta name=\"format-detection\" content=\"telephone=no\">\n    <meta http-equiv=\"cleartype\" content=\"on\">\n    <meta http-equiv=\"imagetoolbar\" content=\"false\">\n\n    <script async\n            src=\"https://media.ethicalads.io/media/client/v1.4.0/ethicalads.min.js\"\n            integrity=\"sha256-U3hKDidudIaxBDEzwGJApJgPEf2mWk6cfMWghrAa6i0= sha384-UcmsCqcNRSLW/dV3Lo1oCi2/VaurXbib6p4HyUEOeIa/4OpsrnucrugAefzVZJfI sha512-q4t1L4xEjGV2R4hzqCa41P8jrgFUS8xTb8rdNv4FGvw7FpydVj/kkxBJHOiaoxHa8olCcx1Slk9K+3sNbsM4ug==\"\n            crossorigin=\"anonymous\"\n    ></script>\n    <script src=\"/static/js/libs/modernizr.js\"></script>\n\n    <link href=\"/static/stylesheets/style.08a078d0aa02.css\" rel=\"stylesheet\" type=\"text/css\" media=\"all\" title=\"default\" />\n    <link href=\"/static/stylesheets/mq.98d6092b2ada.css\" rel=\"stylesheet\" type=\"text/css\" media=\"not print, braille, embossed, speech, tty\" />\n    <link href=\"/static/stylesheets/no-mq.bf0c425cdb73.css\" rel=\"stylesheet\" type=\"text/css\" media=\"screen\" />\n    \n\n    <!--[if (lte IE 8)&(!IEMobile)]>\n    <link href=\"/static/stylesheets/no-mq.bf0c425cdb73.css\" rel=\"stylesheet\" type=\"text/css\" media=\"screen\" />\n    \n    \n    <![endif]-->\n    <link rel=\"stylesheet\" href=\"//ajax.googleapis.com/ajax/libs/jqueryui/1.12.1/themes/smoothness/jquery-ui.css\">\n\n    \n    <link rel=\"icon\" type=\"image/x-icon\" href=\"/static/favicon.ico\">\n    <link rel=\"apple-touch-icon-precomposed\" sizes=\"144x144\" href=\"/static/apple-touch-icon-144x144-precomposed.png\">\n    <link rel=\"apple-touch-icon-precomposed\" sizes=\"114x114\" href=\"/static/apple-touch-icon-114x114-precomposed.png\">\n    <link rel=\"apple-touch-icon-precomposed\" sizes=\"72x72\" href=\"/static/apple-touch-icon-72x72-precomposed.png\">\n    <link rel=\"apple-touch-icon-precomposed\" href=\"/static/apple-touch-icon-precomposed.png\">\n    <link rel=\"apple-touch-icon\" href=\"/static/apple-touch-icon-precomposed.png\">\n\n    \n    <meta name=\"msapplication-TileImage\" content=\"/static/metro-icon-144x144.png\"><!-- white shape -->\n    <meta name=\"msapplication-TileColor\" content=\"#3673a5\"><!-- python blue -->\n    <meta name=\"msapplication-navbutton-color\" content=\"#3673a5\">\n\n    <title>Welcome to Python.org</title>\n\n    <meta name=\"description\" content=\"The official home of the Python Programming Language\">\n    <meta name=\"keywords\" content=\"Python programming language object oriented web free open source software license documentation download community\">\n\n    \n    <meta property=\"og:type\" content=\"website\">\n    <meta property=\"og:site_name\" content=\"Python.org\">\n    <meta property=\"og:title\" content=\"Welcome to Python.org\">\n    <meta property=\"og:description\" content=\"The official home of the Python Programming Language\">\n    \n    <meta property=\"og:image\" content=\"https://www.python.org/st...",
  "id": 1,
  "lang": "en",
  "published_at": null,
  "site": "www.python.org",
  "title": "Welcome to Python.org",
  "url": "https://www.python.org/"
}
```

### 按 ID 查

```bash
curl "http://127.0.0.1:5080/page?id=1"
```
```bash
{
  "content": "Get Started Whether you're new to programming or an experienced developer, it's easy to learn and use Python. Download Python source code and installers are available for download for all versions! Latest: Python 3.13.7 Docs Documentation for Python's standard library, along with tutorials and guides, are available online. Jobs Looking for work or have a Python related position that you're trying to hire for? Our relaunched community-run job board is the place to go. Use Python for\u2026 >>> Python Software Foundation The mission of the Python Software Foundation is to promote, protect, and advance the Python programming language, and to support and facilitate the growth of a diverse and international community of Python programmers. Learn more",
  "fetched_at": "Sat, 27 Sep 2025 10:42:09 GMT",
  "html": "<!doctype html>\n<!--[if lt IE 7]>   <html class=\"no-js ie6 lt-ie7 lt-ie8 lt-ie9\">   <![endif]-->\n<!--[if IE 7]>      <html class=\"no-js ie7 lt-ie8 lt-ie9\">          <![endif]-->\n<!--[if IE 8]>      <html class=\"no-js ie8 lt-ie9\">                 <![endif]-->\n<!--[if gt IE 8]><!--><html class=\"no-js\" lang=\"en\" dir=\"ltr\">  <!--<![endif]-->\n\n<head>\n    <script defer data-domain=\"python.org\" src=\"https://analytics.python.org/js/script.outbound-links.js\"></script>\n\n    <meta charset=\"utf-8\">\n    <meta http-equiv=\"X-UA-Compatible\" content=\"IE=edge\">\n\n    <link rel=\"prefetch\" href=\"//ajax.googleapis.com/ajax/libs/jquery/1.8.2/jquery.min.js\">\n    <link rel=\"prefetch\" href=\"//ajax.googleapis.com/ajax/libs/jqueryui/1.12.1/jquery-ui.min.js\">\n\n    <meta name=\"application-name\" content=\"Python.org\">\n    <meta name=\"msapplication-tooltip\" content=\"The official home of the Python Programming Language\">\n    <meta name=\"apple-mobile-web-app-title\" content=\"Python.org\">\n    <meta name=\"apple-mobile-web-app-capable\" content=\"yes\">\n    <meta name=\"apple-mobile-web-app-status-bar-style\" content=\"black\">\n\n    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n    <meta name=\"HandheldFriendly\" content=\"True\">\n    <meta name=\"format-detection\" content=\"telephone=no\">\n    <meta http-equiv=\"cleartype\" content=\"on\">\n    <meta http-equiv=\"imagetoolbar\" content=\"false\">\n\n    <script async\n            src=\"https://media.ethicalads.io/media/client/v1.4.0/ethicalads.min.js\"\n            integrity=\"sha256-U3hKDidudIaxBDEzwGJApJgPEf2mWk6cfMWghrAa6i0= sha384-UcmsCqcNRSLW/dV3Lo1oCi2/VaurXbib6p4HyUEOeIa/4OpsrnucrugAefzVZJfI sha512-q4t1L4xEjGV2R4hzqCa41P8jrgFUS8xTb8rdNv4FGvw7FpydVj/kkxBJHOiaoxHa8olCcx1Slk9K+3sNbsM4ug==\"\n            crossorigin=\"anonymous\"\n    ></script>\n    <script src=\"/static/js/libs/modernizr.js\"></script>\n\n    <link href=\"/static/stylesheets/style.08a078d0aa02.css\" rel=\"stylesheet\" type=\"text/css\" media=\"all\" title=\"default\" />\n    <link href=\"/static/stylesheets/mq.98d6092b2ada.css\" rel=\"stylesheet\" type=\"text/css\" media=\"not print, braille, embossed, speech, tty\" />\n    <link href=\"/static/stylesheets/no-mq.bf0c425cdb73.css\" rel=\"stylesheet\" type=\"text/css\" media=\"screen\" />\n    \n\n    <!--[if (lte IE 8)&(!IEMobile)]>\n    <link href=\"/static/stylesheets/no-mq.bf0c425cdb73.css\" rel=\"stylesheet\" type=\"text/css\" media=\"screen\" />\n    \n    \n    <![endif]-->\n    <link rel=\"stylesheet\" href=\"//ajax.googleapis.com/ajax/libs/jqueryui/1.12.1/themes/smoothness/jquery-ui.css\">\n\n    \n    <link rel=\"icon\" type=\"image/x-icon\" href=\"/static/favicon.ico\">\n    <link rel=\"apple-touch-icon-precomposed\" sizes=\"144x144\" href=\"/static/apple-touch-icon-144x144-precomposed.png\">\n    <link rel=\"apple-touch-icon-precomposed\" sizes=\"114x114\" href=\"/static/apple-touch-icon-114x114-precomposed.png\">\n    <link rel=\"apple-touch-icon-precomposed\" sizes=\"72x72\" href=\"/static/apple-touch-icon-72x72-precomposed.png\">\n    <link rel=\"apple-touch-icon-precomposed\" href=\"/static/apple-touch-icon-precomposed.png\">\n    <link rel=\"apple-touch-icon\" href=\"/static/apple-touch-icon-precomposed.png\">\n\n    \n    <meta name=\"msapplication-TileImage\" content=\"/static/metro-icon-144x144.png\"><!-- white shape -->\n    <meta name=\"msapplication-TileColor\" content=\"#3673a5\"><!-- python blue -->\n    <meta name=\"msapplication-navbutton-color\" content=\"#3673a5\">\n\n    <title>Welcome to Python.org</title>\n\n    <meta name=\"description\" content=\"The official home of the Python Programming Language\">\n    <meta name=\"keywords\" content=\"Python programming language object oriented web free open source software license documentation download community\">\n\n    \n    <meta property=\"og:type\" content=\"website\">\n    <meta property=\"og:site_name\" content=\"Python.org\">\n    <meta property=\"og:title\" content=\"Welcome to Python.org\">\n    <meta property=\"og:description\" content=\"The official home of the Python Programming Language\">\n    \n    <meta property=\"og:image\" content=\"https://www.python.org/st...",
  "id": 1,
  "lang": "en",
  "published_at": null,
  "site": "www.python.org",
  "title": "Welcome to Python.org",
  "url": "https://www.python.org/"
}
```

# <font color="red"> VLLM 模块</font>
普通接口（一次性返回结果）
```bash
curl -X POST http://127.0.0.1:7208/describe_image ^
  -H "Content-Type: application/json" ^
  -d "{\"text\": \"描述这幅图\", \"image_url\": \"https://modelscope.oss-cn-beijing.aliyuncs.com/demo/images/audrey_hepburn.jpg\"}"
```
```
{
  "result": "\u8fd9\u662f\u4e00\u5f20\u7ecf\u5178\u7684\u9ed1\u767d\u7167\u7247\uff0c\u62cd\u6444\u4e8e1950\u5e74\u4ee3\uff0c\u4e3b\u89d2\u662f\u8457\u540d\u5f71\u661f\u5965\u9edb\u4e3d\u00b7\u8d6b\u672c\uff08Audrey Hepburn\uff09\u3002\n\n\u7167\u7247\u4e2d\uff0c\u8d6b\u672c\u8eab\u7a7f\u4e00\u4ef6\u8f7b\u76c8\u7684\u3001\u5e26\u6709\u82b1\u5349\u56fe\u6848\u7684\u540a\u5e26\u8fde\u8863\u88d9\uff0c\u8d64\u7740\u53cc\u811a\uff0c\u8e72\u5728\u53a8\u623f\u7684\u5730\u677f\u4e0a\u3002\u5979\u6b63\u4e13\u6ce8\u5730\u6253\u5f00\u4e00\u4e2a\u8001\u5f0f\u70e4\u7bb1\u7684\u95e8\uff0c\u8eab\u4f53\u5fae\u5fae\u524d\u503e\uff0c\u76ee\u5149\u6295\u5411\u70e4\u7bb1\u5185\u90e8\uff0c\u795e\u60c5\u8ba4\u771f\u800c\u7565\u5e26\u4e00\u4e1d\u597d\u5947\u6216\u56f0\u60d1\u3002\n\n\u5979\u7684\u53d1\u578b\u662f\u6807\u5fd7\u6027\u7684\u77ed\u53d1\uff0c\u663e\u5f97\u5e72\u7ec3\u53c8\u4fcf\u76ae\u3002\u6574\u4e2a\u573a\u666f\u5145\u6ee1\u4e86\u751f\u6d3b\u6c14\u606f\u548c\u4e00\u79cd\u4e0d\u7ecf\u610f\u7684\u4f18\u96c5\u2014\u2014\u5373\u4f7f\u662f\u5728\u505a\u5bb6\u52a1\uff0c\u5979\u4f9d\u7136\u4fdd\u6301\u7740\u8ff7\u4eba\u7684\u59ff\u6001\u548c\u6c14\u8d28\u3002\n\n\u80cc\u666f\u662f\u5178\u578b\u7684\u7f8e\u5f0f\u53a8\u623f\uff0c\u53ef\u4ee5\u770b\u5230\u767d\u8272\u7684\u6a71\u67dc\u3001\u7a97\u6237\u4ee5\u53ca\u4e00\u4e2a\u88c5\u7740\u62a5\u7eb8\u7684\u5783\u573e\u6876\u3002\u7167\u7247\u7684\u6784\u56fe\u5c06\u7126\u70b9\u5b8c\u5168\u96c6\u4e2d\u5728\u8d6b\u672c\u8eab\u4e0a\uff0c\u6355\u6349\u4e86\u8fd9\u4f4d\u94f6\u5e55\u5973\u795e\u5728\u79c1\u5bc6\u7a7a\u95f4\u91cc\u81ea\u7136\u3001\u771f\u5b9e\u7684\u4e00\u9762\uff0c\u5c55\u73b0\u4e86\u5979\u4e0e\u516c\u4f17\u5f62\u8c61\u4e0d\u540c\u7684\u4eb2\u548c\u529b\u4e0e\u751f\u6d3b\u611f\u3002\n\n\u8fd9\u5f20\u7167\u7247\u5e38\u88ab\u8ba4\u4e3a\u662f\u6444\u5f71\u5e08\u83f2\u5229\u666e\u00b7\u54c8\u5c14\u65af\u66fc\uff08Philippe Halsman\uff09\u7684\u4f5c\u54c1\uff0c\u5b83\u6253\u7834\u4e86\u660e\u661f\u9ad8\u9ad8\u5728\u4e0a\u7684\u523b\u677f\u5370\u8c61\uff0c\u8ba9\u89c2\u4f17\u770b\u5230\u8d6b\u672c\u4f5c\u4e3a\u666e\u901a\u5973\u6027\u7684\u53ef\u7231\u4e0e\u771f\u5b9e\u3002"
}
```
流式接口（逐步返回结果）
```bash
curl -X POST http://127.0.0.1:7208/describe_image_stream ^
  -H "Content-Type: application/json" ^
  -d "{\"text\": \"描述这幅图\", \"image_url\": \"https://modelscope.oss-cn-beijing.aliyuncs.com/demo/images/audrey_hepburn.jpg\"}"
```
```
这是一张经典的黑白照片，主角是著名影星奥黛丽·赫本（Audrey Hepburn）。照片捕捉了她在一个厨房里非常生活化、接地气的瞬间。

**场景与人物：**

*   **人物姿态**：奥黛丽·赫本赤着脚，蹲在厨房的地板上。她身体微微前倾，神情专注地低头看着面前打开的烤箱。
*   **衣着**：她穿着一件带有花卉图案的吊带连衣裙，款式轻盈休闲，与她平时银幕上的优雅形象形成有趣的反差，展现了她私下随性的一面。
*   **动作**：她的右手正伸向烤箱内部，似乎是在检查或取出什么东西；左手则扶着烤箱门，保持其打开的状态。

**环境细节：**

*   **厨房**：背景是一个典型的美式家庭厨房，可以看到白色的橱柜和台面。
*   **烤箱**：她面前是一个老式的白色电烤箱，烤箱门向下打开，内部的烤架清晰可见。
*   **其他物品**：在她身后的角落里，有一个用报纸衬里的垃圾桶。上方的窗台上还放着一盆绿植，为这个日常场景增添了一丝生气。

**整体氛围：**

这张照片由摄影师马克·肖（Mark Shaw）于1950年代拍摄，旨在展现明星“人”的一面，而非遥不可及的偶像。它成功地捕捉到了奥黛丽·赫本在家中放松、自然的状态，充满了生活气息和亲切感。尽管是黑白影像，但她的专注神情和优雅气质依然跃然纸上，使这张照片成为她众多经典影像中极具代表性和亲和力的一幅。
```

# <font color="red"> Embedding 模块</font>

虽然你主要是通过 `core.py` 调用，但也可以单独测试：

## 单条 GET

```bash
curl "http://127.0.0.1:7202/Qwen3-Embedding-4B/hello%20world"
```

## 批量 POST

```bash
curl -X POST http://127.0.0.1:7202/Qwen3-Embedding-4B ^
  -H "Content-Type: application/json" ^
  -d "{\"texts\":[\"hello world\",\"python语言\"]}"
```

## 相似度

```bash
curl -X POST http://127.0.0.1:7202/similarity ^
  -H "Content-Type: application/json" ^
  -d "{\"a\":\"python programming\",\"b\":\"learn python\"}"
```

## Rerank

```bash
curl -X POST http://127.0.0.1:7202/rerank ^
  -H "Content-Type: application/json" ^
  -d "{\"query\":\"python\",\"candidates\":[\"python tutorial\",\"java guide\",\"python flask\"]}"
```
