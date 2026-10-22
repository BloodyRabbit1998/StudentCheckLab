import os
import dashscope

AI_TOKEN = os.getenv("AI_TOKEN")
dashscope.base_http_api_url = "https://maas.qwencloudapi.com/api/v1"

messages = [
    {"role": "system", "content": [{"text": "You are a helpful assistant."}]},
    {"role": "user",   "content": [{"text": "Распиши мне план на неделю по изучению "
                                            "английского языка в формате таблицы с 3 "
                                            "колонками: день недели, тема, время на "
                                            "изучение в формате .md"}]},
]

response = dashscope.MultiModalConversation.call(
    api_key=AI_TOKEN,
    model="qwen3.8-max",
    messages=messages,
    result_format="message",
    temperature=0.7,
    max_tokens=2000,
)

if response.status_code != 200:
    raise RuntimeError(f"{response.code}: {response.message}")

result = response.output.choices[0].message.content[0]["text"]

with open("result.md", "w", encoding="utf-8") as f:
    f.write(result)