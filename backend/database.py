import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def init_db():
    """
    A appeler au démarrage pour créer les tables (si elles n'existent pas encore).
    """
    Base.metadata.create_all(bind=engine)

def get_db():
    """
    Dépendance FastAPI pour obtenir une session de base de données.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
