# core/create_default_users.py

from .database import Database


def main():
    db = Database()
    conn = db.get_connection()
    cur = conn.cursor()

    # Manager: ID = "0000"
    cur.execute(
        """
        INSERT OR IGNORE INTO users (id, name, username, password_hash, role)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            "0000",
            "System Manager",
            "System Manager",  # username is a name, not used for login
            "0000",
            "manager",
        ),
    )

    # Employee: ID = "0001"
    cur.execute(
        """
        INSERT OR IGNORE INTO users (id, name, username, password_hash, role)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            "0001",
            "Test Employee",
            "Test Employee",
            "0001",
            "employee",
        ),
    )

    conn.commit()
    print("Default users ready: 0000/0000 (manager), 0001/0001 (employee)")


if __name__ == "__main__":
    main()
