from PyQt5.QtWidgets import (
    QApplication, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QTableWidget, QTableWidgetItem,
    QMessageBox, QDialog
)
from manager_backend import (
    add_employee, get_all_employees, delete_employee, get_employee_data
)


class ManagerUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Manager Dashboard - Vision")
        self.setGeometry(200, 200, 700, 500)

        layout = QVBoxLayout()
        self.tabs = QTabWidget()

        # Tab 1
        self.tab_register = QWidget()
        self.init_register_tab()
        self.tabs.addTab(self.tab_register, "Employee Registration")

        # Tab 2
        self.tab_data = QWidget()
        self.init_data_tab()
        self.tabs.addTab(self.tab_data, "Employee Data")

        layout.addWidget(self.tabs)
        self.setLayout(layout)

    # -----------------------------------
    # Employee Registration Tab
    # -----------------------------------
    def init_register_tab(self):
        layout = QVBoxLayout()

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Name")

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)

        add_btn = QPushButton("Add Employee")
        add_btn.clicked.connect(self.add_employee)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["#", "ID (hidden)", "Name", "Username", "Role"])
        self.table.setColumnHidden(1, True)

        del_btn = QPushButton("Delete Selected Employee")
        del_btn.clicked.connect(self.delete_selected)

        layout.addWidget(QLabel("Add New Employee"))
        layout.addWidget(self.name_input)
        layout.addWidget(self.username_input)
        layout.addWidget(self.password_input)
        layout.addWidget(add_btn)
        layout.addWidget(QLabel("Employee List"))
        layout.addWidget(self.table)
        layout.addWidget(del_btn)

        self.tab_register.setLayout(layout)
        self.load_table()

    # -----------------------------------
    # Employee Data Tab
    # -----------------------------------
    def init_data_tab(self):
        layout = QVBoxLayout()

        self.data_table = QTableWidget()
        self.data_table.setColumnCount(5)
        self.data_table.setHorizontalHeaderLabels(["#", "ID (hidden)", "Name", "Username", "Role"])
        self.data_table.setColumnHidden(1, True)

        self.load_data_table()

        view_btn = QPushButton("View / Edit Employee Data")
        view_btn.clicked.connect(self.view_employee_data)

        layout.addWidget(QLabel("Employees"))
        layout.addWidget(self.data_table)
        layout.addWidget(view_btn)

        self.tab_data.setLayout(layout)

    # -----------------------------------
    # Add Employee
    # -----------------------------------
    def add_employee(self):
        name = self.name_input.text()
        username = self.username_input.text()
        password = self.password_input.text()

        if not (name and username and password):
            QMessageBox.warning(self, "Error", "All fields are required")
            return

        if add_employee(name, username, password):
            QMessageBox.information(self, "Success", "Employee added!")
            self.name_input.clear()
            self.username_input.clear()
            self.password_input.clear()
            self.load_table()
            self.load_data_table()
        else:
            QMessageBox.warning(self, "Error", "Username already exists")

    # -----------------------------------
    # Load Table (with separated blocks)
    # -----------------------------------
    def load_table(self):
        data = get_all_employees()

        self.table.setRowCount(len(data) * 2)
        row_index = 0

        for emp in data:
            self.table.setItem(row_index, 0, QTableWidgetItem(str((row_index // 2) + 1)))
            self.table.setItem(row_index, 1, QTableWidgetItem(str(emp[0])))
            self.table.setItem(row_index, 2, QTableWidgetItem(emp[1]))
            self.table.setItem(row_index, 3, QTableWidgetItem(emp[2]))
            self.table.setItem(row_index, 4, QTableWidgetItem(emp[3]))

            row_index += 2

        # make blank rows small
        for r in range(1, self.table.rowCount(), 2):
            self.table.setRowHeight(r, 10)

    def load_data_table(self):
        data = get_all_employees()

        self.data_table.setRowCount(len(data) * 2)
        row_index = 0

        for emp in data:
            self.data_table.setItem(row_index, 0, QTableWidgetItem(str((row_index // 2) + 1)))
            self.data_table.setItem(row_index, 1, QTableWidgetItem(str(emp[0])))
            self.data_table.setItem(row_index, 2, QTableWidgetItem(emp[1]))
            self.data_table.setItem(row_index, 3, QTableWidgetItem(emp[2]))
            self.data_table.setItem(row_index, 4, QTableWidgetItem(emp[3]))

            row_index += 2

        for r in range(1, self.data_table.rowCount(), 2):
            self.data_table.setRowHeight(r, 10)

    # -----------------------------------
    # Delete Employee
    # -----------------------------------
    def delete_selected(self):
        selected = self.table.currentRow()

        # user clicked on an empty separator row
        if selected % 2 == 1:
            QMessageBox.warning(self, "Error", "Select an employee row, not the blank row")
            return

        if selected < 0:
            QMessageBox.warning(self, "Error", "Select a row first")
            return

        real_id = int(self.table.item(selected, 1).text())

        if delete_employee(real_id):
            QMessageBox.information(self, "Deleted", "Employee removed")
            self.load_table()
            self.load_data_table()
        else:
            QMessageBox.warning(self, "Error", "Failed to delete employee")

    # -----------------------------------
    # View / Edit Employee Data
    # -----------------------------------
    def view_employee_data(self):
        selected = self.data_table.currentRow()

        if selected % 2 == 1:
            QMessageBox.warning(self, "Error", "Select an employee row, not the blank row")
            return

        if selected < 0:
            QMessageBox.warning(self, "Error", "Select a row first")
            return

        user_id = int(self.data_table.item(selected, 1).text())
        data = get_employee_data(user_id)

        if not data:
            QMessageBox.warning(self, "Error", "Employee not found")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("View Employee")
        layout = QVBoxLayout()

        info_text = (
            f"Name: {data['user_info'][1]}\n"
            f"Username: {data['user_info'][2]}\n"
            f"Role: {data['user_info'][3]}\n"
            f"Shift Start: {data['shift'][0]}\n"
            f"Shift End: {data['shift'][1]}"
        )

        info_label = QLabel(info_text)
        info_label.setStyleSheet("background-color: #f0f0f0; padding: 10px; border: 1px solid #ccc;")
        info_label.setWordWrap(True)

        edit_btn = QPushButton("Edit")
        save_btn = QPushButton("Save Changes")
        save_btn.setEnabled(False)

        layout.addWidget(info_label)
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

        def enable_edit():
            layout.removeWidget(info_label)
            info_label.deleteLater()

            name_edit = QLineEdit(data['user_info'][1])
            username_edit = QLineEdit(data['user_info'][2])
            password_edit = QLineEdit()
            password_edit.setPlaceholderText("New password (optional)")
            password_edit.setEchoMode(QLineEdit.Password)
            shift_start = QLineEdit(data['shift'][0])
            shift_end = QLineEdit(data['shift'][1])

            layout.insertWidget(0, QLabel("Name"))
            layout.insertWidget(1, name_edit)
            layout.insertWidget(2, QLabel("Username"))
            layout.insertWidget(3, username_edit)
            layout.insertWidget(4, QLabel("New Password"))
            layout.insertWidget(5, password_edit)
            layout.insertWidget(6, QLabel("Shift Start"))
            layout.insertWidget(7, shift_start)
            layout.insertWidget(8, QLabel("Shift End"))
            layout.insertWidget(9, shift_end)

            save_btn.setEnabled(True)
            edit_btn.setEnabled(False)

            def save_changes():
                new_name = name_edit.text()
                new_username = username_edit.text()
                new_password = password_edit.text() or None
                new_start = shift_start.text()
                new_end = shift_end.text()

                from manager_backend import update_employee_basic, update_employee_shift

                ok1 = update_employee_basic(user_id, new_name, new_username, new_password)
                ok2 = update_employee_shift(user_id, new_start, new_end)

                if ok1 and ok2:
                    QMessageBox.information(dialog, "Success", "Changes saved!")
                    self.load_data_table()
                    self.load_table()
                    dialog.close()
                else:
                    QMessageBox.warning(dialog, "Error", "Failed to save changes")

            save_btn.clicked.connect(save_changes)

        edit_btn.clicked.connect(enable_edit)

        dialog.setLayout(layout)
        dialog.exec_()


if __name__ == "__main__":
    app = QApplication([])
    window = ManagerUI()
    window.show()
    app.exec_()