# core/session_tracker.py

from __future__ import annotations

import datetime
import threading
import time
from typing import Optional, Callable, Any

from core.database import Database
from core.services.shift_service import ShiftService
from monitoring.camera_monitor import CameraMonitor
from monitoring.pc_activity_monitor import PCActivityMonitor
from monitoring.productivity_calculator import ProductivityCalculator
from monitoring.i_focus_detector import FocusState
from monitoring.i_activity_classifier import ActivityLabel


class SessionTracker:
    """
    Connects monitoring modules (camera + PC) to the SQLite database.

    - start_session(user_id):
        * ensures daily_summaries row for today
        * starts CameraMonitor + PCActivityMonitor
    - Monitors push events into DB:
        * focus_logs
        * pc_activity_logs
    - Background thread periodically updates daily_summaries using
      ProductivityCalculator based on:
        * camera_monitor.focused_seconds / distracted_seconds / away_seconds
        * pc_monitor.work_seconds / non_work_seconds / idle_seconds
    """

    def __init__(self, db: Database):
        self.db = db
        self.conn = db.get_connection()
        self._db_lock = threading.Lock()

        self.user_id: Optional[str] = None
        self._camera_monitor: Optional[CameraMonitor] = None
        self._pc_monitor: Optional[PCActivityMonitor] = None

        self._productivity_calc = ProductivityCalculator()
        self._summary_thread: Optional[threading.Thread] = None
        self._summary_running: bool = False

        # last known focus state (for logging / UI)
        self._current_focus_state: FocusState = FocusState.AWAY
        self._current_pc_app: Optional[str] = None
        self._current_pc_label: Optional[ActivityLabel] = ActivityLabel.IDLE

        # optional callbacks to drive UI directly from monitors
        self._ui_focus_callback: Optional[Callable[[FocusState], None]] = None
        self._ui_pc_callback: Optional[Callable[[Optional[str], ActivityLabel], None]] = None
        self._ui_frame_callback: Optional[Callable[[Any, FocusState], None]] = None

        # shift handling (for late_minutes)
        self._shift_service = ShiftService(db)
        self._login_time: Optional[datetime.datetime] = None

    # ------------------------------------------------------------------ #
    # PUBLIC API
    # ------------------------------------------------------------------ #

    def start_session(self, user_id: str):
        """
        Called when employee logs in.
        """
        self.user_id = user_id
        self._login_time = datetime.datetime.now()

        # Make sure daily_summaries row for today exists
        self._ensure_today_summary_row()

        # ---- Start Camera Monitor ----
        # CameraMonitor will call _on_focus_state_change when state changes
        self._camera_monitor = CameraMonitor(
            user_id=int(user_id),  # annotation is int, but it's not enforced
            on_state_update=self._on_focus_state_change,
            on_frame=self._on_camera_frame,
        )
        self._camera_monitor.start()

        # ---- Start PC Activity Monitor ----
        # PCActivityMonitor will call _on_pc_activity when app/label changes
        self._pc_monitor = PCActivityMonitor(
            user_id=int(user_id),
            on_update=self._on_pc_activity,
        )
        self._pc_monitor.start()

        # ---- Start summary sync thread ----
        self._summary_running = True
        self._summary_thread = threading.Thread(
            target=self._summary_loop, daemon=True
        )
        self._summary_thread.start()

    def stop_session(self):
        """
        Stop monitors and background summary thread.
        """
        self._summary_running = False
        if self._summary_thread and self._summary_thread.is_alive():
            self._summary_thread.join(timeout=1.0)
        self._summary_thread = None

        if self._camera_monitor is not None:
            self._camera_monitor.stop()
            self._camera_monitor = None

        if self._pc_monitor is not None:
            self._pc_monitor.stop()
            self._pc_monitor = None

        self.user_id = None
        self._login_time = None

    # ------------------------------------------------------------------ #
    # UI callbacks & helpers
    # ------------------------------------------------------------------ #

    def register_ui_callbacks(
        self,
        on_focus_state_change: Optional[Callable[[FocusState], None]] = None,
        on_pc_activity: Optional[Callable[[Optional[str], ActivityLabel], None]] = None,
        on_camera_frame: Optional[Callable[[Any, FocusState], None]] = None,
    ) -> None:
        """
        Allow UI (EmployeeDashboard) to subscribe to focus / PC events
        without spawning its own monitors.
        """
        self._ui_focus_callback = on_focus_state_change
        self._ui_pc_callback = on_pc_activity
        self._ui_frame_callback = on_camera_frame

        if self._ui_focus_callback is not None and self._current_focus_state is not None:
            try:
                self._ui_focus_callback(self._current_focus_state)
            except Exception:
                pass

        if self._ui_pc_callback is not None and self._current_pc_label is not None:
            try:
                self._ui_pc_callback(self._current_pc_app, self._current_pc_label)
            except Exception:
                pass

    def get_counters(self) -> tuple[float, float, float]:
        """
        Return (focused_seconds, non_work_seconds, idle_seconds)
        from the underlying monitors.
        """
        focused_seconds = 0.0
        non_work_seconds = 0.0
        idle_seconds = 0.0

        if self._camera_monitor is not None:
            focused_seconds = self._camera_monitor.focused_seconds

        if self._pc_monitor is not None:
            non_work_seconds = self._pc_monitor.non_work_seconds
            idle_seconds = self._pc_monitor.idle_seconds

        return focused_seconds, non_work_seconds, idle_seconds

    def get_focus_state(self) -> FocusState:
        return self._current_focus_state

    def get_pc_activity_state(self) -> tuple[Optional[str], ActivityLabel]:
        return self._current_pc_app, self._current_pc_label

    # ------------------------------------------------------------------ #
    # INTERNAL: DB helpers
    # ------------------------------------------------------------------ #

    def _ensure_today_summary_row(self):
        """
        Ensure a daily_summaries row exists for today.
        """
        from datetime import date

        today = date.today().isoformat()

        with self._db_lock:
            cur = self.conn.cursor()

            cur.execute(
                """
                SELECT id FROM daily_summaries
                WHERE user_id = ? AND date = ?
                """,
                (self.user_id, today),
            )

            row = cur.fetchone()

            if row is None:
                cur.execute(
                    """
                    INSERT INTO daily_summaries (
                        user_id,
                        date,
                        productivity_percentage,
                        category,
                        late_minutes,
                        focused_minutes,
                        non_work_minutes,
                        idle_minutes
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        self.user_id,
                        today,
                        0.0,
                        "UNDEFINED",
                        0,
                        0,
                        0,
                        0,
                    ),
                )

            self.conn.commit()


    # ------------------------------------------------------------------ #
    # CALLBACKS FROM MONITORS
    # ------------------------------------------------------------------ #

    def _on_focus_state_change(self, state: FocusState):
        """
        Called by CameraMonitor when the *stable* focus state changes.
        Logs into focus_logs immediately.
        """
        if self.user_id is None:
            return

        self._current_focus_state = state

        with self._db_lock:
            cur = self.conn.cursor()
            cur.execute(...)
            self.conn.commit()


        score_map = {
            FocusState.FOCUSED: 100,
            FocusState.DISTRACTED: 60,
            FocusState.AWAY: 0,
        }
        score_value = score_map.get(state, 0)

        now = datetime.datetime.now().isoformat(timespec="seconds")

        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO focus_logs (user_id, timestamp, status, score_value)
            VALUES (?, ?, ?, ?)
            """,
            (self.user_id, now, state.value, score_value),
        )
        self.conn.commit()

        # propagate to UI if subscribed
        if self._ui_focus_callback is not None:
            try:
                self._ui_focus_callback(state)
            except Exception:
                pass

    def _on_pc_activity(self, app_name: Optional[str], label: ActivityLabel):
        """
        Called by PCActivityMonitor on each update.
        Logs into pc_activity_logs.
        """
        if self.user_id is None:
            return
        # Store current state for UI
        self._current_pc_app = app_name
        self._current_pc_label = label


        with self._db_lock:
            cur = self.conn.cursor()
            cur.execute(...)
            self.conn.commit()


        now = datetime.datetime.now().isoformat(timespec="seconds")

        if app_name is None:
            app_name = ""

        # Map ActivityLabel -> text type used in DB
        if label == ActivityLabel.WORK:
            type_str = "work"
        elif label == ActivityLabel.NON_WORK:
            type_str = "non_work"
        else:
            type_str = "idle"

        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO pc_activity_logs (user_id, start_time, end_time, app, type)
            VALUES (?, ?, ?, ?, ?)
            """,
            (self.user_id, now, now, app_name, type_str),
        )
        self.conn.commit()
        self._current_pc_app = app_name
        self._current_pc_label = label
        # propagate to UI if subscribed
        if self._ui_pc_callback is not None:
            try:
                self._ui_pc_callback(app_name, label)
            except Exception:
                pass

    def _on_camera_frame(self, frame: Any, state: FocusState):
        """
        Forward raw camera frame to UI if subscribed.
        """
        if self._ui_frame_callback is None:
            return
        try:
            self._ui_frame_callback(frame, state)
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # SUMMARY LOOP (daily_summaries)
    # ------------------------------------------------------------------ #

    def _summary_loop(self):
        """
        Periodically recompute productivity summary for today
        using the seconds counters from the monitors.
        """
        while self._summary_running:
            try:
                self._update_daily_summary()
            except Exception:
                # Don't crash the thread if something goes wrong
                pass
            time.sleep(30.0)  # update every 30 seconds



    def stop_session(self):
        """
        Stop monitors + summary thread and FORCE one final summary write.
        Call this when employee closes dashboard or logs out.
        """
        # stop summary thread first
        self._summary_running = False
        if self._summary_thread and self._summary_thread.is_alive():
            self._summary_thread.join(timeout=2.0)
        self._summary_thread = None

        # stop monitors
        if self._camera_monitor is not None:
            try:
                self._camera_monitor.stop()
            except Exception:
                pass
            self._camera_monitor = None

        if self._pc_monitor is not None:
            try:
                self._pc_monitor.stop()
            except Exception:
                pass
            self._pc_monitor = None

        # final flush (very important)
        try:
            self._update_daily_summary()
        except Exception:
            pass


    def shutdown(self):
        """
        Graceful shutdown hook.
        Ensures all threads stop and final data is saved.
        """
        # stop summary loop
        self._summary_running = False
        if self._summary_thread and self._summary_thread.is_alive():
            self._summary_thread.join(timeout=2.0)

        # stop camera monitor
        if self._camera_monitor:
            try:
                self._camera_monitor.stop()
            except Exception:
                pass
            self._camera_monitor = None

        # stop pc monitor
        if self._pc_monitor:
            try:
                self._pc_monitor.stop()
            except Exception:
                pass
            self._pc_monitor = None

        # FINAL SAVE (critical)
        try:
            self._update_daily_summary()
        except Exception as e:
            print("[SessionTracker] Final save failed:", e)


    def _update_daily_summary(self):
        from datetime import date

        today = date.today().isoformat()

        focused_min = int(self.focused_seconds // 60)
        non_work_min = int(self.non_work_seconds // 60)
        idle_min = int(self.idle_seconds // 60)

        score = self.productivity_calculator.calculate_score(
            focused_seconds=self.focused_seconds,
            non_work_seconds=self.non_work_seconds,
            idle_seconds=self.idle_seconds,
            late_minutes=self.late_minutes,
        )

        category = self.productivity_calculator.categorize(score).name

        with self._db_lock:
            cur = self.conn.cursor()
            cur.execute(
                """
                UPDATE daily_summaries
                SET
                    productivity_percentage = ?,
                    category = ?,
                    late_minutes = ?,
                    focused_minutes = ?,
                    non_work_minutes = ?,
                    idle_minutes = ?
                WHERE user_id = ? AND date = ?
                """,
                (
                    score,
                    category,
                    self.late_minutes,
                    focused_min,
                    non_work_min,
                    idle_min,
                    self.user_id,
                    today,
                ),
            )
            self.conn.commit()

