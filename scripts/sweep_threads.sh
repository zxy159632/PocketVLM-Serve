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
START_SCRIPT="${START_SCRIPT:-$ROOT_DIR/scripts/start_bench.sh}"
WARMUP_IMAGE_SCRIPT="${WARMUP_IMAGE_SCRIPT:-$ROOT_DIR/scripts/warmup_image.sh}"
URL="${URL:-http://127.0.0.1:8081/v1/chat/completions}"
METRICS_URL="${METRICS_URL:-http://127.0.0.1:8081/metrics}"
MODEL="${MODEL:-qwen35-vlm}"
PID_FILE="${PID_FILE:-$ROOT_DIR/pids/llama_server.pid}"
IMAGE_FILE="${IMAGE_FILE:-$HOME/storage/dcim/Camera/test.jpg}"
TIMEOUT="${TIMEOUT:-600}"
# 测试-t -tb
# THREAD_SWEEP="${THREAD_SWEEP:-2:4 4:4 4:6 6:6}"
# UBATCH_SWEEP="${UBATCH_SWEEP:-256}"
# 测试-ub
THREAD_SWEEP="${THREAD_SWEEP:-4:4}"
UBATCH_SWEEP="${UBATCH_SWEEP:-128 256 512}"

CASES="${CASES:-text_short_64 text_medium_128 image_short_64}"
PARALLEL="${PARALLEL:-2}"
CTX_SIZE="${CTX_SIZE:-8192}"
BATCH_SIZE="${BATCH_SIZE:-512}"
TEXT_REQUESTS="${TEXT_REQUESTS:-10}"
IMAGE_REQUESTS="${IMAGE_REQUESTS:-5}"
CONCURRENCY_TEXT="${CONCURRENCY_TEXT:-1}"
CONCURRENCY_IMAGE="${CONCURRENCY_IMAGE:-1}"
TEXT_WARMUP_REQUESTS="${TEXT_WARMUP_REQUESTS:-1}"
ENABLE_IMAGE_WARMUP="${ENABLE_IMAGE_WARMUP:-1}"
TEXT_WARMUP_PROMPT="${TEXT_WARMUP_PROMPT:-请用一句话介绍Transformer。}"
RESULT_TAG="${RESULT_TAG:-threads_sweep}"
RESULTS_ROOT="${RESULTS_ROOT:-$ROOT_DIR/results/benchmark_runs/${RESULT_TAG}_$(date +%Y%m%d_%H%M%S)}"

mkdir -p "$RESULTS_ROOT"

if [ ! -f "$BENCH_SCRIPT" ]; then
  echo "[ERROR] benchmark script not found: $BENCH_SCRIPT"
  exit 1
fi
if [ ! -x "$START_SCRIPT" ]; then
  echo "[ERROR] start script not executable: $START_SCRIPT"
  exit 1
fi
if [ ! -x "$WARMUP_IMAGE_SCRIPT" ]; then
  echo "[ERROR] warmup image script not executable: $WARMUP_IMAGE_SCRIPT"
  exit 1
fi

run_text_warmup() {
  local out_json="$1"
  "$PYTHON_BIN" "$BENCH_SCRIPT" \
    --url "$URL" \
    --metrics-url "$METRICS_URL" \
    --model "$MODEL" \
    --prompt "$TEXT_WARMUP_PROMPT" \
    --requests "$TEXT_WARMUP_REQUESTS" \
    --concurrency 1 \
    --max-tokens 32 \
    --temperature 0.2 \
    --pid-file "$PID_FILE" \
    --timeout "$TIMEOUT" \
    --output-json "$out_json" >/dev/null
}

run_case() {
  local case_name="$1"
  local out_json="$2"
  local reqs conc
  if [[ "$case_name" == image_* ]]; then
    reqs="$IMAGE_REQUESTS"
    conc="$CONCURRENCY_IMAGE"
    "$PYTHON_BIN" "$BENCH_SCRIPT" \
      --url "$URL" \
      --metrics-url "$METRICS_URL" \
      --model "$MODEL" \
      --case "$case_name" \
      --image "$IMAGE_FILE" \
      --requests "$reqs" \
      --concurrency "$conc" \
      --pid-file "$PID_FILE" \
      --timeout "$TIMEOUT" \
      --output-json "$out_json"
  else
    reqs="$TEXT_REQUESTS"
    conc="$CONCURRENCY_TEXT"
    "$PYTHON_BIN" "$BENCH_SCRIPT" \
      --url "$URL" \
      --metrics-url "$METRICS_URL" \
      --model "$MODEL" \
      --case "$case_name" \
      --requests "$reqs" \
      --concurrency "$conc" \
      --pid-file "$PID_FILE" \
      --timeout "$TIMEOUT" \
      --output-json "$out_json"
  fi
}

echo "[INFO] sweep results dir: $RESULTS_ROOT"

for combo in $THREAD_SWEEP; do
  THREADS="${combo%%:*}"
  THREADS_BATCH="${combo##*:}"

  for UBATCH in $UBATCH_SWEEP; do
    RUN_NAME="t${THREADS}_tb${THREADS_BATCH}_ub${UBATCH}"
    RUN_DIR="$RESULTS_ROOT/$RUN_NAME"
    mkdir -p "$RUN_DIR"

    echo "=================================================="
    echo "[INFO] start combo: $RUN_NAME"

    export THREADS THREADS_BATCH UBATCH PARALLEL CTX_SIZE BATCH_SIZE PID_FILE
    export LOG_FILE="$ROOT_DIR/logs/${RUN_NAME}.log"
    export SERVER_EXTRA_ARGS="${SERVER_EXTRA_ARGS:-}"
    "$START_SCRIPT"

    echo "[INFO] text warmup"
    run_text_warmup "$RUN_DIR/warmup_text.json"

    if [ "$ENABLE_IMAGE_WARMUP" = "1" ] && printf '%s
' $CASES | grep -q '^image_'; then
      echo "[INFO] image warmup"
      OUTPUT_DIR="$RUN_DIR" IMAGE_FILE="$IMAGE_FILE" PID_FILE="$PID_FILE" URL="$URL" METRICS_URL="$METRICS_URL" MODEL="$MODEL" "$WARMUP_IMAGE_SCRIPT" >/dev/null
    fi

    cat > "$RUN_DIR/run_env.txt" <<ENV
THREADS=$THREADS
THREADS_BATCH=$THREADS_BATCH
UBATCH=$UBATCH
PARALLEL=$PARALLEL
CTX_SIZE=$CTX_SIZE
BATCH_SIZE=$BATCH_SIZE
URL=$URL
METRICS_URL=$METRICS_URL
MODEL=$MODEL
IMAGE_FILE=$IMAGE_FILE
CASES=$CASES
TEXT_REQUESTS=$TEXT_REQUESTS
IMAGE_REQUESTS=$IMAGE_REQUESTS
CONCURRENCY_TEXT=$CONCURRENCY_TEXT
CONCURRENCY_IMAGE=$CONCURRENCY_IMAGE
ENV

    for case_name in $CASES; do
      OUT_JSON="$RUN_DIR/${case_name}.json"
      echo "[INFO] running case=$case_name"
      run_case "$case_name" "$OUT_JSON"
      echo "[INFO] compact summary -> $OUT_JSON"
      "$PYTHON_BIN" "$ROOT_DIR/src/benchmarks/report_summary.py" "$OUT_JSON" | tee "$RUN_DIR/${case_name}.summary.txt"
    done
  done
done

echo "[INFO] sweep finished: $RESULTS_ROOT"
