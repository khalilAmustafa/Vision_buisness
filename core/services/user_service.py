from core.models.user import User
from core.database import Database


class UserService:
    def __init__(self, db: Database):
        self.db = db
        self.conn = db.get_connection()

    # ---------------------------------------------------
    # Add user
    # ---------------------------------------------------
    def add_user(self, user: User) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO users (id, name, username, password_hash, role)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user.id, user.name, user.username, user.password_hash, user.role),
        )
        self.conn.commit()



    def delete_user(self, user_id: str) -> None:
        """
        Deletes a user and all related data (safe delete).
        """
        conn = self.db.get_connection()
        cur = conn.cursor()

        # Prevent deleting the default manager (optional but recommended)
        if user_id == "0000":
            raise ValueError("Cannot delete the default manager (0000).")

        # Delete dependents first (order matters)
        cur.execute("DELETE FROM focus_logs WHERE user_id = ?", (user_id,))
        cur.execute("DELETE FROM pc_activity_logs WHERE user_id = ?", (user_id,))
        cur.execute("DELETE FROM daily_summaries WHERE user_id = ?", (user_id,))
        cur.execute("DELETE FROM shifts WHERE user_id = ?", (user_id,))

        # Finally delete the user
        cur.execute("DELETE FROM users WHERE id = ?", (user_id,))

        conn.commit()

        
    # ---------------------------------------------------
    # Alias for old scripts
    # ---------------------------------------------------
    def create_user(self, user: User) -> None:
        return self.add_user(user)
