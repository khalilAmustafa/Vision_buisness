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

    # ---------------------------------------------------
    # Alias for old scripts
    # ---------------------------------------------------
    def create_user(self, user: User) -> None:
        return self.add_user(user)
