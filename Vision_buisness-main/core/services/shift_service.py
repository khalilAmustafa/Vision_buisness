# core/services/shift_service.py

from typing import Optional, List, Tuple
from datetime import datetime, date

from core.database import Database
from core.models.shift import Shift


class ShiftService:
    """Access to `shifts` table in a model-friendly way."""

    def __init__(self, db: Database):
        self.db = db

    def get_shift_for_user(self, user_id: str) -> Optional[Shift]:
        """
        Return the latest shift for a user, or None if not set.
        """
        conn = self.db.get_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM shifts WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user_id,),
        )
        row = cur.fetchone()
        if row is None:
            return None

        return Shift(
            id=row["id"],
            user_id=row["user_id"],
            shift_start=row["shift_start"],
            shift_end=row["shift_end"],
        )

    # ------------------------------------------------------------------
    # New helpers used by ShiftTracker and manager UI
    # ------------------------------------------------------------------

    def get_today_shift(self, user_id: str) -> Optional[Shift]:
        """
        Return the shift that applies "today" for the given user.

        For now we simply return the latest shift, assuming one active
        shift template per user.
        """
        return self.get_shift_for_user(user_id)

    def set_shift_for_user(self, user_id: str, shift_start: str, shift_end: str) -> None:
        """
        Create or update a shift for a user.

        We keep it simple: if a shift exists, update the latest one,
        otherwise insert a new row.

        shift_start / shift_end are stored as TEXT (e.g. "09:00", "17:00"
        or full ISO strings, depending on how you want to use them).
        """
        conn = self.db.get_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT id FROM shifts WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user_id,),
        )
        row = cur.fetchone()

        if row is None:
            cur.execute(
                """
                INSERT INTO shifts (user_id, shift_start, shift_end)
                VALUES (?, ?, ?)
                """,
                (user_id, shift_start, shift_end),
            )
        else:
            cur.execute(
                """
                UPDATE shifts
                SET shift_start = ?, shift_end = ?
                WHERE id = ?
                """,
                (shift_start, shift_end, row["id"]),
            )

        conn.commit()

    def list_all_shifts(self) -> List[Tuple[str, str, str]]:
        """
        Return a list of (user_id, shift_start, shift_end) for manager UI.
        """
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT user_id, shift_start, shift_end FROM shifts ORDER BY user_id"
        )
        return [(row["user_id"], row["shift_start"], row["shift_end"]) for row in cur.fetchall()]
