# monitoring/camera_monitor.py

from __future__ import annotations

import threading
import time
from typing import Optional, Callable, Any

import cv2

from monitoring.i_monitor import IMonitor
from monitoring.i_focus_detector import IFocusDetector, FocusState


class CameraMonitor(IMonitor, IFocusDetector):
    """
    Camera monitor with 3 states:
      - FOCUSED
      - DISTRACTED
      - AWAY

    Improvements:
    - Lower resolution capture (640x480) for speed
    - Face detection on downscaled image
    - TEMPORAL SMOOTHING:
        State must persist for `stabilization_seconds`
        before we change it (reduces flicker/noise).
    """

    def __init__(
        self,
        user_id: int,
        *,
        camera_index: int = 0,
        on_state_update: Optional[Callable[[FocusState], None]] = None,
        on_frame: Optional[Callable[[Any, FocusState], None]] = None,
        stabilization_seconds: float = 2.0,  # min time before switching state
    ) -> None:
        self.user_id = user_id
        self.camera_index = camera_index
        self.on_state_update = on_state_update
        self.on_frame = on_frame
        self.stabilization_seconds = stabilization_seconds

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._cap: Optional[cv2.VideoCapture] = None

        # tracking seconds (for STABLE state only)
        self.focused_seconds: float = 0.0
        self.distracted_seconds: float = 0.0
        self.away_seconds: float = 0.0

        # FPS tracking
        self.fps: float = 0.0
        self._frame_count: int = 0
        self._fps_last_time: float = time.time()

        # state smoothing
        self._current_state: FocusState = FocusState.AWAY
        self._pending_state: FocusState = FocusState.AWAY
        self._pending_duration: float = 0.0

        self.face_detector = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

    # -------------------------------------------------
    # IMonitor
    # -------------------------------------------------
    def start(self) -> None:
        if self._running:
            return

        # Try using DirectShow backend on Windows to avoid MSMF issues
        try:
            self._cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        except Exception:
            self._cap = cv2.VideoCapture(self.camera_index)

        if not self._cap or not self._cap.isOpened():
            print(f"[CameraMonitor] ERROR: Cannot open camera (index={self.camera_index}). "
                  f"Camera monitoring will be disabled.")
            if self._cap:
                self._cap.release()
            self._cap = None
            self._running = False
            return

        # Lower resolution for speed
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()


    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        if self._cap:
            self._cap.release()
        self._cap = None

    # -------------------------------------------------
    # Loop
    # -------------------------------------------------
    def _loop(self) -> None:
        last_time = time.time()
        failed_reads = 0

        while self._running and self._cap is not None:
            ok, frame = self._cap.read()
            if not ok or frame is None:
                failed_reads += 1
                if failed_reads >= 30:
                    print("[CameraMonitor] ERROR: Failed to read from camera repeatedly. "
                          "Stopping camera monitor.")
                    break
                time.sleep(0.1)  # small delay to avoid spamming
                continue

            failed_reads = 0  # reset on success


            raw_state = self.detect_focus_state(frame)

            now = time.time()
            delta = now - last_time
            last_time = now

            # ---- temporal smoothing of state ----
            stable_state_before = self._current_state
            self._update_stable_state(raw_state, delta)
            stable_state_after = self._current_state

            # seconds tracking uses STABLE state only
            if self._current_state == FocusState.FOCUSED:
                self.focused_seconds += delta
            elif self._current_state == FocusState.DISTRACTED:
                self.distracted_seconds += delta
            else:
                self.away_seconds += delta

            # FPS tracking
            self._frame_count += 1
            if now - self._fps_last_time >= 1.0:
                self.fps = self._frame_count / (now - self._fps_last_time)
                self._frame_count = 0
                self._fps_last_time = now

            # callbacks: send STABLE state, not raw
            if self.on_state_update and stable_state_after != stable_state_before:
                try:
                    self.on_state_update(self._current_state)
                except Exception:
                    pass

            if self.on_frame:
                try:
                    # pass stable state to frame callback
                    self.on_frame(frame, self._current_state)
                except Exception:
                    pass

            time.sleep(0.03)

    # -------------------------------------------------
    # State smoothing helper
    # -------------------------------------------------

    def _update_stable_state(self, raw_state: FocusState, delta: float) -> None:
        """
        Only switch to a new state if it persists at least
        `self.stabilization_seconds` seconds.
        """
        if raw_state == self._current_state:
            # we are stable, reset pending
            self._pending_state = self._current_state
            self._pending_duration = 0.0
            return

        # raw != current
        if raw_state == self._pending_state:
            # same candidate as before, accumulate time
            self._pending_duration += delta
            if self._pending_duration >= self.stabilization_seconds:
                # commit new stable state
                self._current_state = raw_state
                self._pending_duration = 0.0
        else:
            # new candidate appears, start counting
            self._pending_state = raw_state
            self._pending_duration = 0.0

    # -------------------------------------------------
    # Focus detection logic (downscaled for speed)
    # -------------------------------------------------

    def detect_focus_state(self, frame) -> FocusState:
        """
        - Convert to gray
        - Downscale to 0.5x for faster detection
        - Use largest face
        - If face center far from frame center => DISTRACTED

        This returns the RAW state; smoothing is applied later.
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # downscale for speed
        small = cv2.resize(gray, None, fx=0.5, fy=0.5)
        faces = self.face_detector.detectMultiScale(small, 1.3, 5)

        if len(faces) == 0:
            return FocusState.AWAY

        # biggest face
        x, y, w, h = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)[0]

        frame_h_small, frame_w_small = small.shape
        face_center_x = x + w / 2
        frame_center_x = frame_w_small / 2

        offset = abs(face_center_x - frame_center_x)
        offset_ratio = offset / frame_w_small
        aspect_ratio = w / float(h) if h else 1.0

        # Threshold for distraction (15% of width in small space)
        if offset_ratio > 0.15 or aspect_ratio < 0.65:
            return FocusState.DISTRACTED

        return FocusState.FOCUSED
