import cv2
import torch
import os
import time
from ultralytics import YOLO
from config import (
    SHOW_FRAMES, ACTIVE_CAMERA, FRAME_WIDTH, FRAME_HEIGHT,
    MODEL_PATH, CONFIDENCE, INFERENCE_SIZE, SKIP_FRAMES,
    VEHICLE_CLASSES, CAMERAS, CAMERA_LINES,
    LINE_COLORS, VEHICLE_COLORS
)
from db import init_db, save_journey

# ============================================
# SNAPSHOT SETTINGS
# ============================================
SNAPSHOT_DIR      = "snapshots"
SNAPSHOT_INTERVAL = 5  # save one frame every 5 seconds
os.makedirs(SNAPSHOT_DIR, exist_ok=True)

# ============================================
# STARTUP INFO
# ============================================
print("=" * 50)
print("  🚦 Kurra Traffic Detection")
print("=" * 50)
print(f"  CUDA available : {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"  GPU            : {torch.cuda.get_device_name(0)}")
print(f"  Camera         : {ACTIVE_CAMERA}")
print(f"  Resolution     : {FRAME_WIDTH}x{FRAME_HEIGHT}")
print(f"  Show frames    : {SHOW_FRAMES}")
print("=" * 50)

# ============================================
# INIT DATABASE
# ============================================
init_db()

# ============================================
# LOAD MODEL
# ============================================
print(f"Loading model: {MODEL_PATH}...")
model = YOLO(MODEL_PATH)
print("✅ Model loaded!")

# ============================================
# OPEN VIDEO SOURCE
# ============================================
source = CAMERAS[ACTIVE_CAMERA]
cap    = cv2.VideoCapture(source)

if not cap.isOpened():
    print(f"❌ Could not open: {source}")
    exit()

total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
fps          = int(cap.get(cv2.CAP_PROP_FPS))
print(f"✅ Video opened  : {source}")
print(f"   Frames        : {total_frames} | FPS: {fps}")

# ============================================
# LINE CROSSING HELPER
# ============================================
def get_side(px, py, x1, y1, x2, y2):
    """
    Returns which side of a line a point is on.
    +1 = one side, -1 = other side, 0 = on the line
    """
    val = (x2 - x1) * (py - y1) - (y2 - y1) * (px - x1)
    if val > 0: return  1
    if val < 0: return -1
    return 0

# ============================================
# TRACKING STATE
# ============================================
prev_sides   = {}   # { track_id: { road_name: last_side } }
crossings    = {}   # { track_id: [road1, road2, ...] }
saved_tracks = set()  # track IDs already saved to DB
journey_log  = []   # in-memory log for summary at end

lines = CAMERA_LINES[ACTIVE_CAMERA]

# ============================================
# SNAPSHOT STATE
# ============================================
last_snapshot_time = 0

# ============================================
# DRAW HELPERS
# ============================================
def draw_lines(frame):
    """Draw all road lines with labels on frame."""
    for road, (start, end) in lines.items():
        color = LINE_COLORS.get(road, (255, 255, 255))
        cv2.line(frame, start, end, color, 2)
        mid_x = (start[0] + end[0]) // 2
        mid_y = (start[1] + end[1]) // 2
        # Label background
        label = road.upper().replace("_", " ")
        (tw, th), _ = cv2.getTextSize(
            label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
        cv2.rectangle(frame,
            (mid_x - 2, mid_y - th - 10),
            (mid_x + tw + 2, mid_y - 4),
            (0, 0, 0), -1)
        cv2.putText(frame, label,
            (mid_x, mid_y - 8),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)


def draw_vehicle(frame, track_id, box, vtype, history):
    """Draw bounding box, label, center dot and journey history."""
    color       = VEHICLE_COLORS.get(vtype, (200, 200, 200))
    x1, y1, x2, y2 = box
    cx          = (x1 + x2) // 2
    cy          = (y1 + y2) // 2

    # Bounding box
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

    # Label with background
    label = f"{vtype} #{track_id}"
    (tw, th), _ = cv2.getTextSize(
        label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
    cv2.rectangle(frame,
        (x1, y1 - th - 10),
        (x1 + tw + 4, y1),
        color, -1)
    cv2.putText(frame, label,
        (x1 + 2, y1 - 4),
        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)

    # Center dot
    cv2.circle(frame, (cx, cy), 4, color, -1)

    # Journey history under box
    if history:
        journey_text = " → ".join(h.upper() for h in history)
        (tw2, _), _ = cv2.getTextSize(
            journey_text, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
        cv2.rectangle(frame,
            (x1, y2 + 2),
            (x1 + tw2 + 4, y2 + 18),
            (0, 0, 0), -1)
        cv2.putText(frame, journey_text,
            (x1 + 2, y2 + 14),
            cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)


def draw_stats(frame, frame_count, tracked_count):
    """Draw stats overlay in top left corner."""
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (310, 90), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

    cv2.putText(frame, f"Camera  : {ACTIVE_CAMERA}",
        (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1)
    cv2.putText(frame, f"Tracked : {tracked_count} vehicles",
        (8, 44), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1)
    cv2.putText(frame, f"Journeys: {len(journey_log)} saved",
        (8, 66), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 255, 136), 1)

    # Frame counter bottom right
    cv2.putText(frame,
        f"Frame {frame_count}/{total_frames}",
        (FRAME_WIDTH - 185, FRAME_HEIGHT - 10),
        cv2.FONT_HERSHEY_SIMPLEX, 0.42, (150, 150, 150), 1)


def save_snapshot(frame):
    """Save current frame as snapshot for dashboard."""
    global last_snapshot_time
    now = time.time()
    if now - last_snapshot_time >= SNAPSHOT_INTERVAL:
        path = os.path.join(SNAPSHOT_DIR, f"{ACTIVE_CAMERA}.jpg")
        cv2.imwrite(path, frame)
        last_snapshot_time = now


# ============================================
# MAIN LOOP
# ============================================
frame_count  = 0
skip_counter = 0
last_results = None

print(f"\n▶️  Processing... Press Q to quit | P to pause")
print("-" * 50)

while True:
    ret, frame = cap.read()

    # Loop video when it ends (for testing)
    if not ret:
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ret, frame = cap.read()
        if not ret:
            break

    frame_count  += 1
    skip_counter += 1

    # Resize to target resolution
    frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))

    # Save snapshot for dashboard (every 5 seconds)
    save_snapshot(frame)

    # ── FRAME SKIPPING FOR PERFORMANCE ──
    if skip_counter >= SKIP_FRAMES:
        skip_counter = 0
        results = model.track(
            frame,
            persist=True,
            tracker="bytetrack.yaml",
            conf=CONFIDENCE,
            imgsz=INFERENCE_SIZE,
            classes=list(VEHICLE_CLASSES.keys()),
            verbose=False,
            half=torch.cuda.is_available(),
        )
        last_results = results
    else:
        results = last_results

    # ── PROCESS DETECTIONS ──
    tracked_count = 0

    if (results and
        results[0].boxes is not None and
        results[0].boxes.id is not None):

        boxes         = results[0].boxes
        tracked_count = len(boxes)

        for i in range(len(boxes)):
            track_id        = int(boxes.id[i].item())
            cls             = int(boxes.cls[i].item())
            x1, y1, x2, y2 = map(int, boxes.xyxy[i].tolist())
            cx              = (x1 + x2) // 2
            cy              = (y1 + y2) // 2
            vtype           = VEHICLE_CLASSES.get(cls, "unknown")

            # Init state for new vehicle
            if track_id not in prev_sides:
                prev_sides[track_id] = {}
                crossings[track_id]  = []

            # ── CHECK EACH LINE ──
            for road, (start, end) in lines.items():
                curr_side = get_side(
                    cx, cy,
                    start[0], start[1],
                    end[0],   end[1]
                )
                prev = prev_sides[track_id].get(road)

                # Crossing detected!
                if (curr_side != 0 and
                    prev is not None and
                    prev != 0 and
                    curr_side != prev):

                    if road not in crossings[track_id]:
                        crossings[track_id].append(road)
                        print(f"  🚗 #{track_id} ({vtype}) "
                              f"crossed [{road.upper()}] | "
                              f"history: {crossings[track_id]}")

                        # ── JOURNEY COMPLETE (2 lines crossed) ──
                        if (len(crossings[track_id]) == 2 and
                            track_id not in saved_tracks):

                            from_road = crossings[track_id][0]
                            to_road   = crossings[track_id][1]

                            journey_log.append({
                                "track_id":  track_id,
                                "vehicle":   vtype,
                                "from_road": from_road,
                                "to_road":   to_road,
                            })

                            print(f"  ✅ JOURNEY: #{track_id} "
                                  f"{vtype} | "
                                  f"{from_road} → {to_road}")

                            # Save to DB
                            save_journey(
                                camera_id=ACTIVE_CAMERA,
                                track_id=track_id,
                                vehicle_type=vtype,
                                from_road=from_road,
                                to_road=to_road,
                            )

                            saved_tracks.add(track_id)

                prev_sides[track_id][road] = curr_side

            # Draw vehicle on frame
            draw_vehicle(
                frame, track_id,
                (x1, y1, x2, y2),
                vtype,
                crossings[track_id]
            )

    # ── DRAW LINES AND STATS ──
    draw_lines(frame)
    draw_stats(frame, frame_count, tracked_count)

    # ── SHOW FRAME ──
    if SHOW_FRAMES:
        cv2.imshow(f"Kurra Traffic — {ACTIVE_CAMERA}", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            print("\n🛑 Quit requested")
            break
        elif key == ord('p'):
            print("\n⏸  Paused — press any key to continue")
            cv2.waitKey(0)

    # Progress log every 100 frames
    if frame_count % 100 == 0:
        print(f"  📊 Frame {frame_count}/{total_frames} | "
              f"Journeys: {len(journey_log)}")

# ============================================
# CLEANUP & SUMMARY
# ============================================
cap.release()
cv2.destroyAllWindows()

print("\n" + "=" * 50)
print(f"  CAMERA  : {ACTIVE_CAMERA}")
print(f"  FRAMES  : {frame_count}")
print(f"  JOURNEYS: {len(journey_log)}")
print("=" * 50)
for j in journey_log:
    print(f"  #{j['track_id']:>4} {j['vehicle']:<12} "
          f"{j['from_road']} → {j['to_road']}")
print("=" * 50)