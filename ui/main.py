import sys
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QComboBox,
)

from core.database import Database
from core.session_tracker import SessionTracker
from ui.employee_dashboard import EmployeeDashboard


class ManagerWindow(QMainWindow):
    def __init__(self, db: Database):
        super().__init__()

        self.db = db
        self.conn = db.get_connection()

        self.setWindowTitle("Vision – Manager Dashboard (Beta)")
        self.setMinimumSize(850, 500)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("Manager – Employee Management (Beta)")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        # ---------------- EMPLOYEE TABLE ----------------
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Username", "Role"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        layout.addWidget(QLabel("Registered Users:"))
        layout.addWidget(self.table)

        # ---------------- ADD EMPLOYEE FORM ----------------
        layout.addWidget(QLabel("Add New User:"))

        form = QHBoxLayout()

        self.id_input = QLineEdit()
        self.id_input.setPlaceholderText("ID (e.g., 0002)")
        form.addWidget(self.id_input)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Name")
        form.addWidget(self.name_input)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        form.addWidget(self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        form.addWidget(self.password_input)

        self.role_combo = QComboBox()
        self.role_combo.addItems(["employee", "manager"])
        form.addWidget(self.role_combo)

        self.add_button = QPushButton("Add User")
        self.add_button.clicked.connect(self.add_user)
        form.addWidget(self.add_button)

        layout.addLayout(form)

        # Refresh button
        refresh_btn = QPushButton("Refresh User List")
        refresh_btn.clicked.connect(self.load_users)
        layout.addWidget(refresh_btn)

        self.setCentralWidget(central)

        # Load initial table data
        self.load_users()

    # ---------------------------------------------------
    # Load all users from DB
    # ---------------------------------------------------
    def load_users(self):
        self.table.setRowCount(0)

        cur = self.conn.cursor()
        cur.execute("SELECT id, name, username, role FROM users ORDER BY id")
        rows = cur.fetchall()

        for row_idx, row in enumerate(rows):
            self.table.insertRow(row_idx)
            self.table.setItem(row_idx, 0, QTableWidgetItem(str(row["id"])))
            self.table.setItem(row_idx, 1, QTableWidgetItem(row["name"]))
            self.table.setItem(row_idx, 2, QTableWidgetItem(row["username"]))
            self.table.setItem(row_idx, 3, QTableWidgetItem(row["role"]))

    # ---------------------------------------------------
    # Add user to DB
    # ---------------------------------------------------
    def add_user(self):
        user_id = self.id_input.text().strip()
        name = self.name_input.text().strip()
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        role = self.role_combo.currentText().strip()

        if not user_id or not name or not username or not password:
            QMessageBox.warning(self, "Missing Data", "Please fill all fields.")
            return

        try:
            cur = self.conn.cursor()
            cur.execute(
                """
                INSERT INTO users (id, name, username, password_hash, role)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, name, username, password, role),
            )
            self.conn.commit()

            QMessageBox.information(self, "Success", f"User '{username}' added.")
            self.id_input.clear()
            self.name_input.clear()
            self.username_input.clear()
            self.password_input.clear()

            self.load_users()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to add user:\n{e}")


class LoginWindow(QMainWindow):
    def __init__(self, db: Database):
        super().__init__()

        self.db = db
        self.conn = db.get_connection()

        self._manager_window = None
        self._employee_window = None

        # Session tracker for pc_activity_logs, focus_logs, daily_summaries
        self.session_tracker = SessionTracker(self.db)

        # ---------------- UI SETUP ----------------
        self.setWindowTitle("Vision – Login")
        self.setFixedSize(400, 260)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        title_label = QLabel("Sign in to Vision")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title_label)

        # ------ ID FIELD ------
        id_row = QHBoxLayout()
        id_label = QLabel("ID:")
        self.id_input = QLineEdit()
        self.id_input.setPlaceholderText("Enter ID (e.g., 0000 / 0001)")
        id_row.addWidget(id_label)
        id_row.addWidget(self.id_input)
        layout.addLayout(id_row)

        # ------ PASSWORD ------
        pass_row = QHBoxLayout()
        pass_label = QLabel("Password:")
        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.Password)
        self.pass_input.setPlaceholderText("Enter password")
        pass_row.addWidget(pass_label)
        pass_row.addWidget(self.pass_input)
        layout.addLayout(pass_row)

        # ------ LOGIN BUTTON ------
        login_btn = QPushButton("Login")
        login_btn.clicked.connect(self.handle_login)
        layout.addWidget(login_btn)

        info_label = QLabel(
            "Temporary accounts:\n"
            "Manager  → ID: 0000, Pass: 0000\n"
            "Employee → ID: 0001, Pass: 0001"
        )
        info_label.setStyleSheet("font-size: 11px; color: gray;")
        layout.addWidget(info_label)

        self.setCentralWidget(central)

    # ---------------------------------------------------
    # LOGIN HANDLER
    # ---------------------------------------------------
    def handle_login(self):
        user_id = self.id_input.text().strip()
        password = self.pass_input.text().strip()

        if not user_id or not password:
            QMessageBox.warning(self, "Login failed", "Please enter ID and password.")
            return

        # Query from DB using TEXT ID
        cur = self.conn.cursor()
        cur.execute(
            "SELECT id, name, role, password_hash FROM users WHERE id = ?",
            (user_id,),
        )
        row = cur.fetchone()

        if row is None:
            QMessageBox.warning(self, "Login failed", "User not found.")
            return

        if row["password_hash"] != password:
            QMessageBox.warning(self, "Login failed", "Invalid password.")
            return

        role = row["role"]

        if role == "manager":
            self.open_manager()
        elif role == "employee":
            self.open_employee(row["id"])
        else:
            QMessageBox.warning(self, "Error", f"Unknown role: {role}")

    # ---------------------------------------------------
    # OPEN MANAGER UI
    # ---------------------------------------------------
    def open_manager(self):
        if self._manager_window is None:
            self._manager_window = ManagerWindow(self.db)

        self._manager_window.show()
        self.hide()

    # ---------------------------------------------------
    # OPEN EMPLOYEE UI  (with session tracking)
    # ---------------------------------------------------
    def open_employee(self, user_id: str):
        """
        Called after successful employee login.
        Starts monitoring session and opens the employee dashboard.
        """

        # Start monitoring (PC logs, focus logs, daily summaries)
        self.session_tracker.start_session(user_id)

        # Create dashboard if not created
        if self._employee_window is None:
            self._employee_window = EmployeeDashboard(user_id=user_id)

        self._employee_window.show()
        self.hide()


# ---------------------------------------------------
# MAIN ENTRY
# ---------------------------------------------------
def main():
    db = Database()
    app = QApplication(sys.argv)
    window = LoginWindow(db)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
