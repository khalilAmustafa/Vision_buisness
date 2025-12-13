# core/models/shift.py

class Shift:
    def __init__(self, id, user_id, shift_start, shift_end):
        self.id = id
        self.user_id = user_id
        self.shift_start = shift_start  # ISO string for now
        self.shift_end = shift_end

    def __repr__(self):
        return f"<Shift id={self.id} user_id={self.user_id} {self.shift_start} -> {self.shift_end}>"
