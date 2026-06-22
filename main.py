"""
Kurra v2 — single-camera detection + line-crossing tracker.
RTSP live stream with silent infinite reconnect.
Launches dashboard in a background thread (same process = shared frame_slot).
"""

import os
import time
import queue
import threading
from urllib.parse import urlsplit

import cv2
import numpy as np
import uvicorn
from ultralytics import YOLO

from config import (
    SHOW_FRAMES, ACTIVE_CAMERA,
    FRAME_WIDTH, FRAME_HEIGHT,
    MODEL_PATH, CONFIDENCE, INFERENCE_SIZE, SKIP_FRAMES,
    VEHICLE_CLASSES, CAMERAS, CAMERA_LINES,
    LINE_COLORS, VEHICLE_COLORS,
    SNAPSHOT_DIR, SNAPSHOT_INTERVAL,
    DASHBOARD_HOST, DASHBOARD_PORT,
)
from db import init_db, save_journey
from stream import RtspStream
import frame_slot

# ── Setup ─────────────────────────────────────────────────────────────────────
os.makedirs(SNAPSHOT_DIR, exist_ok=True)
init_db()

print("=" * 52)
print("  🚦 Jicho Smart v2  —  LIVE RTSP")
print(f"  Camera : {ACTIVE_CAMERA}")
print("=" * 52)

model  = YOLO(MODEL_PATH, task="detect")
labels = model.names
print(f"✅ Model loaded: {MODEL_PATH}")

# ── Start dashboard in background (same process → shared frame_slot) ──────────
from dashboard import app as dashboard_app

def _start_dashboard():
    uvicorn.run(
        dashboard_app,
        host=DASHBOARD_HOST,
        port=DASHBOARD_PORT,
        log_level="warning",
    )

if os.getenv("RUN_DASHBOARD_IN_MAIN", "0") == "1":
    threading.Thread(target=_start_dashboard, daemon=True, name="dashboard").start()
    print(f"✅ Dashboard running at http://{DASHBOARD_HOST}:{DASHBOARD_PORT}")
else:
    print("ℹ️ Dashboard launch in main.py disabled (RUN_DASHBOARD_IN_MAIN != 1)")


def _safe_rtsp_label(url: str) -> str:
    parts = urlsplit(url)
    host = parts.hostname or "camera-host"
    port = f":{parts.port}" if parts.port else ""
    return f"{parts.scheme}://{host}{port}{parts.path}"

# ── Start RTSP stream ─────────────────────────────────────────────────────────
rtsp = RtspStream(CAMERAS[ACTIVE_CAMERA])
rtsp.start()
print(f"✅ RTSP stream started: {_safe_rtsp_label(CAMERAS[ACTIVE_CAMERA])}")

LINES = CAMERA_LINES[ACTIVE_CAMERA]

# ── Create window ─────────────────────────────────────────────────────────────
WIN = f"Kurra v2 — {ACTIVE_CAMERA}"
if SHOW_FRAMES:
    cv2.namedWindow(WIN, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WIN, FRAME_WIDTH, FRAME_HEIGHT)

# ── Helpers ───────────────────────────────────────────────────────────────────
def side_of_line(pt, p1, p2):
    cross = (p2[0]-p1[0])*(pt[1]-p1[1]) - (p2[1]-p1[1])*(pt[0]-p1[0])
    return 1 if cross > 0 else (-1 if cross < 0 else 0)

def segments_intersect(a, b, p1, p2):
    d1 = side_of_line(p1, a, b)
    d2 = side_of_line(p2, a, b)
    d3 = side_of_line(a, p1, p2)
    d4 = side_of_line(b, p1, p2)
    return (d1 * d2 < 0) and (d3 * d4 < 0)

# ── Threading ─────────────────────────────────────────────────────────────────
result_q = queue.Queue(maxsize=8)
stop_evt  = threading.Event()

def inference_worker():
    n        = 0
    last_res = None
    while not stop_evt.is_set():
        try:
            frame = rtsp.queue.get(timeout=5)
        except queue.Empty:
            continue
        if frame is None:
            result_q.put(None)
            return
        n += 1
        if n % SKIP_FRAMES == 0:
            res      = model.track(frame, persist=True, verbose=False,
                                   conf=CONFIDENCE, imgsz=INFERENCE_SIZE)
            last_res = res
            result_q.put((frame.copy(), res, False))
        else:
            result_q.put((frame.copy(), last_res, True))

t_inference = threading.Thread(target=inference_worker, daemon=True)
t_inference.start()

# ── Tracking state ────────────────────────────────────────────────────────────
prev_centroids = {}
journeys       = {}
journey_log    = []

last_snap_time = 0
frame_number   = 0
fps_buf        = []
avg_fps        = 0.0

BOX_COLORS = [
    (164,120,87),(68,148,228),(93,97,209),(178,182,133),(88,159,106),
    (96,202,231),(159,124,168),(169,162,241),(98,118,150),(172,176,184),
]

print(f"\n▶️  Running — press Q to quit\n" + "-"*52)

# ── Main loop ─────────────────────────────────────────────────────────────────
while True:
    t0 = time.perf_counter()

    try:
        item = result_q.get(timeout=10)
    except queue.Empty:
        continue

    if item is None:
        print("Stream ended.")
        break

    frame, results, skipped = item
    frame_number += 1
    current_ids  = set()

    # ── Draw lines ──
    for name, (p1, p2) in LINES.items():
        color = LINE_COLORS.get(name, (255, 255, 255))
        cv2.line(frame, p1, p2, color, 2)
        mid = ((p1[0]+p2[0])//2, (p1[1]+p2[1])//2)
        cv2.putText(frame, name.upper(), mid,
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)

    # ── Detections ──
    if (results is not None and
            results[0].boxes is not None and
            results[0].boxes.id is not None):

        boxes   = results[0].boxes.xyxy.cpu().numpy()
        ids     = results[0].boxes.id.cpu().numpy().astype(int)
        classes = results[0].boxes.cls.cpu().numpy().astype(int)
        confs   = results[0].boxes.conf.cpu().numpy()

        for box, tid, cls_idx, conf in zip(boxes, ids, classes, confs):
            if conf < CONFIDENCE:
                continue

            x1, y1, x2, y2 = box.astype(int)
            tid      = int(tid)
            vtype    = VEHICLE_CLASSES.get(int(cls_idx), "unknown")
            color    = BOX_COLORS[tid % len(BOX_COLORS)]
            cx, cy   = (x1+x2)//2, (y1+y2)//2
            centroid = (cx, cy)

            current_ids.add(tid)

            if tid not in journeys:
                journeys[tid] = {
                    "crossings":    [],
                    "vehicle_type": vtype,
                    "saved":        False,
                }

            # ── Crossing check ──
            if not skipped and tid in prev_centroids:
                prev = prev_centroids[tid]
                for name, (p1, p2) in LINES.items():
                    if segments_intersect(prev, centroid, p1, p2):
                        crossings = journeys[tid]["crossings"]
                        if not crossings or crossings[-1] != name:
                            crossings.append(name)
                            print(f"  🚗 #{tid} ({vtype}) crossed "
                                  f"[{name.upper()}] | "
                                  f"{' → '.join(crossings)}")

                        if len(crossings) == 2 and not journeys[tid]["saved"]:
                            from_r, to_r = crossings[0], crossings[1]
                            save_journey(ACTIVE_CAMERA, tid, vtype,
                                         from_r, to_r)
                            journeys[tid]["saved"] = True
                            journey_log.append(1)

            if not skipped:
                prev_centroids[tid] = centroid

            # ── Draw bounding box ──
            thick = 1 if skipped else 2
            cv2.rectangle(frame, (x1,y1), (x2,y2), color, thick)

            label = f"ID{tid} {vtype} {int(conf*100)}%"
            (lw, lh), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.38, 1)
            cv2.rectangle(frame, (x1, y1-lh-8), (x1+lw+4, y1), color, -1)
            cv2.putText(frame, label, (x1+2, y1-4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0,0,0), 1)
            cv2.circle(frame, centroid, 3, color, -1)

            # ── Crossing history under box ──
            hist = journeys[tid]["crossings"]
            if hist:
                hist_text = " → ".join(h.upper() for h in hist)
                cv2.putText(frame, hist_text, (x1, y2+14),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.35,
                            VEHICLE_COLORS.get(vtype,(200,200,200)), 1)

    # ── Snapshot ──
    now = time.time()
    if now - last_snap_time >= SNAPSHOT_INTERVAL:
        snap_path = os.path.join(SNAPSHOT_DIR, f"{ACTIVE_CAMERA}.jpg")
        cv2.imwrite(snap_path, frame)
        last_snap_time = now

    # ── Push to MJPEG stream slot ──
    frame_slot.slot.update(frame)

    # ── HUD overlay ──
    overlay = frame.copy()
    cv2.rectangle(overlay, (0,0), (220, 115), (0,0,0), -1)
    cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)

    cv2.putText(frame, f"FPS: {avg_fps:.1f}",
                (8,20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0,255,255), 2)
    cv2.putText(frame, f"Tracked: {len(current_ids)}",
                (8,42), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0,255,255), 2)
    cv2.putText(frame, f"Journeys: {len(journey_log)}",
                (8,64), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0,255,0),   2)
    cv2.putText(frame, f"Frame: {frame_number}",
                (8,84), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (150,150,150), 1)
    cv2.putText(frame, f"Skip 1/{SKIP_FRAMES}",
                (8,102), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (180,180,0), 1)

    cv2.putText(frame, "● LIVE",
                (FRAME_WIDTH - 80, 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 60, 255), 2)

    if skipped:
        cv2.putText(frame, "SKIP",
                    (FRAME_WIDTH - 58, 42),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,100,255), 2)

    # ── Show frame ──
    if SHOW_FRAMES:
        cv2.imshow(WIN, frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            print("\n🛑 User quit")
            stop_evt.set()
            break
        elif key == ord('f'):
            prop = cv2.getWindowProperty(WIN, cv2.WND_PROP_FULLSCREEN)
            if prop == cv2.WINDOW_FULLSCREEN:
                cv2.setWindowProperty(WIN, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)
            else:
                cv2.setWindowProperty(WIN, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    # ── FPS calc ──
    t1_time = time.perf_counter()
    fps_buf.append(1.0 / max(t1_time - t0, 1e-6))
    if len(fps_buf) > 120:
        fps_buf.pop(0)
    avg_fps = float(np.mean(fps_buf))

    if frame_number % 200 == 0:
        print(f"  📊 Frame {frame_number} | "
              f"Journeys: {len(journey_log)} | FPS: {avg_fps:.1f}")

# ── Cleanup ───────────────────────────────────────────────────────────────────
stop_evt.set()
rtsp.stop()
cv2.destroyAllWindows()
print(f"\n✅ Done — {frame_number} frames processed, "
      f"{len(journey_log)} journeys saved.")