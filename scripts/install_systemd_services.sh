#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE_DIR="$REPO_DIR/deploy/systemd"

if [[ ! -d "$SERVICE_DIR" ]]; then
  echo "Missing service directory: $SERVICE_DIR"
  exit 1
fi

sudo mkdir -p /etc/systemd/system
sudo cp "$SERVICE_DIR/jicho-detector.service" /etc/systemd/system/jicho-detector.service
sudo cp "$SERVICE_DIR/jicho-ui.service" /etc/systemd/system/jicho-ui.service
sudo systemctl daemon-reload

echo "Installed service files:"
echo "  /etc/systemd/system/jicho-detector.service"
echo "  /etc/systemd/system/jicho-ui.service"
echo ""
echo "Next:"
echo "  sudo systemctl enable --now jicho-detector.service"
echo "  sudo systemctl enable --now jicho-ui.service"
