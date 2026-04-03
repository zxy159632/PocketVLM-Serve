#!/data/data/com.termux/files/usr/bin/bash
set -e

BASE_DIR="$HOME/zxy/mobile_llm"
MODEL_DIR="$BASE_DIR/models/Qwen_Qwen3.5-0.8B-Q4_K_M"
LOG_DIR="$BASE_DIR/logs"
PID_DIR="$BASE_DIR/pids"

mkdir -p "$LOG_DIR" "$PID_DIR"

MODEL_FILE="$MODEL_DIR/Qwen3.5-0.8B-Q4_K_M.gguf"
MMPROJ_FILE="$MODEL_DIR/mmproj-F16.gguf"

if [ ! -f "$MODEL_FILE" ]; then
  echo "找不到主模型文件: $MODEL_FILE"
  exit 1
fi

if [ ! -f "$MMPROJ_FILE" ]; then
  echo "找不到 mmproj 文件: $MMPROJ_FILE"
  exit 1
fi

cd "$BASE_DIR/llama.cpp"

echo "启动 llama-server ..."
nohup ./build/bin/llama-server \
  -m "$MODEL_FILE" \
  --mmproj "$MMPROJ_FILE" \
  --host 0.0.0.0 \
  --port 8081 \
  -c 8192 \
  --reasoning off \
  --reasoning-format none \
  --alias qwen35-vlm \
  --metrics \
  > "$LOG_DIR/llama_server.log" 2>&1 &

echo $! > "$PID_DIR/llama_server.pid"
echo "llama-server 已启动，PID=$(cat "$PID_DIR/llama_server.pid")"