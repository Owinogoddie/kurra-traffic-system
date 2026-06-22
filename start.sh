#!/bin/bash
# ============================================
# Jicho Smart v2 � Start Script
# ============================================

set -e

cd "$(dirname "$0")"
# source venv/bin/activate

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo "=================================================="
echo "  ?? Jicho Smart v2"
echo "=================================================="

# -- .env check --
if [ ! -f .env ]; then
    echo -e "${RED}? .env not found!${NC}"
    exit 1
fi

set -a
. ./.env
set +a

DASHBOARD_HOST="${DASHBOARD_HOST:-0.0.0.0}"
DASHBOARD_PORT="${DASHBOARD_PORT:-3000}"

# -- PostgreSQL check --
if ! pg_isready -q; then
    echo -e "${YELLOW}??  PostgreSQL not running � starting it...${NC}"
    sudo systemctl start postgresql
    sleep 2
fi
echo -e "${GREEN}? PostgreSQL ready${NC}"

# -- Create folders --
mkdir -p snapshots logs static

STATE_DIR="logs/pids"
mkdir -p "$STATE_DIR"

stop_pid_file() {
    local pidfile="$1"
    if [ -f "$pidfile" ]; then
        local pid
        pid=$(cat "$pidfile")
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            echo -e "${YELLOW}Stopping prior process PID ${pid}${NC}"
            kill "$pid" 2>/dev/null || true
        fi
        rm -f "$pidfile"
    fi
}

# -- Stop only previously managed processes --
stop_pid_file "$STATE_DIR/main.pid"
stop_pid_file "$STATE_DIR/dashboard.pid"
stop_pid_file "$STATE_DIR/ngrok.pid"
sleep 1

# -- Init DB --
echo -e "${GREEN}??  Initialising database...${NC}"
python3 -c "from db import init_db; init_db()"

# -- Start detection --
echo -e "${GREEN}??  Starting detection...${NC}"
python3 main.py > logs/detection.log 2>&1 &
MAIN_PID=$!
echo "$MAIN_PID" > "$STATE_DIR/main.pid"
sleep 3

if ! kill -0 $MAIN_PID 2>/dev/null; then
    echo -e "${RED}? Detection failed � check logs/detection.log${NC}"
    exit 1
fi
echo -e "${GREEN}? Detection running (PID $MAIN_PID)${NC}"

# -- Start dashboard --
echo -e "${GREEN}??  Starting dashboard...${NC}"
# venv/bin//home/jichosmart/.local/bin/uvicorn dashboard:app --host "$DASHBOARD_HOST" --port "$DASHBOARD_PORT" > logs/dashboard.log 2>&1 &
/home/jichosmart/.local/bin/uvicorn dashboard:app --host "$DASHBOARD_HOST" --port "$DASHBOARD_PORT" > logs/dashboard.log 2>&1 &
DASH_PID=$!
echo "$DASH_PID" > "$STATE_DIR/dashboard.pid"
sleep 3

if curl -s "http://localhost:${DASHBOARD_PORT}/" > /dev/null 2>&1; then
    echo -e "${GREEN}? Dashboard running (PID $DASH_PID)${NC}"
else
    echo -e "${RED}? Dashboard failed � check logs/dashboard.log${NC}"
    kill $MAIN_PID 2>/dev/null
    exit 1
fi

# -- Start ngrok --
echo -e "${GREEN}??  Starting ngrok...${NC}"
ngrok http "$DASHBOARD_PORT" > /dev/null 2>&1 &
NGROK_PID=$!
echo "$NGROK_PID" > "$STATE_DIR/ngrok.pid"
sleep 4

NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    for t in d.get('tunnels', []):
        if t['proto'] == 'https':
            print(t['public_url'])
            sys.exit()
    tunnels = d.get('tunnels', [])
    if tunnels:
        print(tunnels[0]['public_url'])
    else:
        print('ngrok not ready')
except:
    print('ngrok not ready')
")

IP=$(hostname -I | awk '{print $1}')

echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  ?? Jicho Smart v2 is running!${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""
echo -e "  ${GREEN}Local machine  ${NC}: http://localhost:${DASHBOARD_PORT}"
echo -e "  ${GREEN}Local network  ${NC}: http://$IP:${DASHBOARD_PORT}"
echo -e "  ${GREEN}Internet (ngrok)${NC}: $NGROK_URL"
echo ""
echo -e "  Logs: tail -f logs/detection.log"
echo -e "        tail -f logs/dashboard.log"
echo ""
echo -e "  Press ${RED}CTRL+C${NC} to stop everything"
echo -e "${CYAN}========================================${NC}"

# -- Graceful shutdown --
trap "
  echo ''
  echo 'Stopping all services...'
  kill $MAIN_PID $DASH_PID $NGROK_PID 2>/dev/null
    rm -f $STATE_DIR/main.pid $STATE_DIR/dashboard.pid $STATE_DIR/ngrok.pid
  echo '? All stopped'
  exit 0
" INT TERM

wait