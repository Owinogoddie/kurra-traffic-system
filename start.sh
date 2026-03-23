#!/bin/bash
cd ~/KURRA/traffic-system
source venv_traffic/bin/activate

echo "Starting Kurra Traffic System..."
mkdir -p snapshots

# Kill anything on port 8000
fuser -k 8000/tcp 2>/dev/null
sleep 1

# ── AI DETECTION ──
echo "Starting AI detection..."
python3 main.py &
MAIN_PID=$!
sleep 2

if ! kill -0 $MAIN_PID 2>/dev/null; then
    echo "❌ main.py failed to start — aborting"
    exit 1
fi
echo "✅ Detection running (PID $MAIN_PID)"
sleep 3

# ── DASHBOARD ──
echo "Starting dashboard..."
venv_traffic/bin/python3 -m uvicorn dashboard:app --host 0.0.0.0 --port 8000 &
DASH_PID=$!
sleep 3

if curl -s http://localhost:8000/ > /dev/null 2>&1; then
    echo "✅ Dashboard running (PID $DASH_PID)"
else
    echo "❌ Dashboard failed to start — check dashboard.py"
    kill $MAIN_PID 2>/dev/null
    exit 1
fi

# ── NGROK ──
echo "Starting ngrok..."
ngrok http 8000 > /dev/null &
NGROK_PID=$!
sleep 3

NGROK_URL=$(curl -s http://localhost:4040/api/tunnels \
    | python3 -c "import sys,json; d=json.load(sys.stdin); \
      print(d['tunnels'][0]['public_url'] if d.get('tunnels') else 'ngrok not ready')")

IP=$(hostname -I | awk '{print $1}')

echo ""
echo "======================================="
echo "  Kurra Traffic System is running!"
echo "======================================="
echo ""
echo "  Local network : http://$IP:8000"
echo "  Internet      : $NGROK_URL"
echo ""
echo "  Press CTRL+C to stop everything"
echo "======================================="

trap "echo 'Stopping...'; kill $MAIN_PID $DASH_PID $NGROK_PID 2>/dev/null; exit" INT TERM
wait