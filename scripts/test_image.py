import base64
import json
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

img_path = Path.home() / "storage/dcim/Camera/test.jpg"
print("img_path =", img_path)
print("exists =", img_path.exists())
print("size =", img_path.stat().st_size if img_path.exists() else -1)

b64 = base64.b64encode(img_path.read_bytes()).decode()

payload = {
    "model": "qwen35-vlm",
    "messages": [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "请描述这张图片的主要内容，并尽量简洁。"
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{b64}"
                    }
                }
            ]
        }
    ],
    "temperature": 0.2,
    "max_tokens": 128
}

print("payload keys =", payload.keys())
print("first content types =", [x["type"] for x in payload["messages"][0]["content"]])

req = Request(
    "http://127.0.0.1:8081/v1/chat/completions",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST"
)

try:
    with urlopen(req, timeout=300) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        print(json.dumps(result, indent=2, ensure_ascii=False))
except HTTPError as e:
    print("HTTP status:", e.code)
    print("HTTP reason:", e.reason)
    body = e.read().decode("utf-8", errors="ignore")
    print("Error body:")
    print(body)