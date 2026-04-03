#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ -n "${VENV_ACTIVATE:-}" ] && [ -f "$VENV_ACTIVATE" ]; then
  # shellcheck disable=SC1090
  source "$VENV_ACTIVATE"
fi

PYTHON_BIN="${PYTHON_BIN:-python}"
BENCH_SCRIPT="${BENCH_SCRIPT:-$ROOT_DIR/src/benchmarks/benchmark_openai_termux.py}"
URL="${URL:-http://127.0.0.1:8081/v1/chat/completions}"
METRICS_URL="${METRICS_URL:-http://127.0.0.1:8081/metrics}"
MODEL="${MODEL:-qwen35-vlm}"
PROMPT="${PROMPT:-请简洁描述图片内容。}"
IMAGE_FILE="${IMAGE_FILE:-$HOME/storage/dcim/Camera/test.jpg}"
REQUESTS="${REQUESTS:-2}"
MAX_TOKENS="${MAX_TOKENS:-64}"
TEMPERATURE="${TEMPERATURE:-0.2}"
PID_FILE="${PID_FILE:-$ROOT_DIR/pids/llama_server.pid}"
TIMEOUT="${TIMEOUT:-600}"
OUTPUT_DIR="${OUTPUT_DIR:-$ROOT_DIR/results/benchmark_runs/warmup}"
TAG="${TAG:-image_warmup}"

mkdir -p "$OUTPUT_DIR"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
OUTPUT_JSON="$OUTPUT_DIR/${TAG}_${TIMESTAMP}.json"

if [ ! -f "$BENCH_SCRIPT" ]; then
  echo "[ERROR] benchmark script not found: $BENCH_SCRIPT"
  exit 1
fi

if [ ! -f "$IMAGE_FILE" ]; then
  echo "[ERROR] image file not found: $IMAGE_FILE"
  echo "[HINT] set IMAGE_FILE=/your/path/test.jpg"
  exit 1
fi

echo "[INFO] image warmup begin"
echo "[INFO] image=$IMAGE_FILE"
echo "[INFO] output=$OUTPUT_JSON"

"$PYTHON_BIN" "$BENCH_SCRIPT" \
  --url "$URL" \
  --metrics-url "$METRICS_URL" \
  --model "$MODEL" \
  --case image_short_64 \
  --image "$IMAGE_FILE" \
  --image "$IMAGE_FILE" \
  --requests "$REQUESTS" \
  --concurrency 1 \
  --max-tokens "$MAX_TOKENS" \
  --temperature "$TEMPERATURE" \
  --pid-file "$PID_FILE" \
  --timeout "$TIMEOUT" \
  --output-json "$OUTPUT_JSON"

echo "[INFO] image warmup done: $OUTPUT_JSON"
