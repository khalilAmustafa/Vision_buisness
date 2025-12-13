
# monitoring/pc_activity_monitor.py

from __future__ import annotations

import time
import threading
from typing import Optional, Callable

import psutil
import ctypes
import ctypes.wintypes

from monitoring.i_monitor import IMonitor
from monitoring.i_activity_classifier import IActivityClassifier, ActivityLabel


# Windows API setup for getting active window title
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

GetForegroundWindow = user32.GetForegroundWindow
GetWindowTextW = user32.GetWindowTextW
GetWindowThreadProcessId = user32.GetWindowThreadProcessId


class PCActivityMonitor(IMonitor, IActivityClassifier):
    """
    Tracks:
    - active window (foreground process)
    - idle vs active time
    - work vs non-work apps

    Counts seconds in:
        self.work_seconds
        self.non_work_seconds
        self.idle_seconds
    """

    def __init__(
        self,
        user_id: int,
        *,
        on_update: Optional[Callable[[str, ActivityLabel], None]] = None,
        idle_threshold: float = 60.0  # seconds without input = idle
    ):
        self.user_id = user_id
        self.on_update = on_update
        self.idle_threshold = idle_threshold

        self._running = False
        self._thread: Optional[threading.Thread] = None

        # Statistics
        self.work_seconds = 0.0
        self.non_work_seconds = 0.0
        self.idle_seconds = 0.0

        self._last_input_time = time.time()

        # simple example work apps list
        self.work_apps = {
            "code.exe",
            "pycharm.exe",
            "python.exe",
            "chrome.exe",  # only if on work websites later
            "excel.exe",
            "word.exe",
        }

    # -------------------------------------------------------
    # Helper: detect idle time (Windows only)
    # -------------------------------------------------------

    def _get_idle_time(self) -> float:
        """Return how many seconds since last mouse/keyboard input."""
        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.wintypes.UINT),
                ("dwTime", ctypes.wintypes.DWORD),
            ]

        last_input_info = LASTINPUTINFO()
        last_input_info.cbSize = ctypes.sizeof(last_input_info)

        user32.GetLastInputInfo(ctypes.byref(last_input_info))
        millis = kernel32.GetTickCount() - last_input_info.dwTime
        return millis / 1000.0

    # -------------------------------------------------------
    # Helper: get active window executable name
    # -------------------------------------------------------

    def _get_active_app_name(self) -> Optional[str]:
        hwnd = GetForegroundWindow()
        if not hwnd:
            return None

        pid = ctypes.wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

        try:
            process = psutil.Process(pid.value)
            return process.name().lower()
        except Exception:
            return None

    # -------------------------------------------------------
    # IMonitor
    # -------------------------------------------------------

    def start(self) -> None:
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

    # -------------------------------------------------------
    # Main loop
    # -------------------------------------------------------

    def _loop(self) -> None:
        last_time = time.time()

        while self._running:
            now = time.time()
            delta = now - last_time
            last_time = now

            idle_seconds = self._get_idle_time()

            if idle_seconds >= self.idle_threshold:
                label = ActivityLabel.IDLE
                self.idle_seconds += delta
                app_name = None
            else:
                app_name = self._get_active_app_name()
                label = self.classify_activity(app_name)

                if label == ActivityLabel.WORK:
                    self.work_seconds += delta
                else:
                    self.non_work_seconds += delta

            if self.on_update:
                try:
                    self.on_update(app_name, label)
                except Exception:
                    pass

            time.sleep(0.2)

    # -------------------------------------------------------
    # IActivityClassifier
    # -------------------------------------------------------

    def classify_activity(self, app_name: Optional[str]) -> ActivityLabel:
        if not app_name:
            return ActivityLabel.IDLE

        if app_name in self.work_apps:
            return ActivityLabel.WORK

        return ActivityLabel.NON_WORK
