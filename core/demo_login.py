# core/demo_login.py

from core.database import Database
from core.services.auth_service import AuthService


def main():
    db = Database()
    auth = AuthService(db)

    print("=== Demo Login ===")
    username = input("Username: ").strip()
    password = input("Password: ").strip()

    user = auth.login(username, password)

    if user is None:
        print("\nLogin failed: invalid username or password.")
        return

    print("\nLogin successful!")
    print(f"ID: {user.id}")
    print(f"Name: {user.name}")
    print(f"Username: {user.username}")
    print(f"Role: {user.role}")
    print(f"is_manager: {user.is_manager}")
    print(f"is_employee: {user.is_employee}")


if __name__ == "__main__":
    main()
