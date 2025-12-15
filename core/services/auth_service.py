# core/services/auth_service.py

from typing import Optional

from core.database import Database
from core.models.user import User


class AuthService:
    """
    Authentication helper for Vision.

    NOTE:
    Right now passwords are stored as plain text in `password_hash`
    (see core/create_default_users.py and ui/main.py), so we just
    compare them directly. Later you can switch to hashing.
    """

    def __init__(self, db: Database):
        self.db = db

    def login(self, username: str, password: str) -> Optional[User]:
        """
        Login by username OR by ID (we use the same parameter for both).

        Returns:
            User on success, or None on failure.
        """
        conn = self.db.get_connection()
        cur = conn.cursor()

        # Try match by username first, then by id for flexibility
        cur.execute(
            "SELECT * FROM users WHERE username = ? OR id = ?",
            (username, username),
        )
        row = cur.fetchone()
        if row is None:
            return None

        if row["password_hash"] != password:
            return None

        return User(
            user_id=row["id"],
            name=row["name"],
            username=row["username"],
            password_hash=row["password_hash"],
            role=row["role"],
        )
