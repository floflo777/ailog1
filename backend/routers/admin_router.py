from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from database import get_db
from services.auth_service import superadmin_required
from services.user_service import create_user, list_users, delete_user, get_user_by_username

router = APIRouter()

class CreateAdminRequest(BaseModel):
    username: str
    password: str
    role: Optional[str] = "admin"

@router.post("/create-admin")
def create_admin(req: CreateAdminRequest, 
                 db: Session = Depends(get_db), 
                 _=Depends(superadmin_required)):
    """
    Crée un nouveau compte (admin ou superadmin) 
    => seul un superadmin peut faire ça.
    """
    try:
        user = create_user(db, req.username, req.password, role=req.role or "admin")
        return {"status": "success", "user_id": user.id, "role": user.role}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/users")
def get_all_users(db: Session = Depends(get_db), 
                  _=Depends(superadmin_required)):
    """
    Liste tous les utilisateurs (admin + superadmin).
    """
    users = list_users(db)
    return [
        {
            "id": u.id,
            "username": u.username,
            "role": u.role
        }
        for u in users
    ]

@router.delete("/users/{user_id}")
def remove_user(user_id: int, 
                db: Session = Depends(get_db), 
                _=Depends(superadmin_required)):
    """
    Supprime un user par ID (superadmin only).
    """
    delete_user(db, user_id)
    return {"status": "deleted", "user_id": user_id}
