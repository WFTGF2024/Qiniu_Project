这里存AI大模型本地部署代码，全部由朱佳鸿开发
# <font color="red">语音识别模块</font>
## Whisper_v1
暂不使用，cnn库冲突，后续调明白会使用，因为它是SOTA
### 整段识别
```cmd
curl -X POST http://120.79.25.184:7205/transcribe ^
  -F "file=@test.wav"
```
### 流式识别
```cmd
curl -N -X POST http://120.79.25.184:7205/transcribe_stream ^
  -F "file=@test.wav"
```

## SenseVoice_v1
* `/asr`（非流式）
* `/asr/stream`（流式）

```cmd
curl -X POST http://120.79.25.184:7205/asr ^
     -F "file=@test.wav"
```
```cmd
curl -N -X POST http://120.79.25.184/asr/stream ^
     -F "file=@test.wav"
```


# <font color="red">LLM模块</font>
* `/health`
* `/api/chat`（非流式）
* `/api/chat/stream`（流式）

##  健康检查  `/health`

```bash
curl http://127.0.0.1:7207/health
```

## 非流式对话 `/api/chat`

### 最简单对话

```bash
curl -X POST http://127.0.0.1:7207/api/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"messages\":[{\"role\":\"user\",\"content\":\"你好，给我一句鸡汤\"}]}"
```

### 带 system 提示

```bash
curl -X POST http://127.0.0.1:7207/api/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"messages\":[{\"role\":\"system\",\"content\":\"你是一个精简的助手\"},{\"role\":\"user\",\"content\":\"请用一句话总结人工智能\"}]}"
```

### 指定模型

```bash
curl -X POST http://127.0.0.1:7207/api/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"model\":\"Qwen/Qwen3-Coder-480B-A35B-Instruct\",\"messages\":[{\"role\":\"user\",\"content\":\"Python 适合初学者吗？\"}]}"
```
### 保存到 JSON 再请求：

  ```json
  {
    "messages": [
      {"role": "system", "content": "你是一个简洁的助手"},
      {"role": "user", "content": "给我一句关于未来的格言"}
    ]
  }
  ```

  然后：

  ```bash
  curl -X POST http://127.0.0.1:7207/api/chat -H "Content-Type: application/json" -d @body.json
  ```

## 流式对话 `/api/chat/stream`

### 简单对话

```bash
curl -N -X POST http://127.0.0.1:7207/api/chat/stream ^
  -H "Content-Type: application/json" ^
  -d "{\"messages\":[{\"role\":\"user\",\"content\":\"请用一句话总结量子计算\"}]}"
```

### 带 system 提示

```bash
curl -N -X POST http://127.0.0.1:7207/api/chat/stream ^
  -H "Content-Type: application/json" ^
  -d "{\"messages\":[{\"role\":\"system\",\"content\":\"你是一位数学家\"},{\"role\":\"user\",\"content\":\"解释勾股定理\"}]}"
```

# <font color="red">TTS模块</font>
模型权重和源码不再下载，重构源代码的 webui.py 为 Flask API 接口，直接放在源码的根目录下，按照根目录的 README.md 配置环境。uv 安装一下 flask 模块然后运行 flask.py 即可。
```bash
uv pip install flask
python3 flask.py
```
## flaskapi_v1
可以正常基于说话人声音和文本进行语音合成，目前还有些小问题。

## flaskapi_v2
可以正常基于说话人声音和文本进行语音合成，并且可以返回合成后的语音文件。也可以根据参考音频生成对应风格的语音。

### 使用默认风格音频

```cmd
curl -X POST http://120.79.25.184:7206/synthesize ^
  -F "text=你好，这是默认风格的测试" ^
  -F "style=style2" ^
  --output output.wav
```

### 上传用户参考音频

```cmd
curl -X POST http://120.79.25.184:7206/synthesize ^
  -F "text=你好，这是用我自己的录音做参考的测试" ^
  -F "prompt_audio=@test.wav" ^
  --output output.wav
```


* 这里的 `test.wav` 必须是你 **本地 cmd 工作目录**下的文件；


### 带调参的请求

```cmd
curl -X POST http://120.79.25.184:7206/synthesize ^
  -F "text=你好，这是调节参数后的TTS测试" ^
  -F "style=style1" ^
  -F "temperature=0.6" ^
  -F "top_p=0.9" ^
  --output output.wav
```

### 健康检查

```cmd
curl http://120.79.25.184:7206/health
```

# <font color="red">联网搜索模块</font>
这个部分由传统关系型数据库 PostgreSQL 与非关系型数据库 Qdrant 组成，如果在几年前，凭我的认知只会单单使用 MySQL 数据库。但近几年AI的兴趣和知识的爆炸，Qdrant 的独特检索机制能更好游龙于千万级数据量中。但不意味着传统关系型数据库 PostgreSQL 或 MySQL没有优势。这里是基于开源免费选的 PostgreSQL。

```bash
curl http://127.0.0.1:5080/health
```

## 数据入库

### 单条 URL 入库

抓取网页 → 解析正文 → 切块 → 调你的 7202 Embedding API → 存 PostgreSQL + Qdrant

```bash
curl -X POST http://127.0.0.1:5080/ingest ^
  -H "Content-Type: application/json" ^
  -d "{\"url\":\"https://www.python.org/\"}"
```

### 批量 URL 入库

```bash
curl -X POST http://127.0.0.1:5080/bulk_ingest ^
  -H "Content-Type: application/json" ^
  -d "{\"urls\":[\"https://www.python.org/\",\"https://docs.python.org/3/tutorial/index.html\"]}"
```

---

## 搜索接口

### 关键词搜索（PostgreSQL trigram）

模糊匹配标题 + 内容

```bash
curl "http://127.0.0.1:5080/search/keyword?q=Python&limit=5"
```

### 语义搜索（Qdrant 向量检索）

用你的 7202 Embedding API 算向量，然后 Qdrant 最近邻搜索

```bash
curl "http://127.0.0.1:5080/search/semantic?q=解释器%20与%20编译器的区别&limit=5"
```

### 混合搜索（关键词 + 语义）

默认 `alpha=0.7`，语义为主，关键词加权

```bash
curl "http://127.0.0.1:5080/search/hybrid?q=虚拟环境%20环境管理&limit=5&alpha=0.7"
```


##  查看原始页面记录

根据 `url` 或 `id` 查看数据库里存的页面原文（正文 + HTML 截断）

### 按 URL 查

```bash
curl "http://127.0.0.1:5080/page?url=https://www.python.org/"
```

### 按 ID 查

```bash
curl "http://127.0.0.1:5080/page?id=1"
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
