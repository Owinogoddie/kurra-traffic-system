#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

if [[ -f .env ]]; then
  set -a
  . ./.env
  set +a
fi

PORT="${DASHBOARD_PORT:-3000}"
CAMERA_ID="${1:-cam_101}"
URL="http://127.0.0.1:${PORT}/api/health/communication/${CAMERA_ID}"

echo "Checking service state..."
sudo systemctl is-active --quiet jicho-detector.service && echo "detector: active" || echo "detector: NOT active"
sudo systemctl is-active --quiet jicho-ui.service && echo "ui: active" || echo "ui: NOT active"

echo "\nChecking communication endpoint: ${URL}"
python3 - <<PY
import json
import urllib.request
import sys

url = "${URL}"
try:
    with urllib.request.urlopen(url, timeout=5) as r:
        body = r.read().decode("utf-8", errors="replace")
        data = json.loads(body)
except Exception as exc:
    print(f"ERROR: cannot reach communication endpoint: {exc}")
    sys.exit(2)

print(json.dumps(data, indent=2))

ok = bool(data.get("db_ok")) and bool(data.get("detector_stream_ok"))
if ok:
    print("\nCOMMUNICATION STATUS: OK")
    sys.exit(0)

print("\nCOMMUNICATION STATUS: DEGRADED")
if not data.get("db_ok"):
    print("- Database query from UI failed")
if not data.get("detector_stream_ok"):
    print("- Detector snapshot is missing or stale (>10s)")
sys.exit(1)
PY
