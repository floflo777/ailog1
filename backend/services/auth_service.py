import os
import jwt
import logging
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from services.user_service import get_user_by_username, verify_password, list_users
from models import User

logger = logging.getLogger(__name__)

JWT_SECRET = os.getenv("JWT_SECRET", "changeMe")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

class LoginData(BaseModel):
    username: str
    password: str

def create_jwt_token(username: str, role: str, expire_hours: int = 2) -> str:
    """
    Génère un JWT portant un champ "sub" = username et "role" = user.role
    Expire dans 'expire_hours' heures.
    """
    payload = {
        "sub": username,
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=expire_hours)
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    return token

def decode_jwt(token: str) -> dict:
    """
    Retourne un dictionnaire contenant "sub" (username) et "role".
    Ex: {"sub": "admin", "role": "superadmin"} ou {} si invalide.
    """
    try:
        decoded = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return decoded
    except jwt.ExpiredSignatureError:
        logger.warning("Token expiré")
        return {}
    except jwt.DecodeError:
        logger.warning("Token invalide (DecodeError)")
        return {}

def login_user(db: Session, data: LoginData) -> str:
    """
    Vérifie username/password, renvoie un token JWT si OK.
    """
    user = get_user_by_username(db, data.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    if not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    token = create_jwt_token(user.username, user.role, expire_hours=2)
    return token

async def get_current_role(token: str = Depends(oauth2_scheme)) -> str:
    """
    Dépendance FastAPI : on récupère le token, on renvoie le rôle du user.
    """
    decoded = decode_jwt(token)
    role = decoded.get("role", "")
    if not role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )
    return role

async def admin_required(role: str = Depends(get_current_role)):
    """
    Vérifie que le rôle est "admin" ou "superadmin".
    """
    if role not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized (needs admin or superadmin role)"
        )
    return True

async def superadmin_required(role: str = Depends(get_current_role)):
    """
    Vérifie que le rôle est "superadmin" seulement.
    """
    if role != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized (needs superadmin role)"
        )
    return True

async def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    """
    Retourne l'objet User correspondant au token JWT, ou 401 si invalide.
    """
    decoded = decode_jwt(token)
    username = decoded.get("sub", "")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: no username"
        )
    user = get_user_by_username(db, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    return user
