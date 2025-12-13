# ui/employee_dashboard.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

import cv2

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout

from monitoring.shift_tracker import ShiftTracker, ShiftState, ShiftStatus
from monitoring.camera_monitor import CameraMonitor
from monitoring.i_focus_detector import FocusState
from monitoring.pc_activity_monitor import PCActivityMonitor
from monitoring.i_activity_classifier import ActivityLabel
from monitoring.productivity_calculator import ProductivityCalculator
from monitoring.base_productivity_calculator import ProductivityCategory
from ui.widgets.productivity_widget import ProductivityWidget

# optional beep (Windows)
try:
    import winsound
except ImportError:
    winsound = None


# ---------------------------------------------------------------
# Temporary FAKE shift service (for testing only)
# ---------------------------------------------------------------

@dataclass
class FakeShift:
    start_time: datetime
    end_time: datetime


class FakeShiftService:
    def get_today_shift(self, user_id: int):
        now = datetime.now()
        start = now - timedelta(minutes=2)
        end = start + timedelta(minutes=30)
        return FakeShift(start_time=start, end_time=end)


# ---------------------------------------------------------------
# Employee dashboard prototype
# ---------------------------------------------------------------

class EmployeeDashboard(QWidget):
    def __init__(self, user_id: int):
        super().__init__()

        self.user_id = user_id
        self.setWindowTitle("Vision – Employee Prototype UI")

        # -------- UI labels --------
        self.label_title = QLabel(f"Employee ID: {self.user_id}")
        self.label_status = QLabel("Shift Status: ...")
        self.label_worked = QLabel("Worked Minutes: ...")
        self.label_remaining = QLabel("Remaining Minutes: ...")
        self.label_late = QLabel("Late Minutes: ...")

        self.label_camera = QLabel("Camera State: ...")
        self.label_pc = QLabel("PC Activity: ...")

        # Live camera preview
        self.label_camera_view = QLabel("Camera preview")
        self.label_camera_view.setFixedSize(320, 240)
        self.label_camera_view.setAlignment(Qt.AlignCenter)
        self.label_camera_view.setStyleSheet(
            "background-color: #202020; color: #cccccc; border: 1px solid #555;"
        )

        # Alert label
        self.label_alert = QLabel("")
        self.label_alert.setStyleSheet("color: red; font-weight: bold;")

        # Productivity widget
        self.productivity_widget = ProductivityWidget()

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.label_title)
        layout.addWidget(self.label_status)
        layout.addWidget(self.label_worked)
        layout.addWidget(self.label_remaining)
        layout.addWidget(self.label_late)

        layout.addWidget(self.label_camera)
        layout.addWidget(self.label_camera_view)

        layout.addWidget(self.label_pc)
        layout.addWidget(self.label_alert)

        layout.addWidget(self.productivity_widget)
        self.setLayout(layout)

        # -------- Shift tracking --------
        self.shift_service = FakeShiftService()
        self._last_shift_state: ShiftState | None = None

        self.shift_tracker = ShiftTracker(
            user_id=self.user_id,
            shift_service=self.shift_service,
            on_update=self._on_shift_update,
        )
        self.shift_tracker.start()

        # -------- Camera monitoring --------
        self._camera_state: FocusState | None = None
        self._latest_camera_pixmap: QPixmap | None = None

        self.camera_monitor = CameraMonitor(
            user_id=self.user_id,
            on_state_update=self._on_camera_update,
            on_frame=self._on_camera_frame,
        )
        self.camera_monitor.start()

        # -------- PC monitoring --------
        self._last_pc_app: str | None = None
        self._last_pc_label: ActivityLabel | None = None

        self.pc_monitor = PCActivityMonitor(
            user_id=self.user_id,
            on_update=self._on_pc_update,
        )
        self.pc_monitor.start()

        # -------- Productivity calculator --------
        self.productivity_calculator = ProductivityCalculator()

        # -------- Alert timers --------
        self.away_alert_timer = 0.0
        self.distracted_alert_timer = 0.0
        self.non_work_alert_timer = 0.0
        self._last_refresh_time = datetime.now()

        # Refresh UI (higher rate for smoother preview)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_ui)
        self._timer.start(100)  # ~10 fps

    # ===================== Callbacks =========================

    def _on_shift_update(self, state: ShiftState):
        self._last_shift_state = state

    def _on_camera_update(self, state: FocusState):
        self._camera_state = state

    def _on_camera_frame(self, frame, state: FocusState):
        """
        Called from CameraMonitor thread with raw OpenCV frame.
        Convert to QPixmap and store; actual UI update happens in _refresh_ui().
        """
        try:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            bytes_per_line = ch * w
            qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg)

            pixmap = pixmap.scaled(
                self.label_camera_view.width(),
                self.label_camera_view.height(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            self._latest_camera_pixmap = pixmap
        except Exception:
            pass

    def _on_pc_update(self, app_name: str | None, label: ActivityLabel):
        self._last_pc_app = app_name
        self._last_pc_label = label

    # ===================== UI Refresh =========================

    def _refresh_ui(self):
        # time delta for alert timers
        now = datetime.now()
        delta = (now - self._last_refresh_time).total_seconds()
        self._last_refresh_time = now

        late_minutes = 0

        # ---- Shift ----
        if self._last_shift_state:
            state = self._last_shift_state

            status_map = {
                ShiftStatus.NO_SHIFT: "No shift today",
                ShiftStatus.BEFORE_SHIFT: "Before shift",
                ShiftStatus.IN_SHIFT: "In shift",
                ShiftStatus.AFTER_SHIFT: "After shift",
            }

            self.label_status.setText(f"Shift Status: {status_map[state.status]}")
            self.label_worked.setText(f"Worked Minutes: {state.worked_minutes}")
            self.label_remaining.setText(f"Remaining Minutes: {state.remaining_minutes}")
            self.label_late.setText(f"Late Minutes: {state.late_minutes}")
            late_minutes = state.late_minutes

        # ---- Camera state text ----
        if self._camera_state:
            self.label_camera.setText(f"Camera State: {self._camera_state.value}")

        # ---- Camera preview image ----
        if self._latest_camera_pixmap is not None:
            self.label_camera_view.setPixmap(self._latest_camera_pixmap)

        # ---- PC activity ----
        if self._last_pc_label:
            text = self._last_pc_label.value
            if self._last_pc_app:
                text += f" ({self._last_pc_app})"
            self.label_pc.setText(f"PC Activity: {text}")

        # ---- Alert timers ----
        if self._camera_state == FocusState.AWAY:
            self.away_alert_timer += delta
        else:
            self.away_alert_timer = 0.0

        if self._camera_state == FocusState.DISTRACTED:
            self.distracted_alert_timer += delta
        else:
            self.distracted_alert_timer = 0.0

        if self._last_pc_label == ActivityLabel.NON_WORK:
            self.non_work_alert_timer += delta
        else:
            self.non_work_alert_timer = 0.0

        # ---- Alert conditions ----
        alert_message = ""

        if self.away_alert_timer > 6:
            alert_message = "⚠ You are away from the screen too long!"
            if winsound:
                winsound.Beep(1000, 200)

        elif self.distracted_alert_timer > 10:
            alert_message = "⚠ You seem distracted for too long!"
            if winsound:
                winsound.Beep(900, 200)

        elif self.non_work_alert_timer > 15:
            alert_message = "⚠ You are on non-work apps too long!"
            if winsound:
                winsound.Beep(800, 200)

        self.label_alert.setText(alert_message)

        # ---- Productivity ----
        focused = self.camera_monitor.focused_seconds
        distracted = getattr(self.camera_monitor, "distracted_seconds", 0.0)
        non_work = self.pc_monitor.non_work_seconds
        idle = self.pc_monitor.idle_seconds + distracted  # treat distracted as idle/penalty

        score = self.productivity_calculator.calculate_score(
            focused_seconds=focused,
            non_work_seconds=non_work,
            idle_seconds=idle,
            late_minutes=late_minutes,
        )

        category: ProductivityCategory = self.productivity_calculator.categorize(score)

        self.productivity_widget.update_metrics(
            score=score,
            category=category,
            focused_seconds=focused,
            non_work_seconds=non_work,
            idle_seconds=idle,
            late_minutes=late_minutes,
        )

    # ===================== Cleanup =========================

    def closeEvent(self, event):
        self.shift_tracker.stop()
        self.camera_monitor.stop()
        self.pc_monitor.stop()
        super().closeEvent(event)
