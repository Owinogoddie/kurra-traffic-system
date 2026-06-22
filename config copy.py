# ============================================
# KURRA v2 — CONFIG
# ============================================

# --- Display (set True to open an OpenCV window) ---
SHOW_FRAMES = True

# --- Active camera ---
ACTIVE_CAMERA = "cam_101"

# --- Resolution ---
FRAME_WIDTH  = 854
FRAME_HEIGHT = 480

# --- Model ---
MODEL_PATH     = "/home/jichosmart/yolo26s_batch1.engine"
CONFIDENCE     = 0.5
INFERENCE_SIZE = 640
SKIP_FRAMES    = 2      # run inference every Nth frame

# --- Vehicle classes (COCO ids — adjust if your engine uses different ids) ---
VEHICLE_CLASSES = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
}

# --- Camera video sources ---
CAMERAS = {
    "cam_101": "/home/jichosmart/kurra/traffic_streams/recording_101.mp4",
}

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
    "town":     (0,   255, 0  ),   # green
    "ngong":    (255, 0,   0  ),   # blue
    "5th_ave":  (0,   165, 255),   # orange
    "hospital": (0,   0,   255),   # red
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
SNAPSHOT_INTERVAL = 5   # seconds