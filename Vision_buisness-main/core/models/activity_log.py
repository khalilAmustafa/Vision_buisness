# core/models/activity_log.py

class ActivityLog:
    def __init__(self, id, user_id, start_time, end_time, activity, type_):
        self.id = id
        self.user_id = user_id
        self.start_time = start_time  # ISO datetime string
        self.end_time = end_time
        self.activity = activity      # app name / website
        self.type = type_             # 'work' / 'non_work' / 'idle'

    def __repr__(self):
        return f"<ActivityLog id={self.id} user_id={self.user_id} type={self.type} activity={self.activity}>"
