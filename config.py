# ============================================
# TRAFFIC SYSTEM CONFIGURATION
# ============================================

# --- Display ---
SHOW_FRAMES = False

# --- Which camera to run (change this to test different cameras) ---
ACTIVE_CAMERA = "cam_101"  # change to "cam_102" or "cam_103"

# --- Resolution ---
FRAME_WIDTH  = 854
FRAME_HEIGHT = 480

# --- Model ---
MODEL_PATH      = "yolov8m.pt"  # change to yolo11n.pt if you have it
CONFIDENCE      = 0.4
INFERENCE_SIZE  = 640
SKIP_FRAMES     = 2             # process every 2nd frame for speed

# --- Vehicle classes (COCO) ---
VEHICLE_CLASSES = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
}

# --- Camera video sources ---
CAMERAS = {
    "cam_101": "traffic_streams/recording_101.mp4",
    "cam_102": "traffic_streams/recording_102.mp4",
    "cam_103": "traffic_streams/recording_103.mp4",
}

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