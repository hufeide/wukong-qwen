# deepseek API文档
DeepSeek API 使用与 OpenAI 兼容的 API 格式，通过修改配置，您可以使用 OpenAI SDK 来访问 DeepSeek API，或使用与 OpenAI API 兼容的软件。

PARAM	VALUE
base_url *       	https://api.deepseek.com
api_key	apply for an API key
* 出于与 OpenAI 兼容考虑，您也可以将 base_url 设置为 https://api.deepseek.com/v1 来使用，但注意，此处 v1 与模型版本无关。

* deepseek-chat 模型已全面升级为 DeepSeek-V3，接口不变。 通过指定 model='deepseek-chat' 即可调用 DeepSeek-V3。

* deepseek-reasoner 是 DeepSeek 最新推出的推理模型 DeepSeek-R1。通过指定 model='deepseek-reasoner'，即可调用 DeepSeek-R1。

调用对话 API
在创建 API key 之后，你可以使用以下样例脚本的来访问 DeepSeek API。样例为非流式输出，您可以将 stream 设置为 true 来使用流式输出。


python首次调用实例：
# Please install OpenAI SDK first: `pip3 install openai`

from openai import OpenAI

client = OpenAI(api_key="<DeepSeek API Key>", base_url="https://api.deepseek.com")

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "Hello"},
    ],
    stream=False
)

print(response.choices[0].message.content)

多轮对话
本指南将介绍如何使用 DeepSeek /chat/completions API 进行多轮对话。

DeepSeek /chat/completions API 是一个“无状态” API，即服务端不记录用户请求的上下文，用户在每次请求时，需将之前所有对话历史拼接好后，传递给对话 API。

下面的代码以 Python 语言，展示了如何进行上下文拼接，以实现多轮对话。

from openai import OpenAI
client = OpenAI(api_key="<DeepSeek API Key>", base_url="https://api.deepseek.com")

# Round 1
messages = [{"role": "user", "content": "What's the highest mountain in the world?"}]
response = client.chat.completions.create(
    model="deepseek-chat",
    messages=messages
)

messages.append(response.choices[0].message)
print(f"Messages Round 1: {messages}")

# Round 2
messages.append({"role": "user", "content": "What is the second?"})
response = client.chat.completions.create(
    model="deepseek-chat",
    messages=messages
)

messages.append(response.choices[0].message)
print(f"Messages Round 2: {messages}")

在第一轮请求时，传递给 API 的 messages 为：

[
    {"role": "user", "content": "What's the highest mountain in the world?"}
]

在第二轮请求时：

要将第一轮中模型的输出添加到 messages 末尾
将新的提问添加到 messages 末尾
最终传递给 API 的 messages 为：

[
    {"role": "user", "content": "What's the highest mountain in the world?"},
    {"role": "assistant", "content": "The highest mountain in the world is Mount Everest."},
    {"role": "user", "content": "What is the second?"}
]