import cv2
import os
import time
from dotenv import load_dotenv

load_dotenv()

os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
    "rtsp_transport;tcp|"
    "timeout;10000000|"        # 10s timeout in microseconds
    "stimeout;10000000"        # socket timeout
)

RTSP_URL = os.getenv(
    "RTSP_URL",
    "rtsp://<username>:<password>@<camera-host>:554/Streaming/Channels/101",
)
WIN_NAME        = "Camera Stream"
WIDTH           = 1280
HEIGHT          = 720
# WIDTH = 480
# HEIGHT = 270
RECONNECT_DELAY = 3

def open_stream(url):
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 3)          # was 1, too tight
    cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 10000)   # 10s open timeout
    cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 10000)   # 10s read timeout
    return cap

def main():
    cap = open_stream(RTSP_URL)

    if not cap.isOpened():
        print("❌ Cannot open stream.")
        return

    cv2.namedWindow(WIN_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WIN_NAME, WIDTH, HEIGHT)

    print(f"✅ Streaming at {WIDTH}x{HEIGHT} — Press 'q' to quit, 'f' for fullscreen")

    consecutive_failures = 0
    MAX_FAILURES = 10  # give up retrying after this many in a row

    while True:
        ret, frame = cap.read()

        if not ret:
            consecutive_failures += 1
            print(f"⚠️  Lost connection (attempt {consecutive_failures}) — retrying in {RECONNECT_DELAY}s...")
            cap.release()

            if consecutive_failures >= MAX_FAILURES:
                print("❌ Too many failures, giving up.")
                break

            time.sleep(RECONNECT_DELAY)
            cap = open_stream(RTSP_URL)
            continue

        consecutive_failures = 0  # reset on success

        frame = cv2.resize(frame, (WIDTH, HEIGHT))

        fps = cap.get(cv2.CAP_PROP_FPS)
        cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        cv2.imshow(WIN_NAME, frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            print("👋 Exiting...")
            break
        elif key == ord('f'):
            prop = cv2.getWindowProperty(WIN_NAME, cv2.WND_PROP_FULLSCREEN)
            if prop == cv2.WINDOW_FULLSCREEN:
                cv2.setWindowProperty(WIN_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)
            else:
                cv2.setWindowProperty(WIN_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()