import bcrypt
from sqlalchemy.orm import Session
from models import User

def hash_password(plain_pwd: str) -> str:
    return bcrypt.hashpw(plain_pwd.encode(), bcrypt.gensalt()).decode()

def verify_password(plain_pwd: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain_pwd.encode(), hashed.encode())

def create_user(db: Session, username: str, password: str, role: str = "admin"):
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        raise ValueError("Username already exists")

    user = User(
        username=username,
        password_hash=hash_password(password),
        role=role
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def list_users(db: Session):
    return db.query(User).all()

def delete_user(db: Session, user_id: int):
    user = db.query(User).get(user_id)
    if user:
        db.delete(user)
        db.commit()
