from openai import OpenAI

# 初始化客户端
client = OpenAI(
    base_url='https://api-inference.modelscope.cn/v1',
    api_key='ms-fb4f7a45-0e56-4d01-a136-013064aece63',  # ModelScope Token
)

# 创建请求
response = client.chat.completions.create(
    model='Qwen/Qwen3-Coder-480B-A35B-Instruct',  # ModelScope Model-Id
    messages=[
        {
            'role': 'system',
            'content': 'You are a helpful assistant.'
        },
        {
            'role': 'user',
            'content': 
            '''
有没有语音直接生成语音对话的大模型？
'''
        }
    ],
    stream=True
)

# 打开文件准备写入
with open('Qwen_Generated.md', 'w', encoding='utf-8') as f:
    for chunk in response:
        content = chunk.choices[0].delta.content
        if content:  # 确保内容不为空
            print(content, end='', flush=True)  # 打印到控制台
            f.write(content)  # 写入文件