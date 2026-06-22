"""
frame_slot.py — Shared latest-frame store.
main.py calls slot.update(frame) every frame.
dashboard.py reads slot.get_jpeg() in the MJPEG stream.
Same process = shared memory, no IPC needed.
"""

import threading
import numpy as np
import cv2


def _make_placeholder() -> bytes:
    """Generate a 'Stream starting…' placeholder JPEG once at import time."""
    img = np.zeros((360, 640, 3), dtype=np.uint8)
    cv2.putText(img, "Stream starting...", (160, 175),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (180, 180, 180), 2)
    cv2.putText(img, "Waiting for first frame", (140, 215),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (120, 120, 120), 1)
    _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 70])
    return buf.tobytes()


class FrameSlot:
    def __init__(self):
        self._lock = threading.Lock()
        self._jpeg = _make_placeholder()   # ← never None after init

    def update(self, frame):
        """Encode numpy frame to JPEG and cache it. Called from main loop."""
        ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        if not ok:
            return
        with self._lock:
            self._jpeg = buf.tobytes()

    def get_jpeg(self) -> bytes:
        """Return latest JPEG bytes. Always returns something after init."""
        with self._lock:
            return self._jpeg


# Single global instance shared across the whole process
slot = FrameSlot()