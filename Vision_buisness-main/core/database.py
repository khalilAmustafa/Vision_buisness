import os
import sqlite3


class Database:
    def __init__(self):
        # --------------------------------------------------
        # Force ONE database location for the whole project
        # Project root = parent directory of "core"
        # --------------------------------------------------
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.db_path = os.path.join(base_dir, "vision.db")

        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

        self._create_tables()

    def get_connection(self):
        return self.conn

    # --------------------------------------------------
    # Create tables if they don't exist
    # --------------------------------------------------
    def _create_tables(self):
        cur = self.conn.cursor()

        # USERS
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                username TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL
            )
            """
        )

        # SHIFTS
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS shifts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                shift_start TEXT NOT NULL,
                shift_end TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )

        # FOCUS LOGS
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS focus_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                status TEXT NOT NULL,
                score_value INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )

        # PC ACTIVITY LOGS
        # NOTE: Schema matches core/session_tracker.py and core/models/activity_log.py
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS pc_activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                app TEXT,
                type TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )

        # DAILY SUMMARIES
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                date TEXT NOT NULL,
                productivity_percentage REAL NOT NULL,
                category TEXT NOT NULL,
                late_minutes INTEGER NOT NULL,
                focused_minutes INTEGER NOT NULL,
                non_work_minutes INTEGER NOT NULL,
                idle_minutes INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )

        self.conn.commit()
