# backend/init_superadmin.py

from database import init_db, SessionLocal
from models import User
from services.user_service import hash_password

def main():
    init_db()

    db = SessionLocal()
    try:
        existing_sa = db.query(User).filter(User.role == "superadmin").first()
        if existing_sa:
            print(f"Un superadmin existe déjà: {existing_sa.username}")
            return

        username = "superadmin"
        plain_password = "password"

        user = User(
            username=username,
            password_hash=hash_password(plain_password),
            role="superadmin"
        )
        db.add(user)
        db.commit()
        print(f"Superadmin créé : {username} / {plain_password}")

    finally:
        db.close()

if __name__ == "__main__":
    main()
