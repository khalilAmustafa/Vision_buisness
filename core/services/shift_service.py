# core/services/shift_service.py

from typing import Optional

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
            shift_id=row["id"],
            user_id=row["user_id"],
            shift_start=row["shift_start"],
            shift_end=row["shift_end"],
        )
