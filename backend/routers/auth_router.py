from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from starlette import status

from services.auth_service import LoginData, login_user
from database import get_db

router = APIRouter()

@router.post("/login")
def login(data: LoginData, db: Session = Depends(get_db)):
    """
    Vérifie username/password, renvoie {"access_token": "<JWT>", "token_type": "bearer"}.
    """
    token = login_user(db, data)
    return {
        "access_token": token,
        "token_type": "bearer"
    }
