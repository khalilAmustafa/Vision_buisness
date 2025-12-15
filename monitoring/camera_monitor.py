# monitoring/camera_monitor.py

from __future__ import annotations

import os
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
        # Extra part detectors (for partial face cases)
        self.eye_detector = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_eye.xml")
        self.mouth_detector = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_smile.xml")

        # Nose cascade is NOT guaranteed in OpenCV default install
        nose_path = cv2.data.haarcascades + "haarcascade_mcs_nose.xml"
        self.nose_detector = cv2.CascadeClassifier(nose_path) if os.path.exists(nose_path) else None


    def start(self) -> None:
        if self._running:
            return

        import cv2
        import threading
        import time

        # Use DirectShow on Windows (more stable & faster)
        self._cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)

        if not self._cap.isOpened():
            print("[CameraMonitor] ERROR: Cannot open camera.")
            self._cap = None
            return

        # -----------------------------
        # PERFORMANCE SETTINGS
        # -----------------------------
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)

        # Request HIGH FPS (camera may ignore)
        self._cap.set(cv2.CAP_PROP_FPS, 60)

        # Disable buffering if supported
        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        actual_fps = self._cap.get(cv2.CAP_PROP_FPS)
        print(f"[CameraMonitor] Requested FPS: 60 | Actual FPS: {actual_fps}")

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
        import time

        failed_reads = 0
        last_time = time.time()
        frame_count = 0

        while self._running and self._cap is not None:
            ok, frame = self._cap.read()
            if not ok or frame is None:
                failed_reads += 1
                if failed_reads > 30:
                    print("[CameraMonitor] Camera read failed repeatedly. Stopping.")
                    break
                time.sleep(0.005)
                continue

            failed_reads = 0
            frame_count += 1

            # OPTIONAL: calculate real FPS (debug)
            now = time.time()
            if now - last_time >= 1.0:
                print(f"[CameraMonitor] Real FPS: {frame_count}")
                frame_count = 0
                last_time = now

            # ---- EXISTING LOGIC BELOW ----
            # detect focus state
            raw_state = self.detect_focus_state(frame)
    
            now = time.time()
            delta = now - last_time
            last_time = now

            self._update_stable_state(raw_state, delta)

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
        Face logic:
        1) Full face detected by face cascade => face
        2) If no face:
            - mouth + nose  => face
            - nose + eyes   => face
            - nose only     => face (last option)
        Returns RAW state; smoothing is applied later.
        """

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # downscale for speed
        small = cv2.resize(gray, None, fx=0.5, fy=0.5)
        frame_h, frame_w = small.shape

        # 1) Try full face
        faces = self.face_detector.detectMultiScale(small, 1.3, 5)
        if len(faces) > 0:
            # Choose largest face
            x, y, w, h = max(faces, key=lambda r: r[2] * r[3])

            face_center_x = x + w / 2
            frame_center_x = frame_w / 2

            offset_ratio = abs(face_center_x - frame_center_x) / frame_w
            aspect_ratio = w / float(h) if h else 1.0

            if offset_ratio > 0.15 or aspect_ratio < 0.65:
                return FocusState.DISTRACTED
            return FocusState.FOCUSED

        # 2) No full face: detect parts on the whole frame (small)
        eyes = self.eye_detector.detectMultiScale(small, 1.2, 6)
        mouth = self.mouth_detector.detectMultiScale(small, 1.25, 18)

        nose = []
        if self.nose_detector is not None:
            nose = self.nose_detector.detectMultiScale(small, 1.2, 6)

        has_eyes = len(eyes) > 0
        has_mouth = len(mouth) > 0
        has_nose = len(nose) > 0

        # Your required combinations
        face_found = (has_mouth and has_nose) or (has_nose and has_eyes) or has_nose

        if not face_found:
            return FocusState.AWAY

        # Determine "distracted" based on the best available part center
        # Prefer nose center, else eyes center, else mouth center
        def center_of(rects):
            x, y, w, h = max(rects, key=lambda r: r[2] * r[3])
            return (x + w / 2), (y + h / 2)

        if has_nose:
            cx, _ = center_of(nose)
        elif has_eyes:
            cx, _ = center_of(eyes)
        else:
            cx, _ = center_of(mouth)

        offset_ratio = abs(cx - (frame_w / 2)) / frame_w
        if offset_ratio > 0.18:
            return FocusState.DISTRACTED

        return FocusState.FOCUSED

