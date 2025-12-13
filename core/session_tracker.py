# core/session_tracker.py

from __future__ import annotations

import datetime
import threading
import time
from typing import Optional

from core.database import Database
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

        self.user_id: Optional[str] = None
        self._camera_monitor: Optional[CameraMonitor] = None
        self._pc_monitor: Optional[PCActivityMonitor] = None

        self._productivity_calc = ProductivityCalculator()
        self._summary_thread: Optional[threading.Thread] = None
        self._summary_running: bool = False

        # last known focus state (for logging)
        self._current_focus_state: FocusState = FocusState.AWAY

    # ------------------------------------------------------------------ #
    # PUBLIC API
    # ------------------------------------------------------------------ #

    def start_session(self, user_id: str):
        """
        Called when employee logs in.
        """
        self.user_id = user_id

        # Make sure daily_summaries row for today exists
        self._ensure_today_summary_row()

        # ---- Start Camera Monitor ----
        # CameraMonitor will call _on_focus_state_change when state changes
        self._camera_monitor = CameraMonitor(
            user_id=int(user_id),  # annotation is int, but it's not enforced
            on_state_update=self._on_focus_state_change,
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

    # ------------------------------------------------------------------ #
    # INTERNAL: DB helpers
    # ------------------------------------------------------------------ #

    def _ensure_today_summary_row(self):
        """
        Ensure there is a daily_summaries row for (user_id, today).
        """
        if self.user_id is None:
            return

        today = datetime.date.today().isoformat()
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT OR IGNORE INTO daily_summaries (
                user_id,
                date,
                productivity_percentage,
                category,
                late_minutes,
                focused_minutes,
                non_work_minutes,
                idle_minutes
            )
            VALUES (?, ?, 0, 'Unknown', 0, 0, 0, 0)
            """,
            (self.user_id, today),
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

    def _on_pc_activity(self, app_name: Optional[str], label: ActivityLabel):
        """
        Called by PCActivityMonitor on each update.
        Logs into pc_activity_logs.
        """
        if self.user_id is None:
            return

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

    def _update_daily_summary(self):
        if self.user_id is None:
            return

        focused_seconds = 0.0
        non_work_seconds = 0.0
        idle_seconds = 0.0

        # Get seconds from monitors (they accumulate internally)
        if self._camera_monitor is not None:
            focused_seconds = self._camera_monitor.focused_seconds
            # We ignore distracted/away seconds for score, but you could use them

        if self._pc_monitor is not None:
            non_work_seconds = self._pc_monitor.non_work_seconds
            idle_seconds = self._pc_monitor.idle_seconds

        # Late minutes from shift can be integrated later; 0 for now
        late_minutes = 0

        # Calculate score
        score = self._productivity_calc.calculate_score(
            focused_seconds=focused_seconds,
            non_work_seconds=non_work_seconds,
            idle_seconds=idle_seconds,
            late_minutes=late_minutes,
        )
        category = self._productivity_calc.categorize(score).value

        # Convert seconds to minutes for summary
        focused_minutes = int(focused_seconds // 60)
        non_work_minutes = int(non_work_seconds // 60)
        idle_minutes = int(idle_seconds // 60)

        today = datetime.date.today().isoformat()

        cur = self.conn.cursor()
        cur.execute(
            """
            UPDATE daily_summaries
            SET
                productivity_percentage = ?,
                category = ?,
                focused_minutes = ?,
                non_work_minutes = ?,
                idle_minutes = ?
            WHERE user_id = ? AND date = ?
            """,
            (
                score,
                category,
                focused_minutes,
                non_work_minutes,
                idle_minutes,
                self.user_id,
                today,
            ),
        )
        self.conn.commit()
