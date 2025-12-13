class User:
    def __init__(self, id, name, username, password_hash, role):
        self.id = id
        self.name = name
        self.username = username
        self.password_hash = password_hash
        self.role = role
