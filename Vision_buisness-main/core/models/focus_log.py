# core/models/focus_log.py

class FocusLog:
    def __init__(self, id, user_id, timestamp, status, score_value):
        self.id = id
        self.user_id = user_id
        self.timestamp = timestamp      # ISO datetime string
        self.status = status            # 'focused', 'away', etc.
        self.score_value = score_value  # 0–100

    def __repr__(self):
        return f"<FocusLog id={self.id} user_id={self.user_id} status={self.status} score={self.score_value}>"
