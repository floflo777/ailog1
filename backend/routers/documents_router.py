from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Query
from typing import List
from sqlalchemy.orm import Session

from services.document_service import get_document_service
from services.auth_service import admin_required, get_current_user
from database import get_db
from models import Collection, User

router = APIRouter()

@router.post("/process-document")
async def process_document_endpoint(
    file: UploadFile = File(...),
    collection_id: int = Form(...),
    doc_service=Depends(get_document_service),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(admin_required)
):
    """
    Analyse un document, anonymise, génère Q&A, etc. (admin only).
    On précise la collection via 'collection_id'.
    """
    coll = db.query(Collection).get(collection_id)
    if not coll:
        raise HTTPException(status_code=404, detail="Collection inconnue")
    
    if coll not in current_user.collections:
        raise HTTPException(status_code=403, detail="Accès refusé à cette collection")

    result = await doc_service.process_document(file, collection_name=coll.name)
    return result

@router.post("/save-to-qdrant")
async def save_to_qdrant_endpoint(
    file: UploadFile = File(...),
    document_analysis: str = Form(...),
    collection_id: int = Form(...),
    doc_service=Depends(get_document_service),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(admin_required)
):
    """
    Enregistre l'analyse du document dans Qdrant (admin only).
    """
    coll = db.query(Collection).get(collection_id)
    if not coll:
        raise HTTPException(status_code=404, detail="Collection inconnue")
    if coll not in current_user.collections:
        raise HTTPException(status_code=403, detail="Accès refusé à cette collection")

    result = await doc_service.save_to_qdrant(file, document_analysis, collection_name=coll.name)
    return result

@router.post("/process-directory")
async def process_directory_endpoint(
    files: List[UploadFile] = File(...),
    collection_id: int = Form(...),
    doc_service=Depends(get_document_service),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(admin_required)
):
    """
    Traite plusieurs documents d'un coup (admin only).
    """
    coll = db.query(Collection).get(collection_id)
    if not coll:
        raise HTTPException(status_code=404, detail="Collection inconnue")
    if coll not in current_user.collections:
        raise HTTPException(status_code=403, detail="Accès refusé à cette collection")

    result = await doc_service.process_directory(files, collection_name=coll.name)
    return result
