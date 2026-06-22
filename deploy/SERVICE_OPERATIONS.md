# Service Operations (Detector + UI on Same Machine)

This setup runs detector and UI as separate `systemd` services on the same host.

## Services

- Detector: `jicho-detector.service`
- UI: `jicho-ui.service`

## Install services

```bash
cd /home/tinybeaver/traffic_system
./scripts/install_systemd_services.sh
```

## Enable and start

```bash
sudo systemctl enable --now jicho-detector.service
sudo systemctl enable --now jicho-ui.service
```

## Manage with helper

```bash
./scripts/jichoctl.sh status all
./scripts/jichoctl.sh restart detector
./scripts/jichoctl.sh restart ui
./scripts/jichoctl.sh logs detector
./scripts/jichoctl.sh logs ui
./scripts/jichoctl.sh stop all
```

## Direct systemctl commands

```bash
sudo systemctl status jicho-detector.service
sudo systemctl status jicho-ui.service
sudo systemctl restart jicho-detector.service
sudo systemctl restart jicho-ui.service
```

## Environment variables used

Defined in `.env`:

- `DATABASE_URL`
- `DASHBOARD_HOST` (default: `0.0.0.0`)
- `DASHBOARD_PORT` (default: `3000`)
- `RUN_DASHBOARD_IN_MAIN=0` (important: keeps detector and UI separate)
- `CAM_101_RTSP_URL`
- `MODEL_PATH`

## Logs

- Detector file log: `logs/detector.log`
- UI file log: `logs/ui.log`
- Journal logs:

```bash
sudo journalctl -u jicho-detector.service -f
sudo journalctl -u jicho-ui.service -f
```

## Notes

- Unit files currently use `User=tinybeaver`. If deploying with another Linux user, update both service files before install.
- If Python packages are in a virtual environment, set `PYTHON_BIN` in `.env` (for example `/home/tinybeaver/traffic_system/.venv/bin/python`).
