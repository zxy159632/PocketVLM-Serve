#!/data/data/com.termux/files/usr/bin/bash
set -e

BASE_DIR="$HOME/zxy/mobile_llm"
WEB_DIR="$BASE_DIR/web_demo"
LOG_DIR="$BASE_DIR/logs"
PID_DIR="$BASE_DIR/pids"

mkdir -p "$LOG_DIR" "$PID_DIR"

cd "$WEB_DIR"

echo "启动静态网页服务 ..."
nohup python -m http.server 8090 --bind 127.0.0.1 \
  > "$LOG_DIR/web_server.log" 2>&1 &

echo $! > "$PID_DIR/web_server.pid"
echo "web server 已启动，PID=$(cat "$PID_DIR/web_server.pid")"