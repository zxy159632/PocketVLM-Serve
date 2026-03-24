#!/data/data/com.termux/files/usr/bin/bash
set -e

BASE_DIR="$HOME/zxy/mobile_llm"
SCRIPT_DIR="$BASE_DIR/scripts"
LOG_DIR="$BASE_DIR/logs"

mkdir -p "$LOG_DIR"

termux-wake-lock || true

echo "=============================="
echo "  Phone LLM Demo 一键启动"
echo "=============================="

bash "$SCRIPT_DIR/start_qwen_server.sh"

echo "等待 llama-server 就绪..."

READY=0
for i in $(seq 1 60); do
  if curl -s http://127.0.0.1:8081/v1/models > /dev/null 2>&1; then
    READY=1
    break
  fi
  sleep 2
done

if [ "$READY" -ne 1 ]; then
  echo "llama-server 启动超时，请检查日志："
  echo "$LOG_DIR/llama_server.log"
  exit 1
fi

echo "llama-server 已就绪"

bash "$SCRIPT_DIR/warmup.sh" || true
bash "$SCRIPT_DIR/start_web.sh"

echo
echo "=============================="
echo "  全部启动完成"
echo "=============================="
echo "模型服务: http://127.0.0.1:8081/v1/models"
echo "网页地址: http://127.0.0.1:8090/index.html"
echo
echo "如需查看日志："
echo "tail -f $LOG_DIR/llama_server.log"
echo "tail -f $LOG_DIR/web_server.log"