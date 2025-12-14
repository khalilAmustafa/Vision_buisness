# ui/employee_dashboard.py

from __future__ import annotations

from datetime import datetime

import cv2

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFrame, QGridLayout, QSizePolicy

from core.database import Database
from core.session_tracker import SessionTracker
from core.services.shift_service import ShiftService
from monitoring.shift_tracker import ShiftTracker, ShiftState, ShiftStatus
from monitoring.i_focus_detector import FocusState
from monitoring.i_activity_classifier import ActivityLabel
from monitoring.productivity_calculator import ProductivityCalculator
from monitoring.base_productivity_calculator import ProductivityCategory
from ui.widgets.productivity_widget import ProductivityWidget

try:
    import winsound
except ImportError:
    winsound = None


class EmployeeDashboard(QWidget):
    def __init__(self, user_id: str, session_tracker: SessionTracker, db: Database):
        super().__init__()

        self.user_id = user_id
        self._session_tracker = session_tracker
        self._db = db
        self.setWindowTitle("Vision • Employee Dashboard")
        self.setMinimumSize(1080, 700)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        hero = QFrame()
        hero.setObjectName("Card")
        hero_layout = QVBoxLayout(hero)
        title = QLabel("Daily performance overview")
        title.setObjectName("TitleLabel")
        subtitle = QLabel(f"Employee • ID {self.user_id}")
        subtitle.setObjectName("MutedLabel")
        hero_layout.addWidget(title)
        hero_layout.addWidget(subtitle)
        root.addWidget(hero)

        stats_card = QFrame()
        stats_card.setObjectName("Card")
        stats_layout = QGridLayout(stats_card)
        stats_layout.setSpacing(18)

        (
            self.status_card,
            self.label_status,
        ) = self._create_stat_block("Shift Status", "—")
        (
            self.worked_card,
            self.label_worked,
        ) = self._create_stat_block("Worked Minutes", "—")
        (
            self.remaining_card,
            self.label_remaining,
        ) = self._create_stat_block("Remaining Minutes", "—")
        (
            self.late_card,
            self.label_late,
        ) = self._create_stat_block("Late Minutes", "—")

        stats_layout.addWidget(self.status_card, 0, 0)
        stats_layout.addWidget(self.worked_card, 0, 1)
        stats_layout.addWidget(self.remaining_card, 1, 0)
        stats_layout.addWidget(self.late_card, 1, 1)
        root.addWidget(stats_card)

        row = QHBoxLayout()
        row.setSpacing(16)

        camera_card = QFrame()
        camera_card.setObjectName("Card")
        camera_layout = QVBoxLayout(camera_card)
        camera_layout.setSpacing(8)
        camera_header = QLabel("Focus tracking")
        camera_header.setObjectName("MutedLabel")
        self.label_camera = QLabel("Camera State: …")
        self.label_camera_view = QLabel("Camera preview")
        self.label_camera_view.setAlignment(Qt.AlignCenter)
        self.label_camera_view.setStyleSheet("background-color: #111827; color: #F3F4F6; border-radius: 12px;")
        self.label_camera_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        camera_layout.addWidget(camera_header)
        camera_layout.addWidget(self.label_camera)
        camera_layout.addWidget(self.label_camera_view)
        camera_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        side_column = QVBoxLayout()
        side_column.setSpacing(12)

        activity_card = QFrame()
        activity_card.setObjectName("Card")
        activity_layout = QVBoxLayout(activity_card)
        activity_layout.setSpacing(6)
        activity_header = QLabel("System alerts")
        activity_header.setObjectName("MutedLabel")
        self.label_pc = QLabel("PC Activity: …")
        self.label_alert = QLabel("")
        self.label_alert.setStyleSheet("color: #EF4444; font-weight: 600;")
        activity_layout.addWidget(activity_header)
        activity_layout.addWidget(self.label_pc)
        activity_layout.addWidget(self.label_alert)

        self.productivity_widget = ProductivityWidget()

        activity_card.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.productivity_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        side_column.addWidget(activity_card)
        side_column.addWidget(self.productivity_widget, 1)

        row.addWidget(camera_card, 2)
        row.addLayout(side_column, 1)

        root.addLayout(row)

        self.shift_service = ShiftService(self._db)
        self._last_shift_state: ShiftState | None = None

        self.shift_tracker = ShiftTracker(
            user_id=self.user_id,
            shift_service=self.shift_service,
            on_update=self._on_shift_update,
        )
        self.shift_tracker.start()

        self._camera_state: FocusState | None = None
        self._latest_camera_pixmap: QPixmap | None = None

        self._last_pc_app: str | None = None
        self._last_pc_label: ActivityLabel | None = None

        self._session_tracker.register_ui_callbacks(
            on_focus_state_change=self._on_camera_update,
            on_pc_activity=self._on_pc_update,
            on_camera_frame=self._on_camera_frame,
        )

        self.productivity_calculator = ProductivityCalculator()

        self.away_alert_timer = 0.0
        self.distracted_alert_timer = 0.0
        self.non_work_alert_timer = 0.0
        self._last_refresh_time = datetime.now()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_ui)
        self._timer.start(33)  # ~30 fps

    def _create_stat_block(self, title: str, value: str):
        wrapper = QFrame()
        wrapper.setObjectName("Card")
        wrapper.setStyleSheet("QFrame#Card { padding: 12px; }")
        layout = QVBoxLayout(wrapper)
        label = QLabel(title)
        label.setObjectName("MutedLabel")
        value_label = QLabel(value)
        value_label.setObjectName("MetricValue")
        layout.addWidget(label)
        layout.addWidget(value_label)
        layout.setSpacing(4)
        return wrapper, value_label

    def _on_shift_update(self, state: ShiftState):
        self._last_shift_state = state

    def _on_camera_update(self, state: FocusState):
        self._camera_state = state

    def _on_camera_frame(self, frame, state: FocusState):
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

    def _refresh_ui(self):
        now = datetime.now()
        delta = (now - self._last_refresh_time).total_seconds()
        self._last_refresh_time = now

        late_minutes = 0

        if self._last_shift_state:
            state = self._last_shift_state
            status_map = {
                ShiftStatus.NO_SHIFT: "No shift today",
                ShiftStatus.BEFORE_SHIFT: "Before shift",
                ShiftStatus.IN_SHIFT: "In shift",
                ShiftStatus.AFTER_SHIFT: "After shift",
            }
            self.label_status.setText(status_map[state.status])
            self.label_worked.setText(f"{state.worked_minutes} min")
            self.label_remaining.setText(f"{state.remaining_minutes} min")
            self.label_late.setText(f"{state.late_minutes} min")
            late_minutes = state.late_minutes

        latest_focus = self._session_tracker.get_focus_state()
        if latest_focus:
            self._camera_state = latest_focus
        if self._camera_state:
            self.label_camera.setText(f"Camera State: {self._camera_state.value}")

        if self._latest_camera_pixmap is not None:
            self.label_camera_view.setPixmap(self._latest_camera_pixmap)

        app_name, label_state = self._session_tracker.get_pc_activity_state()
        if label_state:
            self._last_pc_label = label_state
        if app_name is not None:
            self._last_pc_app = app_name
        if self._last_pc_label:
            text = self._last_pc_label.value
            if self._last_pc_app:
                text += f" ({self._last_pc_app})"
            self.label_pc.setText(f"PC Activity: {text}")

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

        focused, non_work, idle_base = self._session_tracker.get_counters()
        idle = idle_base

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

    def closeEvent(self, event):
        self.shift_tracker.stop()
        super().closeEvent(event)
