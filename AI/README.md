这里存AI大模型本地部署代码，全部由朱佳鸿开发
# <font color="red">语音识别模块</font>
调试阶段，暂时没有push
# <font color="red">LLM模块</font>
调试阶段，暂时没有push
# <font color="red">TTS模块</font>
模型权重和源码就不下载了，重构了源代码的webui.py为Flask API接口，直接放在源码的根目录下，按照他的README.md配置环境。uv安装一下flask模块然后运行flask.py即可。
```bash
uv pip install flask
python3 flask.py
```
## flask_v1.py
可以正常基于说话人声音和文本进行语音合成，目前还有些小问题。
