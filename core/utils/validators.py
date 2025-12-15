class Validators:
    @staticmethod
    def validate_username(username):
        return len(username) > 3
