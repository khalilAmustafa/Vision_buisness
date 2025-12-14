class User:
    def __init__(self, id, name, username, password_hash, role):
        self.id = id
        self.name = name
        self.username = username
        self.password_hash = password_hash
        self.role = role

    @property
    def is_manager(self) -> bool:
        return self.role == "manager"

    @property
    def is_employee(self) -> bool:
        return self.role == "employee"
