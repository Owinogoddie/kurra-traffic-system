#!/usr/bin/env bash
set -euo pipefail

LOCAL_BASE="${1:-http://100.70.36.92:3000}"
NGROK_BASE="${2:-https://unrefutable-dianoetically-ismael.ngrok-free.dev}"
TIMEOUT_SECS="${TIMEOUT_SECS:-10}"

workdir="$(mktemp -d)"
trap 'rm -rf "$workdir"' EXIT

fetch() {
  local url="$1"
  local out_file="$2"
  local code
  if code=$(curl -sS -m "$TIMEOUT_SECS" -o "$out_file" -w '%{http_code}' "$url"); then
    echo "$code"
  else
    echo "000"
  fi
}

echo "== Endpoint checks =="
local_home_code=$(fetch "$LOCAL_BASE/" "$workdir/local_home.html")
ngrok_home_code=$(fetch "$NGROK_BASE/" "$workdir/ngrok_home.html")
local_j_code=$(fetch "$LOCAL_BASE/api/journeys" "$workdir/local_journeys.json")
ngrok_j_code=$(fetch "$NGROK_BASE/api/journeys" "$workdir/ngrok_journeys.json")

echo "local_home_http=$local_home_code"
echo "ngrok_home_http=$ngrok_home_code"
echo "local_journeys_http=$local_j_code"
echo "ngrok_journeys_http=$ngrok_j_code"

if [[ "$local_home_code" == "200" && "$ngrok_home_code" == "200" ]]; then
  local_home_sha=$(sha256sum "$workdir/local_home.html" | awk '{print $1}')
  ngrok_home_sha=$(sha256sum "$workdir/ngrok_home.html" | awk '{print $1}')
  echo "local_home_sha256=$local_home_sha"
  echo "ngrok_home_sha256=$ngrok_home_sha"
  if [[ "$local_home_sha" == "$ngrok_home_sha" ]]; then
    echo "home_page_match=yes"
  else
    echo "home_page_match=no"
  fi
fi

echo "\n== Journey API snippets =="
echo -n "local_journeys_preview="
head -c 300 "$workdir/local_journeys.json" || true
echo

echo -n "ngrok_journeys_preview="
head -c 300 "$workdir/ngrok_journeys.json" || true
echo

echo "\n== Local process checks =="
pgrep -af 'main.py|uvicorn|ngrok' || echo "No local matching processes found"

echo "\n== Local service checks =="
if command -v systemctl >/dev/null 2>&1; then
  for svc in jicho-detector.service jicho-ui.service; do
    echo "[$svc]"
    systemctl is-active "$svc" 2>/dev/null || true
    systemctl show "$svc" -p MainPID --no-pager 2>/dev/null || true
  done
else
  echo "systemctl not available"
fi

echo "\n== Verdict =="
if [[ "$local_j_code" == "200" && "$ngrok_j_code" == "200" ]]; then
  echo "API consistency: PASS (both endpoints returned 200 for /api/journeys)"
else
  echo "API consistency: FAIL (one endpoint is unhealthy or not pointing to same backend)"
fi
