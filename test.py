import os
import requests
from dotenv import load_dotenv

load_dotenv()

webhook = os.getenv("FEISHU_WEBHOOK")

payload = {
    "msg_type": "text",
    "content": {
        "text": "这是一条测试消息"
    }
}

r = requests.post(webhook, json=payload)
print(r.json())
