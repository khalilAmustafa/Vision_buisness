
# monitoring/shift_tracker.py

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Callable, Optional

from monitoring.i_monitor import IMonitor


class ShiftStatus(str, Enum):
    """
    High-level state of the current day shift.
    """
    NO_SHIFT = "NO_SHIFT"
    BEFORE_SHIFT = "BEFORE_SHIFT"
    IN_SHIFT = "IN_SHIFT"
    AFTER_SHIFT = "AFTER_SHIFT"


@dataclass
class ShiftState:
    """
    Snapshot of the shift status at a given moment.
    """
    status: ShiftStatus
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    worked_minutes: int
    remaining_minutes: int
    late_minutes: int


class ShiftTracker(IMonitor):
    """
    Tracks the current employee shift:

    - Whether they are before shift, in shift, or after shift.
    - Late minutes (based on when the tracker started vs shift start).
    - Worked vs remaining minutes.

    This class is UI-framework agnostic.
    It periodically calls an optional `on_update` callback with a ShiftState,
    so the UI (PyQt, etc.) can update labels or progress bars.
    """

    def __init__(
        self,
        user_id: int,
        shift_service,
        *,
        on_update: Optional[Callable[[ShiftState], None]] = None,
        tick_seconds: float = 1.0,
    ) -> None:
        """
        Params
        ------
        user_id: int
            Currently logged-in employee ID.

        shift_service:
            Service from core.services.shift_service.ShiftService
            Expected to expose: `get_today_shift(user_id) -> shift or None`
            where shift has datetime attributes:
                - start_time
                - end_time
            (If your model uses `shift_start` / `shift_end`, just adapt in code.)

        on_update: callable(ShiftState) | None
            Optional function called on every tick with the latest state.
            In Qt you can wrap this to emit a signal.

        tick_seconds: float
            How often to recompute the state.
        """
        self.user_id = user_id
        self.shift_service = shift_service
        self.on_update = on_update
        self.tick_seconds = float(tick_seconds)

        self._running = False
        self._thread: Optional[threading.Thread] = None

        self._current_shift = None
        self._check_in_time: Optional[datetime] = None  # when tracker started

    # ------------------------------------------------------------------ #
    # IMonitor interface
    # ------------------------------------------------------------------ #

    def start(self) -> None:
        """
        Start tracking in a background thread.
        Call this after login when the employee dashboard opens.
        """
        if self._running:
            return

        self._current_shift = self.shift_service.get_today_shift(self.user_id)
        self._check_in_time = datetime.now()

        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """
        Stop tracking and join the background thread.
        """
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None

    # ------------------------------------------------------------------ #
    # Internal loop
    # ------------------------------------------------------------------ #

    def _loop(self) -> None:
        """
        Background loop; recomputes state every `tick_seconds`.
        """
        while self._running:
            state = self._compute_state(datetime.now())
            if self.on_update is not None:
                try:
                    self.on_update(state)
                except Exception:
                    # Avoid killing the thread because of UI errors.
                    pass
            time.sleep(self.tick_seconds)

    # ------------------------------------------------------------------ #
    # Core logic (pure, testable)
    # ------------------------------------------------------------------ #

    def _compute_state(self, now: datetime) -> ShiftState:
        """
        Compute the current ShiftState at a given time.
        This is pure logic and easy to unit-test.
        """
        if self._current_shift is None:
            # No shift for today
            return ShiftState(
                status=ShiftStatus.NO_SHIFT,
                start_time=None,
                end_time=None,
                worked_minutes=0,
                remaining_minutes=0,
                late_minutes=0,
            )

        # Adjust attribute names if your Shift model uses different ones.
        start: datetime = getattr(self._current_shift, "start_time")
        end: datetime = getattr(self._current_shift, "end_time")

        # Late minutes: how late the employee opened the app
        late_minutes = 0
        if self._check_in_time is not None and self._check_in_time > start:
            late_minutes = int((self._check_in_time - start).total_seconds() // 60)

        if now < start:
            status = ShiftStatus.BEFORE_SHIFT
            worked_minutes = 0
            remaining_minutes = max(0, int((start - now).total_seconds() // 60))
        elif start <= now <= end:
            status = ShiftStatus.IN_SHIFT
            worked_minutes = int((now - start).total_seconds() // 60)
            remaining_minutes = max(0, int((end - now).total_seconds() // 60))
        else:
            status = ShiftStatus.AFTER_SHIFT
            worked_minutes = int((end - start).total_seconds() // 60)
            remaining_minutes = 0

        return ShiftState(
            status=status,
            start_time=start,
            end_time=end,
            worked_minutes=worked_minutes,
            remaining_minutes=remaining_minutes,
            late_minutes=late_minutes,
        )
