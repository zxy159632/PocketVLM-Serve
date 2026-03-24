#!/data/data/com.termux/files/usr/bin/bash
set -e

BASE_DIR="$HOME/zxy/mobile_llm"
PID_DIR="$BASE_DIR/pids"

stop_pid_file () {
  local pid_file="$1"
  local name="$2"

  if [ -f "$pid_file" ]; then
    PID=$(cat "$pid_file")
    if kill -0 "$PID" 2>/dev/null; then
      kill "$PID" || true
      echo "已停止 $name, PID=$PID"
    else
      echo "$name 的 PID 不存在或已退出: $PID"
    fi
    rm -f "$pid_file"
  else
    echo "未找到 $name 的 PID 文件"
  fi
}

stop_pid_file "$PID_DIR/web_server.pid" "web server"
stop_pid_file "$PID_DIR/llama_server.pid" "llama-server"

termux-wake-unlock || true