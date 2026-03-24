"""
run_all.py — Run all cameras in parallel.

Cameras are read from config.CAMERAS automatically.
To add/remove a camera: comment/uncomment it in config.py — nothing to change here.

Usage:
    python run_all.py                            # all cameras in config
    python run_all.py --cameras cam_101 cam_103  # specific subset
"""

import multiprocessing
import argparse
import time
import sys
import os


def run_camera(camera_id: str):
    """One worker process per camera."""
    import cv2
    import torch
    import time as _time
    from ultralytics import YOLO
    from config import (
        FRAME_WIDTH, FRAME_HEIGHT,
        MODEL_PATH, CONFIDENCE, INFERENCE_SIZE, SKIP_FRAMES,
        VEHICLE_CLASSES, CAMERAS, CAMERA_LINES,
        JOURNEY_OWNERSHIP,                        
    )
    from db import init_db, save_journey

    print(f"[{camera_id}] 🚀 Process started (PID {os.getpid()})")

    if camera_id not in CAMERAS:
        print(f"[{camera_id}] ❌ Not in config.CAMERAS — skipping")
        return
    if camera_id not in CAMERA_LINES:
        print(f"[{camera_id}] ❌ No lines in config.CAMERA_LINES — skipping")
        return

    init_db()

    SNAPSHOT_DIR      = "snapshots"
    SNAPSHOT_INTERVAL = 5
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)

    print(f"[{camera_id}] Loading {MODEL_PATH}...")
    model = YOLO(MODEL_PATH)
    print(f"[{camera_id}] ✅ Model loaded")

    source = CAMERAS[camera_id]
    cap    = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"[{camera_id}] ❌ Could not open: {source}")
        return

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps          = int(cap.get(cv2.CAP_PROP_FPS))
    print(f"[{camera_id}] ✅ Opened {source} | {total_frames} frames @ {fps}fps")

    lines = CAMERA_LINES[camera_id]

    def get_side(px, py, x1, y1, x2, y2):
        val = (x2 - x1) * (py - y1) - (y2 - y1) * (px - x1)
        if val > 0: return  1
        if val < 0: return -1
        return 0

    prev_sides   = {}
    crossings    = {}
    saved_tracks = set()
    journey_log  = []
    frame_count  = 0
    skip_counter = 0
    last_results = None
    last_snap    = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = cap.read()
            if not ret:
                break

        frame_count  += 1
        skip_counter += 1

        frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))

        now = _time.time()
        if now - last_snap >= SNAPSHOT_INTERVAL:
            cv2.imwrite(os.path.join(SNAPSHOT_DIR, f"{camera_id}.jpg"), frame)
            last_snap = now

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

        if (results and
            results[0].boxes is not None and
            results[0].boxes.id is not None):

            boxes = results[0].boxes
            for i in range(len(boxes)):
                track_id        = int(boxes.id[i].item())
                cls             = int(boxes.cls[i].item())
                x1, y1, x2, y2 = map(int, boxes.xyxy[i].tolist())
                cx              = (x1 + x2) // 2
                cy              = (y1 + y2) // 2
                vtype           = VEHICLE_CLASSES.get(cls, "unknown")

                if track_id not in prev_sides:
                    prev_sides[track_id] = {}
                    crossings[track_id]  = []

                for road, (start, end) in lines.items():
                    curr_side = get_side(cx, cy,
                                         start[0], start[1],
                                         end[0],   end[1])
                    prev = prev_sides[track_id].get(road)

                    if (curr_side != 0 and
                        prev is not None and
                        prev != 0 and
                        curr_side != prev):

                        if road not in crossings[track_id]:
                            crossings[track_id].append(road)
                            print(f"[{camera_id}] 🚗 #{track_id} ({vtype}) "
                                  f"crossed [{road.upper()}] | "
                                  f"history: {crossings[track_id]}")

                            if (len(crossings[track_id]) == 2 and
                                track_id not in saved_tracks):

                                from_road = crossings[track_id][0]
                                to_road   = crossings[track_id][1]

                                owner = JOURNEY_OWNERSHIP.get((from_road, to_road))

                                if owner is None:
                                    print(f"[{camera_id}] ⚠️  No owner for "
                                          f"{from_road}→{to_road}, saving anyway")
                                    should_save = True
                                elif owner == camera_id:
                                    should_save = True
                                else:
                                    print(f"[{camera_id}] ⏭️  Skipping "
                                          f"{from_road}→{to_road} "
                                          f"(owned by {owner})")
                                    should_save = False

                                if should_save:
                                    journey_log.append({
                                        "track_id":  track_id,
                                        "vehicle":   vtype,
                                        "from_road": from_road,
                                        "to_road":   to_road,
                                    })
                                    print(f"[{camera_id}] ✅ JOURNEY: #{track_id} "
                                          f"{vtype} | {from_road} → {to_road}")
                                    save_journey(
                                        camera_id=camera_id,
                                        track_id=track_id,
                                        vehicle_type=vtype,
                                        from_road=from_road,
                                        to_road=to_road,
                                    )

                                saved_tracks.add(track_id)

                    prev_sides[track_id][road] = curr_side

        if frame_count % 100 == 0:
            print(f"[{camera_id}] 📊 Frame {frame_count}/{total_frames} | "
                  f"Journeys saved: {len(journey_log)}")

    cap.release()
    print(f"\n[{camera_id}] ✅ Finished | Frames: {frame_count} | "
          f"Journeys: {len(journey_log)}")
    for j in journey_log:
        print(f"[{camera_id}]   #{j['track_id']:>4} {j['vehicle']:<12} "
              f"{j['from_road']} → {j['to_road']}")


def main():
    from config import CAMERAS
    available = list(CAMERAS.keys())

    parser = argparse.ArgumentParser(
        description="Run Kurra cameras in parallel. "
                    "Add/remove cameras in config.CAMERAS — no edits needed here."
    )
    parser.add_argument(
        "--cameras", nargs="+",
        default=available,
        choices=available,
        help=f"Cameras to run. Default: all in config ({', '.join(available)})"
    )
    args    = parser.parse_args()
    cameras = args.cameras

    print("=" * 55)
    print("  🚦 Kurra Traffic — Parallel Runner")
    print(f"  Cameras  : {', '.join(cameras)}")
    print(f"  Processes: {len(cameras)}")
    print("=" * 55)

    ctx       = multiprocessing.get_context("spawn")
    processes = []

    for cam in cameras:
        p = ctx.Process(target=run_camera, args=(cam,), name=cam, daemon=False)
        p.start()
        processes.append(p)
        print(f"  ▶️  Started {cam} (PID {p.pid})")
        time.sleep(0.5)

    print("\n  All cameras running. Press Ctrl+C to stop all.\n")

    try:
        for p in processes:
            p.join()
    except KeyboardInterrupt:
        print("\n🛑 Stopping all cameras...")
        for p in processes:
            p.terminate()
        for p in processes:
            p.join()
        print("✅ All stopped.")
        sys.exit(0)

    print("\n" + "=" * 55)
    for p in processes:
        status = "✅ OK" if p.exitcode == 0 else f"❌ Exit code {p.exitcode}"
        print(f"  {p.name}: {status}")
    print("=" * 55)


if __name__ == "__main__":
    main()
