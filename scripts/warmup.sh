#!/data/data/com.termux/files/usr/bin/bash
set -e

echo "预热模型中..."

curl http://127.0.0.1:8081/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen35-vlm",
    "messages": [
      {
        "role": "user",
        "content": "你好"
      }
    ],
    "temperature": 0.2,
    "max_tokens": 16
  }'

echo
echo "预热完成"