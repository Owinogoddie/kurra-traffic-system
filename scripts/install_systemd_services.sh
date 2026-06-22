#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE_DIR="$REPO_DIR/deploy/systemd"
SERVICE_USER="${SUDO_USER:-$USER}"
PYTHON_BIN="${PYTHON_BIN:-/usr/bin/python3}"

if [[ -f "$REPO_DIR/.env" ]]; then
  ENV_PYTHON_BIN=$(grep -E '^PYTHON_BIN=' "$REPO_DIR/.env" | tail -n 1 | cut -d '=' -f 2- || true)
  if [[ -n "$ENV_PYTHON_BIN" ]]; then
    PYTHON_BIN="$ENV_PYTHON_BIN"
  fi
fi

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Warning: PYTHON_BIN is not executable: $PYTHON_BIN"
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
    echo "Falling back to: $PYTHON_BIN"
  else
    echo "Error: python3 not found in PATH and PYTHON_BIN is invalid."
    exit 1
  fi
fi

render_unit() {
  local src="$1"
  local dst="$2"
  sed \
    -e "s|__REPO_DIR__|$REPO_DIR|g" \
    -e "s|__SERVICE_USER__|$SERVICE_USER|g" \
    -e "s|__PYTHON_BIN__|$PYTHON_BIN|g" \
    "$src" | sudo tee "$dst" >/dev/null
}

if [[ ! -d "$SERVICE_DIR" ]]; then
  echo "Missing service directory: $SERVICE_DIR"
  exit 1
fi

sudo mkdir -p /etc/systemd/system
render_unit "$SERVICE_DIR/jicho-detector.service" /etc/systemd/system/jicho-detector.service
render_unit "$SERVICE_DIR/jicho-ui.service" /etc/systemd/system/jicho-ui.service
sudo systemctl daemon-reload

echo "Installed service files:"
echo "  /etc/systemd/system/jicho-detector.service"
echo "  /etc/systemd/system/jicho-ui.service"
echo "Using:"
echo "  SERVICE_USER=$SERVICE_USER"
echo "  REPO_DIR=$REPO_DIR"
echo "  PYTHON_BIN=$PYTHON_BIN"
echo ""
echo "Next:"
echo "  sudo systemctl enable --now jicho-detector.service"
echo "  sudo systemctl enable --now jicho-ui.service"
