#!/usr/bin/env bash
set -euo pipefail

ACTION=${1:-}
TARGET=${2:-all}

if [[ -z "$ACTION" ]]; then
  echo "Usage: $0 <start|stop|restart|status|logs|enable|disable> [detector|ui|all]"
  exit 1
fi

case "$TARGET" in
  detector) SERVICES=(jicho-detector.service) ;;
  ui) SERVICES=(jicho-ui.service) ;;
  all) SERVICES=(jicho-detector.service jicho-ui.service) ;;
  *)
    echo "Invalid target: $TARGET"
    echo "Use: detector | ui | all"
    exit 1
    ;;
esac

if [[ "$ACTION" == "logs" ]]; then
  if [[ "$TARGET" == "detector" ]]; then
    sudo journalctl -u jicho-detector.service -f
    exit 0
  fi
  if [[ "$TARGET" == "ui" ]]; then
    sudo journalctl -u jicho-ui.service -f
    exit 0
  fi
  sudo journalctl -u jicho-detector.service -u jicho-ui.service -f
  exit 0
fi

for svc in "${SERVICES[@]}"; do
  case "$ACTION" in
    start|stop|restart|status|enable|disable)
      sudo systemctl "$ACTION" "$svc"
      ;;
    *)
      echo "Invalid action: $ACTION"
      echo "Use: start | stop | restart | status | logs | enable | disable"
      exit 1
      ;;
  esac
done
