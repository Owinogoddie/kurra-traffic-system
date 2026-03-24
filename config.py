# ============================================
# TRAFFIC SYSTEM CONFIGURATION
# ============================================


# --- Display ---
SHOW_FRAMES = False


# --- Resolution ---
FRAME_WIDTH  = 854
FRAME_HEIGHT = 480


# --- Model ---
MODEL_PATH     = "yolo11n.pt"   # fast nano model — best for 3 parallel cameras
CONFIDENCE     = 0.35           # slightly lower to catch more vehicles
INFERENCE_SIZE = 416            # faster than 640, fine for traffic detection
SKIP_FRAMES    = 3              # process every 3rd frame (model is faster now)


# --- Vehicle classes (COCO) ---
VEHICLE_CLASSES = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
}


# --- Camera video sources ---
# To add a camera    : add an entry here AND in CAMERA_LINES below
# To remove a camera : comment it out here AND in CAMERA_LINES below
# run_all.py automatically runs whatever cameras are uncommented here
CAMERAS = {
    "cam_101": "traffic_streams/recording_101.mp4",
    "cam_102": "traffic_streams/recording_102.mp4",
    "cam_103": "traffic_streams/recording_103.mp4",
}

# --- Single camera mode ---
# Only used by main.py — change this to test one camera at a time
ACTIVE_CAMERA = "cam_101"


# ============================================
# LINE COORDINATES (original at 1280x720)
# Auto scaled to 854x480
# ============================================
SCALE_X = 854 / 1280
SCALE_Y = 480 / 720


def scale(x, y):
    return (int(x * SCALE_X), int(y * SCALE_Y))


CAMERA_LINES = {
    "cam_101": {
        "town":     [scale(111,  199), scale(637,  135)],
        "5th_ave":  [scale(143,  226), scale(6,    711)],
        "hospital": [scale(917,  175), scale(1277, 329)],
        "ngong":    [scale(1272, 500), scale(0,    680)],
    },
    "cam_102": {
        "5th_ave":  [scale(660,  224), scale(940,  240)],
        "ngong":    [scale(294,  311), scale(1,    697)],
        "town":     [scale(1122, 279), scale(1273, 705)],
        "hospital": [scale(0,    693), scale(1216, 685)],
    },
    "cam_103": {
        "ngong":    [scale(1055, 216), scale(257,  299)],
        "hospital": [scale(194,  321), scale(1,    711)],
        "town":     [scale(1275, 500), scale(15,   700)],
    },
}


# --- Line colors (BGR) ---
LINE_COLORS = {
    "town":     (0,   255, 0  ),  # Green
    "ngong":    (255, 0,   0  ),  # Blue
    "5th_ave":  (0,   165, 255),  # Orange
    "hospital": (0,   0,   255),  # Red
}


# --- Vehicle colors (BGR) ---
VEHICLE_COLORS = {
    "car":        (0,   255, 255),  # Yellow
    "truck":      (255, 0,   255),  # Magenta
    "bus":        (255, 165, 0  ),  # Orange
    "motorcycle": (0,   255, 0  ),  # Green
    "unknown":    (200, 200, 200),  # Grey
}


# ============================================
# JOURNEY OWNERSHIP
# Defines which camera is the single authority
# for each from_road → to_road route.
#
# This prevents double-counting when the same
# vehicle is visible on multiple cameras.
#
# Rules:
#   - Every possible route should have one owner
#   - The owner should be the camera with the
#     clearest view of that specific movement
#   - If a route is missing here, run_all.py will
#     still save it but print a ⚠️  warning
#
# To add a new camera or route: add entries below
# following the same (from_road, to_road) pattern
# ============================================
JOURNEY_OWNERSHIP = {
    # cam_101 — best view of Town entry/exit + Hospital↔Town side
    ("town",     "ngong"   ): "cam_101",
    ("town",     "5th_ave" ): "cam_101",
    ("town",     "hospital"): "cam_101",
    ("hospital", "5th_ave" ): "cam_101",
    ("hospital", "town"    ): "cam_101",

    # cam_102 — best view of 5th Ave movements + Ngong→5th
    ("5th_ave",  "town"    ): "cam_102",
    ("5th_ave",  "ngong"   ): "cam_102",
    ("5th_ave",  "hospital"): "cam_102",
    ("ngong",    "5th_ave" ): "cam_102",

    # cam_103 — best view of Ngong entry/exit + Hospital↔Ngong
    ("ngong",    "town"    ): "cam_103",
    ("ngong",    "hospital"): "cam_103",
    ("hospital", "ngong"   ): "cam_103",
}
