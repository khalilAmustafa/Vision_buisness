import sys
from PyQt5.QtCore import Qt, QTime
from PyQt5.QtGui import QPainter, QColor
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
    QTabWidget,
    QTimeEdit,
    QAbstractItemView,
    QFrame,
    QGridLayout,
    QSizePolicy,
    QSpacerItem,
)
from PyQt5.QtChart import QChart, QChartView, QBarSet, QBarSeries, QBarCategoryAxis

from core.database import Database
from core.session_tracker import SessionTracker
from core.services.shift_service import ShiftService
from manager.report_controller import ReportController
from ui.employee_dashboard import EmployeeDashboard
from ui.theme import apply_theme


class ManagerWindow(QMainWindow):
    def __init__(self, db: Database):
        super().__init__()

        self.db = db
        self.conn = db.get_connection()
        self.shift_service = ShiftService(self.db)
        self.report_controller = ReportController(self.db)

        self.setWindowTitle("Vision • Manager Console")
        self.setMinimumSize(1024, 600)
        self.resize(1300, 760)

        central = QWidget()
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(24, 24, 24, 24)
        root_layout.setSpacing(16)

        root_layout.addWidget(self._build_header_card())

        tabs_container = QFrame()
        tabs_container.setObjectName("Card")
        tabs_layout = QVBoxLayout(tabs_container)
        tabs_layout.setContentsMargins(12, 12, 12, 12)
        self.tabs = QTabWidget()
        tabs_layout.addWidget(self.tabs)
        tabs_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        root_layout.addWidget(tabs_container, 1)

        self._build_tabs()

        self.setCentralWidget(central)

        self.load_users()
        self.load_shifts()
        self.refresh_reports()
        self._refresh_header_metrics()

    def _build_header_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setSpacing(6)

        title = QLabel("Vision Command Center")
        title.setObjectName("TitleLabel")
        subtitle = QLabel("Keep every workforce insight at your fingertips.")
        subtitle.setObjectName("MutedLabel")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        metrics_layout = QHBoxLayout()
        metrics_layout.setSpacing(18)
        self.metric_total = self._create_metric_widget("Total Users")
        self.metric_employees = self._create_metric_widget("Employees")
        self.metric_managers = self._create_metric_widget("Managers")
        metrics_layout.addWidget(self.metric_total)
        metrics_layout.addWidget(self.metric_employees)
        metrics_layout.addWidget(self.metric_managers)
        metrics_layout.addStretch(1)
        layout.addLayout(metrics_layout)
        return card

    def _create_metric_widget(self, label_text: str) -> QWidget:
        card = QFrame()
        card.setObjectName("Card")
        card.setStyleSheet("QFrame#Card { padding: 12px; }")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 8, 8, 8)
        name = QLabel(label_text)
        name.setObjectName("MutedLabel")
        value = QLabel("--")
        value.setObjectName("MetricValue")
        layout.addWidget(name)
        layout.addWidget(value)
        card.value_label = value  # type: ignore
        return card

    def _refresh_header_metrics(self):
        cur = self.conn.cursor()
        total = cur.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
        employees = cur.execute("SELECT COUNT(*) AS c FROM users WHERE role='employee'").fetchone()["c"]
        managers = total - employees
        self.metric_total.value_label.setText(str(total))
        self.metric_employees.value_label.setText(str(employees))
        self.metric_managers.value_label.setText(str(managers))

    def _build_tabs(self):
        self._users_tab = QWidget()
        users_layout = QVBoxLayout(self._users_tab)
        users_layout.setSpacing(14)

        table_card = QFrame()
        table_card.setObjectName("Card")
        table_layout = QVBoxLayout(table_card)
        table_layout.addWidget(QLabel("Registered Users"))

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Username", "Role"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        table_layout.addWidget(self.table)
        users_layout.addWidget(table_card)

        form_card = QFrame()
        form_card.setObjectName("Card")
        form_layout = QGridLayout(form_card)
        form_layout.setSpacing(12)

        self.id_input = QLineEdit()
        self.id_input.setPlaceholderText("ID (e.g., 0002)")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Name")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)

        self.role_combo = QComboBox()
        self.role_combo.addItems(["employee", "manager"])

        add_btn = QPushButton("Add User")
        add_btn.clicked.connect(self.add_user)
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setObjectName("SecondaryButton")
        refresh_btn.clicked.connect(self.load_users)

        form_layout.addWidget(QLabel("User ID"), 0, 0)
        form_layout.addWidget(self.id_input, 1, 0)
        form_layout.addWidget(QLabel("Name"), 0, 1)
        form_layout.addWidget(self.name_input, 1, 1)
        form_layout.addWidget(QLabel("Username"), 2, 0)
        form_layout.addWidget(self.username_input, 3, 0)
        form_layout.addWidget(QLabel("Password"), 2, 1)
        form_layout.addWidget(self.password_input, 3, 1)
        form_layout.addWidget(QLabel("Role"), 4, 0)
        form_layout.addWidget(self.role_combo, 5, 0)

        btn_row = QHBoxLayout()
        btn_row.addWidget(add_btn)
        btn_row.addWidget(refresh_btn)
        btn_row.addStretch(1)
        form_layout.addLayout(btn_row, 5, 1)

        users_layout.addWidget(form_card)
        self.tabs.addTab(self._users_tab, "People")

        # Shifts tab
        self._shifts_tab = QWidget()
        shifts_layout = QVBoxLayout(self._shifts_tab)
        shifts_layout.setSpacing(12)

        shift_table_card = QFrame()
        shift_table_card.setObjectName("Card")
        st_layout = QVBoxLayout(shift_table_card)
        st_layout.addWidget(QLabel("Active Schedules"))

        self.shift_table = QTableWidget()
        self.shift_table.setColumnCount(3)
        self.shift_table.setHorizontalHeaderLabels(["User ID", "Shift Start", "Shift End"])
        self.shift_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.shift_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.shift_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.shift_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.shift_table.itemSelectionChanged.connect(self._on_shift_row_selected)
        st_layout.addWidget(self.shift_table)
        shifts_layout.addWidget(shift_table_card)

        controls_card = QFrame()
        controls_card.setObjectName("Card")
        controls_layout = QHBoxLayout(controls_card)
        controls_layout.setSpacing(12)
        controls_layout.addWidget(QLabel("Start time"))
        self.shift_start_edit = QTimeEdit()
        self.shift_start_edit.setDisplayFormat("HH:mm")
        self.shift_start_edit.setTime(QTime(9, 0))
        controls_layout.addWidget(self.shift_start_edit)
        controls_layout.addWidget(QLabel("End time"))
        self.shift_end_edit = QTimeEdit()
        self.shift_end_edit.setDisplayFormat("HH:mm")
        self.shift_end_edit.setTime(QTime(17, 0))
        controls_layout.addWidget(self.shift_end_edit)

        save_btn = QPushButton("Save Shift")
        save_btn.clicked.connect(self.save_selected_shift)
        refresh_shifts_btn = QPushButton("Refresh")
        refresh_shifts_btn.setObjectName("SecondaryButton")
        refresh_shifts_btn.clicked.connect(self.load_shifts)
        controls_layout.addWidget(save_btn)
        controls_layout.addWidget(refresh_shifts_btn)
        controls_layout.addStretch(1)
        shifts_layout.addWidget(controls_card)
        self.tabs.addTab(self._shifts_tab, "Shifts")

        # Reports tab
        self._reports_tab = QWidget()
        reports_layout = QVBoxLayout(self._reports_tab)
        reports_layout.setSpacing(12)

        chart_card = QFrame()
        chart_card.setObjectName("Card")
        chart_layout = QVBoxLayout(chart_card)
        section_label = QLabel("Productivity Overview (Today)")
        chart_layout.addWidget(section_label)

        self.chart = QChart()
        self.chart.setAnimationOptions(QChart.SeriesAnimations)
        self.chart.legend().setVisible(False)
        self.chart.setBackgroundBrush(QColor("#FFFFFF"))

        self.chart_view = QChartView(self.chart)
        self.chart_view.setRenderHint(QPainter.Antialiasing)
        self.chart_view.setMinimumHeight(320)
        chart_layout.addWidget(self.chart_view)

        refresh_reports_btn = QPushButton("Refresh")
        refresh_reports_btn.setObjectName("SecondaryButton")
        refresh_reports_btn.clicked.connect(self.refresh_reports)
        chart_layout.addWidget(refresh_reports_btn, alignment=Qt.AlignRight)

        reports_layout.addWidget(chart_card)
        self.tabs.addTab(self._reports_tab, "Reports")

    # ------------------------------------------------------------------ #
    # Users tab logic
    # ------------------------------------------------------------------ #
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
        self._refresh_header_metrics()

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
            self.load_shifts()
            self.refresh_reports()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to add user:\n{e}")

    # ------------------------------------------------------------------ #
    # Shifts tab logic
    # ------------------------------------------------------------------ #
    def load_shifts(self):
        cur = self.conn.cursor()
        cur.execute("SELECT id FROM users ORDER BY id")
        users = cur.fetchall()

        self.shift_table.setRowCount(len(users))
        for idx, row in enumerate(users):
            user_id = str(row["id"])
            shift = self.shift_service.get_shift_for_user(user_id)
            start = shift.shift_start if shift and shift.shift_start else ""
            end = shift.shift_end if shift and shift.shift_end else ""

            self.shift_table.setItem(idx, 0, QTableWidgetItem(user_id))
            self.shift_table.setItem(idx, 1, QTableWidgetItem(start))
            self.shift_table.setItem(idx, 2, QTableWidgetItem(end))

        if self.shift_table.rowCount() > 0:
            self.shift_table.selectRow(0)
        else:
            self.shift_start_edit.setTime(QTime(9, 0))
            self.shift_end_edit.setTime(QTime(17, 0))

    def _on_shift_row_selected(self):
        row = self.shift_table.currentRow()
        if row < 0:
            return

        start_item = self.shift_table.item(row, 1)
        end_item = self.shift_table.item(row, 2)

        start_text = start_item.text().strip() if start_item else ""
        end_text = end_item.text().strip() if end_item else ""

        start_time = QTime.fromString(start_text, "HH:mm") if start_text else QTime(9, 0)
        end_time = QTime.fromString(end_text, "HH:mm") if end_text else QTime(17, 0)

        if not start_time.isValid():
            start_time = QTime(9, 0)
        if not end_time.isValid():
            end_time = QTime(17, 0)

        self.shift_start_edit.setTime(start_time)
        self.shift_end_edit.setTime(end_time)

    def save_selected_shift(self):
        row = self.shift_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No selection", "Select a row first.")
            return

        user_item = self.shift_table.item(row, 0)
        if user_item is None:
            QMessageBox.warning(self, "Error", "Missing user id in selected row.")
            return

        user_id = user_item.text().strip()
        shift_start = self.shift_start_edit.time().toString("HH:mm")
        shift_end = self.shift_end_edit.time().toString("HH:mm")

        try:
            self.shift_service.set_shift_for_user(user_id, shift_start, shift_end)
            QMessageBox.information(self, "Saved", "Shift updated.")
            self.load_shifts()
            self.refresh_reports()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save shift:\n{e}")

    # ------------------------------------------------------------------ #
    # Reports tab logic
    # ------------------------------------------------------------------ #
    def refresh_reports(self):
        data = self.report_controller.generate_report()
        summaries = data.get("summaries", [])

        self.chart.removeAllSeries()

        if not summaries:
            self.chart.setTitle("No productivity data for today")
            return

        categories = []
        bar_set = QBarSet("Productivity %")

        for row in summaries:
            categories.append(str(row["user_id"]))
            bar_set.append(float(row["productivity_percentage"]))

        series = QBarSeries()
        series.append(bar_set)
        self.chart.addSeries(series)
        self.chart.setTitle("Today's Productivity by Employee")

        axis_x = QBarCategoryAxis()
        axis_x.append(categories)
        axis_x.setLabelsAngle(-15)
        self.chart.createDefaultAxes()
        self.chart.setAxisX(axis_x, series)


class LoginWindow(QMainWindow):
    def __init__(self, db: Database):
        super().__init__()

        self.db = db
        self.conn = db.get_connection()

        self._manager_window = None
        self._employee_window = None

        self.session_tracker = SessionTracker(self.db)

        self.setWindowTitle("Vision • Secure Access")
        self.setMinimumSize(860, 480)
        self.resize(1100, 600)

        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        hero = QFrame()
        hero.setObjectName("HeroPanel")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(48, 48, 48, 48)
        hero_layout.setSpacing(18)
        hero_title = QLabel("Vision Intelligence")
        hero_title.setObjectName("HeroTitle")
        hero_caption = QLabel(
            "Business-grade monitoring for modern teams.\nSecure, local-first, and manager friendly."
        )
        hero_caption.setObjectName("HeroBody")
        hero_caption.setWordWrap(True)
        hero_layout.addWidget(hero_title)
        hero_layout.addWidget(hero_caption)
        hero_layout.addStretch(1)
        hero_stats = QLabel("• Productivity Insights\n• Shift Compliance\n• Focus & Activity Streams")
        hero_stats.setObjectName("HeroBody")
        hero_layout.addWidget(hero_stats)
        root.addWidget(hero, 1)

        form_wrapper = QFrame()
        form_wrapper.setObjectName("Card")
        form_layout = QVBoxLayout(form_wrapper)
        form_layout.setContentsMargins(36, 36, 36, 36)
        form_layout.setSpacing(16)

        title_label = QLabel("Sign in to Vision")
        title_label.setObjectName("TitleLabel")
        subtitle = QLabel("Use your assigned ID and password to continue.")
        subtitle.setObjectName("MutedLabel")
        form_layout.addWidget(title_label)
        form_layout.addWidget(subtitle)

        self.id_input = QLineEdit()
        self.id_input.setPlaceholderText("Employee or manager ID")
        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("Password")
        self.pass_input.setEchoMode(QLineEdit.Password)

        form_layout.addWidget(QLabel("User ID"))
        form_layout.addWidget(self.id_input)
        form_layout.addWidget(QLabel("Password"))
        form_layout.addWidget(self.pass_input)

        login_btn = QPushButton("Sign In")
        login_btn.clicked.connect(self.handle_login)
        form_layout.addWidget(login_btn)

        info_label = QLabel("Manager → ID: 0000 / Pass: 0000\nEmployee → ID: 0001 / Pass: 0001")
        info_label.setObjectName("MutedLabel")
        form_layout.addWidget(info_label)
        form_layout.addStretch(1)

        root.addWidget(form_wrapper, 1)
        self.setCentralWidget(central)

    def handle_login(self):
        user_id = self.id_input.text().strip()
        password = self.pass_input.text().strip()

        if not user_id or not password:
            QMessageBox.warning(self, "Login failed", "Please enter ID and password.")
            return

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

    def open_manager(self):
        if self._manager_window is None:
            self._manager_window = ManagerWindow(self.db)

        self._manager_window.show()
        self.hide()

    def open_employee(self, user_id: str):
        self.session_tracker.start_session(user_id)

        if self._employee_window is None:
            self._employee_window = EmployeeDashboard(
                user_id=user_id,
                session_tracker=self.session_tracker,
                db=self.db,
            )

        self._employee_window.show()
        self.hide()


def main():
    db = Database()
    app = QApplication(sys.argv)
    apply_theme(app)
    window = LoginWindow(db)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
