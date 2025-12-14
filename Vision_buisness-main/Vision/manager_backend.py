import sqlite3
import bcrypt
from database import get_connection


# ------------------------------------------------
# Add employee
# ------------------------------------------------
def add_employee(name, username, password, role="employee"):
    conn = get_connection()
    c = conn.cursor()

    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    default_start = "09:00"
    default_end = "17:00"

    try:
        conn.execute("BEGIN")

        c.execute("""
            INSERT INTO users (name, username, password_hash, role)
            VALUES (?, ?, ?, ?)
        """, (name, username, password_hash, role))

        user_id = c.lastrowid

        c.execute("""
            INSERT INTO shifts (user_id, shift_start, shift_end)
            VALUES (?, ?, ?)
        """, (user_id, default_start, default_end))

        conn.commit()
        return True

    except sqlite3.IntegrityError:
        conn.rollback()
        return False

    finally:
        conn.close()


# ------------------------------------------------
# Get all employees
# ------------------------------------------------
def get_all_employees():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, name, username, role FROM users WHERE role='employee'")
    data = c.fetchall()
    conn.close()
    return data


# ------------------------------------------------
# DELETE employee
# (Cascade will remove shift)
# ------------------------------------------------
def delete_employee(user_id):
    conn = get_connection()
    c = conn.cursor()

    try:
        conn.execute("BEGIN")
        c.execute("DELETE FROM users WHERE id=?", (user_id,))
        conn.commit()
        return True

    except sqlite3.Error:
        conn.rollback()
        return False

    finally:
        conn.close()


# ------------------------------------------------
# FETCH full employee data for editing
# ------------------------------------------------
def get_employee_data(user_id):
    conn = get_connection()
    c = conn.cursor()

    # user
    c.execute("SELECT id, name, username, role FROM users WHERE id=?", (user_id,))
    user_info = c.fetchone()

    # shift
    c.execute("SELECT shift_start, shift_end FROM shifts WHERE user_id=?", (user_id,))
    shift = c.fetchone()

    conn.close()

    return {
        "user_info": user_info,
        "shift": shift
    }


# ------------------------------------------------
# UPDATE employee basic info
# ------------------------------------------------
def update_employee_basic(user_id, name, username, new_password=None):
    conn = get_connection()
    c = conn.cursor()

    try:
        conn.execute("BEGIN")

        if new_password:
            password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()

            c.execute("""
                UPDATE users
                SET name=?, username=?, password_hash=?
                WHERE id=?
            """, (name, username, password_hash, user_id))

        else:
            c.execute("""
                UPDATE users
                SET name=?, username=?
                WHERE id=?
            """, (name, username, user_id))

        conn.commit()
        return True

    except sqlite3.IntegrityError:
        conn.rollback()
        return False

    finally:
        conn.close()


# ------------------------------------------------
# UPDATE employee shift
# ------------------------------------------------
def update_employee_shift(user_id, start, end):
    conn = get_connection()
    c = conn.cursor()

    try:
        conn.execute("BEGIN")

        c.execute("""
            UPDATE shifts
            SET shift_start=?, shift_end=?
            WHERE user_id=?
        """, (start, end, user_id))

        conn.commit()
        return True

    except sqlite3.Error:
        conn.rollback()
        return False

    finally:
        conn.close()
