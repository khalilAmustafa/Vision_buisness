# core/services/summary_service.py

from typing import Optional

from core.database import Database
from core.models.daily_summary import DailySummary


class SummaryService:
    """Read/write access for the `daily_summaries` table."""

    def __init__(self, db: Database):
        self.db = db

    def save_summary(self, summary: DailySummary) -> None:
        """
        Insert or update a summary for (user_id, date).

        If summary.id is None → insert.
        Otherwise → update.
        """
        conn = self.db.get_connection()
        cur = conn.cursor()

        if getattr(summary, "id", None) is None:
            cur.execute(
                """
                INSERT INTO daily_summaries (
                    user_id, date, productivity_percentage, category,
                    late_minutes, focused_minutes, non_work_minutes, idle_minutes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    summary.user_id,
                    summary.date,
                    summary.productivity,
                    summary.category,
                    summary.late_minutes,
                    summary.focused_minutes,
                    summary.non_work_minutes,
                    summary.idle_minutes,
                ),
            )
            summary.id = cur.lastrowid
        else:
            cur.execute(
                """
                UPDATE daily_summaries
                SET user_id = ?,
                    date = ?,
                    productivity_percentage = ?,
                    category = ?,
                    late_minutes = ?,
                    focused_minutes = ?,
                    non_work_minutes = ?,
                    idle_minutes = ?
                WHERE id = ?
                """,
                (
                    summary.user_id,
                    summary.date,
                    summary.productivity,
                    summary.category,
                    summary.late_minutes,
                    summary.focused_minutes,
                    summary.non_work_minutes,
                    summary.idle_minutes,
                    summary.id,
                ),
            )

        conn.commit()

    def get_summary(self, user_id: str, date: str) -> Optional[DailySummary]:
        """Return DailySummary for (user_id, date) or None."""
        conn = self.db.get_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT *
            FROM daily_summaries
            WHERE user_id = ? AND date = ?
            """,
            (user_id, date),
        )
        row = cur.fetchone()
        if row is None:
            return None

        return DailySummary(
            summary_id=row["id"],
            user_id=row["user_id"],
            date=row["date"],
            productivity=row["productivity_percentage"],
            category=row["category"],
            late_minutes=row["late_minutes"],
            focused_minutes=row["focused_minutes"],
            non_work_minutes=row["non_work_minutes"],
            idle_minutes=row["idle_minutes"],
        )
