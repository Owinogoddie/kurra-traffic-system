# ============================================
# KURRA v2 — CONFIG
# ============================================

import os
from dotenv import load_dotenv

load_dotenv()

# --- Display ---
SHOW_FRAMES = False

# --- Active camera ---
ACTIVE_CAMERA = "cam_101"

# --- Dashboard ---
DASHBOARD_HOST = os.getenv("DASHBOARD_HOST", "0.0.0.0")
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "3000"))

# --- Resolution ---
FRAME_WIDTH  = 854
FRAME_HEIGHT = 480

# --- Model ---
MODEL_PATH     = "/home/jichosmart/yolo26s_batch1.engine"
CONFIDENCE     = 0.5
INFERENCE_SIZE = 640
SKIP_FRAMES    = 1

# --- Vehicle classes ---
VEHICLE_CLASSES = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
}

# --- Camera RTSP sources ---
def _camera_url(env_name, fallback):
    return os.getenv(env_name, fallback)


CAMERAS = {
    "cam_101": _camera_url("CAM_101_RTSP_URL", "rtsp://<username>:<password>@<camera-host>:554/Streaming/Channels/101"),
    # "cam_201": _camera_url("CAM_201_RTSP_URL", "rtsp://<username>:<password>@<camera-host>:554/Streaming/Channels/201"),
    # "cam_301": _camera_url("CAM_301_RTSP_URL", "rtsp://<username>:<password>@<camera-host>:554/Streaming/Channels/301"),
    # "cam_401": _camera_url("CAM_401_RTSP_URL", "rtsp://<username>:<password>@<camera-host>:554/Streaming/Channels/401"),
}

# --- Reconnect behaviour ---
RECONNECT_DELAY = 5      # seconds to wait before each retry
RECONNECT_EVERY = 1800   # proactively reopen stream every 30 min (0 = disabled)

# ============================================
# LINE COORDINATES  (originally drawn at 1280×720)
# ============================================
SRC_W, SRC_H = 1280, 720
SCALE_X = FRAME_WIDTH  / SRC_W
SCALE_Y = FRAME_HEIGHT / SRC_H

def scale(x, y):
    return (int(x * SCALE_X), int(y * SCALE_Y))

CAMERA_LINES = {
    "cam_101": {
        "town":     [scale(61,   119), scale(637,  135)],
        "5th_ave":  [scale(98,   220), scale(175,  717)],
        "hospital": [scale(1277, 198), scale(969,  160)],
        "ngong":    [scale(1272, 291), scale(236,  719)],
    },
}

# --- Line overlay colours (BGR) ---
LINE_COLORS = {
    "town":     (0,   255, 0  ),
    "ngong":    (255, 0,   0  ),
    "5th_ave":  (0,   165, 255),
    "hospital": (0,   0,   255),
}

# --- Bounding-box colours per vehicle type (BGR) ---
VEHICLE_COLORS = {
    "car":        (0,   255, 255),
    "truck":      (255, 0,   255),
    "bus":        (255, 165, 0  ),
    "motorcycle": (0,   255, 0  ),
    "unknown":    (200, 200, 200),
}

# --- Snapshot ---
SNAPSHOT_DIR      = "snapshots"
SNAPSHOT_INTERVAL = 1   # seconds
