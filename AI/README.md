这里存AI大模型本地部署代码，全部由朱佳鸿开发
# <font color="red">语音识别模块</font>
## Whisper_v1
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
```cmd
curl -X POST http://120.79.25.184:7205/asr ^
     -F "file=@test.wav"
```
```cmd
curl -N -X POST http://120.79.25.184/asr/stream ^
     -F "file=@test.wav"
```


# <font color="red">LLM模块</font>
直接调用ModelScope的API，调用方式详见Qwen.py
# <font color="red">TTS模块</font>
模型权重和源码就不下载了，重构了源代码的webui.py为Flask API接口，直接放在源码的根目录下，按照他的README.md配置环境。uv安装一下flask模块然后运行flask.py即可。
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