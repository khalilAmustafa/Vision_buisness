from datetime import date
from typing import List, Dict, Any, Optional

from core.database import Database
from manager.base_report_controller import BaseReportController


class ReportController(BaseReportController):
    """
    Simple report controller that aggregates data for manager reports.
    """

    def __init__(self, db: Database):
        self.db = db
        self.conn = db.get_connection()

    def generate_report(
        self,
        user_id: Optional[str] = None,
        report_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Return a dictionary with:
          - summaries: list of daily_summaries rows (possibly filtered by user/date)
          - focus_events: recent focus_logs (optional, only when user_id given)
          - pc_events: recent pc_activity_logs (optional, only when user_id given)
        """
        if report_date is None:
            report_date = date.today().isoformat()

        result: Dict[str, Any] = {}

        cur = self.conn.cursor()

        # Daily summaries
        if user_id:
            cur.execute(
                """
                SELECT *
                FROM daily_summaries
                WHERE user_id = ? AND date = ?
                ORDER BY user_id, date
                """,
                (user_id, report_date),
            )
        else:
            cur.execute(
                """
                SELECT *
                FROM daily_summaries
                WHERE date = ?
                ORDER BY user_id, date
                """,
                (report_date,),
            )

        result["summaries"] = cur.fetchall()

        # Focus logs (limited)
        if user_id:
            cur.execute(
                """
                SELECT *
                FROM focus_logs
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT 200
                """,
                (user_id,),
            )
            result["focus_events"] = cur.fetchall()

            cur.execute(
                """
                SELECT *
                FROM pc_activity_logs
                WHERE user_id = ?
                ORDER BY start_time DESC
                LIMIT 200
                """,
                (user_id,),
            )
            result["pc_events"] = cur.fetchall()

        return result

