#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE_DIR="$REPO_DIR/deploy/systemd"
SERVICE_USER="${SUDO_USER:-$USER}"

render_unit() {
  local src="$1"
  local dst="$2"
  sed \
    -e "s|__REPO_DIR__|$REPO_DIR|g" \
    -e "s|__SERVICE_USER__|$SERVICE_USER|g" \
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
echo ""
echo "Next:"
echo "  sudo systemctl enable --now jicho-detector.service"
echo "  sudo systemctl enable --now jicho-ui.service"
