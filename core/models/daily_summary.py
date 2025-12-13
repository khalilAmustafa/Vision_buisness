# core/models/daily_summary.py

class DailySummary:
    def __init__(
        self,
        id,
        user_id,
        date,
        productivity_percentage,
        category,
        late_minutes,
        focused_minutes,
        non_work_minutes,
        idle_minutes,
    ):
        self.id = id
        self.user_id = user_id
        self.date = date  # 'YYYY-MM-DD'
        self.productivity_percentage = productivity_percentage
        self.category = category
        self.late_minutes = late_minutes
        self.focused_minutes = focused_minutes
        self.non_work_minutes = non_work_minutes
        self.idle_minutes = idle_minutes

    def __repr__(self):
        return (
            f"<DailySummary id={self.id} user_id={self.user_id} "
            f"date={self.date} prod={self.productivity_percentage}>"
        )
