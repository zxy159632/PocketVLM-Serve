#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ -n "${VENV_ACTIVATE:-}" ] && [ -f "$VENV_ACTIVATE" ]; then
  # shellcheck disable=SC1090
  source "$VENV_ACTIVATE"
fi

PYTHON_BIN="${PYTHON_BIN:-python}"
SERVER_BIN="${SERVER_BIN:-$ROOT_DIR/llama.cpp/build/bin/llama-server}"
MODEL_FILE="${MODEL_FILE:-$ROOT_DIR/models/Qwen_Qwen3.5-0.8B-Q4_K_M/Qwen_Qwen3.5-0.8B-Q4_K_M.gguf}"
MMPROJ_FILE="${MMPROJ_FILE:-$ROOT_DIR/models/Qwen_Qwen3.5-0.8B-Q4_K_M/mmproj-F16.gguf}"
USE_MMPROJ="${USE_MMPROJ:-1}"

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8081}"
CTX_SIZE="${CTX_SIZE:-8192}"
PARALLEL="${PARALLEL:-2}"
THREADS="${THREADS:-4}"
THREADS_BATCH="${THREADS_BATCH:-4}"
UBATCH="${UBATCH:-256}"
BATCH_SIZE="${BATCH_SIZE:-512}"
PREDICT="${PREDICT:--1}"
NO_WEBUI="${NO_WEBUI:-1}"
METRICS="${METRICS:-1}"
JINJA="${JINJA:-0}"
LOG_LEVEL="${LOG_LEVEL:-3}"
SERVER_EXTRA_ARGS="${SERVER_EXTRA_ARGS:-}"

PID_DIR="${PID_DIR:-$ROOT_DIR/pids}"
LOG_DIR="${LOG_DIR:-$ROOT_DIR/logs}"
PID_FILE="${PID_FILE:-$PID_DIR/llama_server.pid}"
LOG_FILE="${LOG_FILE:-$LOG_DIR/llama_server_bench.log}"
STARTUP_TIMEOUT="${STARTUP_TIMEOUT:-60}"
METRICS_URL="${METRICS_URL:-http://127.0.0.1:${PORT}/metrics}"

mkdir -p "$PID_DIR" "$LOG_DIR"

if [ ! -x "$SERVER_BIN" ]; then
  echo "[ERROR] llama-server not found or not executable: $SERVER_BIN"
  exit 1
fi

if [ ! -f "$MODEL_FILE" ]; then
  echo "[ERROR] model file not found: $MODEL_FILE"
  exit 1
fi

if [ -f "$PID_FILE" ]; then
  OLD_PID="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "[INFO] stopping old llama-server pid=$OLD_PID"
    kill "$OLD_PID" 2>/dev/null || true
    for _ in $(seq 1 20); do
      if kill -0 "$OLD_PID" 2>/dev/null; then
        sleep 0.5
      else
        break
      fi
    done
    if kill -0 "$OLD_PID" 2>/dev/null; then
      echo "[WARN] old process still alive, killing -9 pid=$OLD_PID"
      kill -9 "$OLD_PID" 2>/dev/null || true
    fi
  fi
  rm -f "$PID_FILE"
fi

CMD=(
  "$SERVER_BIN"
  -m "$MODEL_FILE"
  --host "$HOST"
  --port "$PORT"
  -c "$CTX_SIZE"
  -np "$PARALLEL"
  -t "$THREADS"
  -tb "$THREADS_BATCH"
  -ub "$UBATCH"
  -b "$BATCH_SIZE"
  -n "$PREDICT"
  --log-verbosity "$LOG_LEVEL"
  --reasoning off
  --reasoning-format none
)

if [ "$USE_MMPROJ" = "1" ] && [ -f "$MMPROJ_FILE" ]; then
  CMD+=(--mmproj "$MMPROJ_FILE")
fi

if [ "$METRICS" = "1" ]; then
  CMD+=(--metrics)
fi

if [ "$NO_WEBUI" = "1" ]; then
  CMD+=(--no-webui)
fi

if [ "$JINJA" = "1" ]; then
  CMD+=(--jinja)
fi

if [ -n "$SERVER_EXTRA_ARGS" ]; then
  # shellcheck disable=SC2206
  EXTRA_ARR=($SERVER_EXTRA_ARGS)
  CMD+=("${EXTRA_ARR[@]}")
fi

echo "[INFO] starting benchmark server"
echo "[INFO] SERVER_BIN=$SERVER_BIN"
echo "[INFO] MODEL_FILE=$MODEL_FILE"
if [ "$USE_MMPROJ" = "1" ] && [ -f "$MMPROJ_FILE" ]; then
  echo "[INFO] MMPROJ_FILE=$MMPROJ_FILE"
fi
echo "[INFO] HOST=$HOST PORT=$PORT CTX_SIZE=$CTX_SIZE PARALLEL=$PARALLEL THREADS=$THREADS THREADS_BATCH=$THREADS_BATCH UBATCH=$UBATCH BATCH_SIZE=$BATCH_SIZE"
echo "[INFO] PID_FILE=$PID_FILE"
echo "[INFO] LOG_FILE=$LOG_FILE"
echo "[INFO] extra args: ${SERVER_EXTRA_ARGS:-<none>}"

nohup "${CMD[@]}" > "$LOG_FILE" 2>&1 &
SERVER_PID=$!
echo "$SERVER_PID" > "$PID_FILE"

echo "[INFO] launched pid=$SERVER_PID, waiting for metrics endpoint: $METRICS_URL"

export START_BENCH_METRICS_URL="$METRICS_URL"
export START_BENCH_TIMEOUT="$STARTUP_TIMEOUT"
"$PYTHON_BIN" - <<'PY'
import os
import sys
import time
from urllib.request import urlopen

url = os.environ["START_BENCH_METRICS_URL"]
timeout_s = int(os.environ["START_BENCH_TIMEOUT"])
last_err = None

for _ in range(timeout_s * 2):
    try:
        with urlopen(url, timeout=3) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
        if body:
            print(f"[INFO] metrics is ready: {url}")
            sys.exit(0)
    except Exception as exc:
        last_err = exc
        time.sleep(0.5)

print(f"[ERROR] server did not become ready within {timeout_s}s: {last_err}")
sys.exit(1)
PY

echo "[INFO] benchmark server is ready"
echo "[INFO] tail log: tail -f $LOG_FILE"
