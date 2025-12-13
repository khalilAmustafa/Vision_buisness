from core.database import Database
from core.models.user import User
from core.services.user_service import UserService


def main():
    db = Database()
    user_service = UserService(db)

    username = input("Manager username: ").strip()
    password = input("Manager password: ").strip()

    manager = User(
        id="0000",              # ✅ id (NOT user_id)
        name="Manager",
        username=username,
        password_hash=password,
        role="manager",
    )

    # if your service has add_user, use that. otherwise create_user.
    if hasattr(user_service, "add_user"):
        user_service.add_user(manager)
    else:
        user_service.create_user(manager)

    print("\nManager created successfully!")
    print("ID:", manager.id)
    print("Username:", manager.username)
    print("Role:", manager.role)


if __name__ == "__main__":
    main()
