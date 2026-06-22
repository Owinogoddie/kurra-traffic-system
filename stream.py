"""
stream.py — Resilient RTSP reader

Reconnects silently and indefinitely in the background.
Puts frames into a queue consumed by main.py's inference thread.
"""

import os
import time
import queue
import threading

import cv2

from config import (
    FRAME_WIDTH, FRAME_HEIGHT,
    RECONNECT_DELAY, RECONNECT_EVERY,
)

# Tell FFmpeg to use TCP and set generous timeouts
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
    "rtsp_transport;tcp|"
    "timeout;10000000|"
    "stimeout;10000000"
)


def _open(url: str) -> cv2.VideoCapture:
    """Open an RTSP stream and return the VideoCapture object."""
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)
    cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 10_000)
    cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 10_000)
    return cap


class RtspStream:
    """
    Background thread that reads frames from an RTSP URL and
    puts them into `self.queue`.

    Reconnects silently and indefinitely whenever:
      - cap.read() fails
      - RECONNECT_EVERY seconds have elapsed (proactive refresh)

    Usage:
        stream = RtspStream(url)
        stream.start()
        ...
        frame = stream.queue.get()   # blocks until a frame arrives
        ...
        stream.stop()
    """

    def __init__(self, url: str, maxsize: int = 8):
        self.url    = url
        self.queue  = queue.Queue(maxsize=maxsize)
        self._stop  = threading.Event()
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="rtsp-reader"
        )

    # ── public API ────────────────────────────────────────────────────────────

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _put_latest(self, frame):
        """Keep latency low by evicting one stale frame when queue is full."""
        try:
            self.queue.put_nowait(frame)
            return
        except queue.Full:
            pass

        try:
            self.queue.get_nowait()
        except queue.Empty:
            pass

        try:
            self.queue.put_nowait(frame)
        except queue.Full:
            # If a consumer raced and refilled the queue, dropping this frame is acceptable.
            pass

    # ── internal ──────────────────────────────────────────────────────────────

    def _run(self):
        cap         = None
        opened_at   = 0.0

        while not self._stop.is_set():

            # ── (re)open if needed ──
            need_open = (cap is None or not cap.isOpened())
            if not need_open and RECONNECT_EVERY > 0:
                need_open = (time.time() - opened_at) >= RECONNECT_EVERY

            if need_open:
                if cap is not None:
                    cap.release()
                cap = _open(self.url)
                if cap.isOpened():
                    opened_at = time.time()
                else:
                    # silent retry — camera may be down
                    cap.release()
                    cap = None
                    time.sleep(RECONNECT_DELAY)
                    continue

            # ── read one frame ──
            ret, frame = cap.read()

            if not ret:
                # stream dropped — release and retry silently
                cap.release()
                cap = None
                time.sleep(RECONNECT_DELAY)
                continue

            # ── resize if needed ──
            if frame.shape[1] != FRAME_WIDTH or frame.shape[0] != FRAME_HEIGHT:
                frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))

            # ── push to queue (drop oldest, keep newest) ──
            self._put_latest(frame)

        # cleanup on stop
        if cap is not None:
            cap.release()