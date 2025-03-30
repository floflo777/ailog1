from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List

from database import get_db
from services.auth_service import superadmin_required, get_current_user
from models import Collection, User
from core.config import get_qdrant_client
from qdrant_client import QdrantClient

router = APIRouter()

@router.get("/qdrant-collections")
def list_qdrant_collections(
    db: Session = Depends(get_db),
    qdrant: QdrantClient = Depends(get_qdrant_client),
    _=Depends(superadmin_required)
):
    """
    Renvoie la liste des collections existantes dans Qdrant
    (côté moteur vectoriel).
    """
    try:
        response = qdrant.get_collections()
        colls = [c.name for c in response.collections]
        return {"status": "success", "collections": colls}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la récupération des collections Qdrant: {e}"
        )

@router.get("/collections")
def list_db_collections(
    db: Session = Depends(get_db),
    _=Depends(superadmin_required)
):
    """
    Renvoie toutes les collections présentes dans la table `Collection` (DB).
    """
    all_coll = db.query(Collection).all()
    data = [{"id": c.id, "name": c.name, "description": c.description} for c in all_coll]
    return {
        "status": "success",
        "collections": data
    }

@router.get("/users/{user_id}/collections")
def get_user_collections(
    user_id: int,
    db: Session = Depends(get_db),
    _=Depends(superadmin_required)
):
    """
    Renvoie la liste des collections (id, name) auxquelles un user a accès.
    """
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(404, "User not found.")

    return [
        {"id": c.id, "name": c.name}
        for c in user.collections
    ]

@router.post("/add-collection")
def add_collection_to_db(
    name: str,
    db: Session = Depends(get_db),
    _=Depends(superadmin_required)
):
    """
    Ajoute un enregistrement dans la table `Collection`
    avec 'name' = nom de la collection Qdrant.
    """
    existing = db.query(Collection).filter_by(name=name).first()
    if existing:
        raise HTTPException(400, f"La collection '{name}' existe déjà dans la DB.")
    new_coll = Collection(name=name)
    db.add(new_coll)
    db.commit()
    db.refresh(new_coll)
    return {
        "status": "success",
        "collection_id": new_coll.id,
        "name": new_coll.name
    }

@router.post("/assign-collection")
def assign_collection_to_user(
    user_id: int,
    collection_id: int,
    db: Session = Depends(get_db),
    _=Depends(superadmin_required)
):
    """
    Donne l'accès d'une collection (DB) à un utilisateur.
    """
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(404, "User not found.")
    coll = db.query(Collection).get(collection_id)
    if not coll:
        raise HTTPException(404, "Collection not found in DB.")

    if coll not in user.collections:
        user.collections.append(coll)
        db.commit()

    return {
        "status": "success",
        "message": f"Collection '{coll.name}' assignée à l'utilisateur '{user.username}'."
    }

@router.delete("/unassign-collection")
def unassign_collection_from_user(
    user_id: int,
    collection_id: int,
    db: Session = Depends(get_db),
    _=Depends(superadmin_required)
):
    """
    Retire la collection (DB) d'un utilisateur.
    """
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(404, "User not found.")
    coll = db.query(Collection).get(collection_id)
    if not coll:
        raise HTTPException(404, "Collection not found in DB.")

    if coll in user.collections:
        user.collections.remove(coll)
        db.commit()

    return {
        "status": "success",
        "message": f"Collection '{coll.name}' retirée de l'utilisateur '{user.username}'."
    }

@router.get("/my-collections")
def get_my_collections(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Renvoie la liste des collections (id, name) auxquelles l'utilisateur courant a accès.
    Nécessite le rôle 'admin' ou 'superadmin'.
    """
    if current_user.role not in ["admin", "superadmin"]:
        raise HTTPException(403, "Not authorized")

    data = [{"id": c.id, "name": c.name} for c in current_user.collections]
    return {
        "status": "success",
        "collections": data
    }
