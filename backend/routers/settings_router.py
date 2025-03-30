from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional

from sqlalchemy.orm import Session
from database import get_db
from services.auth_service import superadmin_required
from services.settings_service import get_global_settings, update_global_settings

router = APIRouter()

class SettingsUpdateRequest(BaseModel):
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None
    temperature: Optional[float] = None
    similarity_threshold: Optional[float] = None
    rag_limit: Optional[int] = None
    model_name: Optional[str] = None

    top_p: Optional[float] = None
    presence_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None
    max_tokens: Optional[int] = None
    system_message: Optional[str] = None

    expressions: Optional[str] = None


@router.get("")
def get_settings(db: Session = Depends(get_db), 
                 _=Depends(superadmin_required)):
    """
    Récupère les settings RAG (superadmin only).
    """
    s = get_global_settings(db)
    return {
        "chunk_size": s.chunk_size,
        "chunk_overlap": s.chunk_overlap,
        "temperature": s.temperature,
        "similarity_threshold": s.similarity_threshold,
        "rag_limit": s.rag_limit,
        "model_name": s.model_name,

        "top_p": s.top_p,
        "presence_penalty": s.presence_penalty,
        "frequency_penalty": s.frequency_penalty,
        "max_tokens": s.max_tokens,
        "system_message": s.system_message,

        "expressions": s.expressions
    }


@router.post("")
def update_settings(payload: SettingsUpdateRequest, 
                    db: Session = Depends(get_db), 
                    _=Depends(superadmin_required)):
    """
    Met à jour tout ou partie des settings RAG (superadmin only).
    """
    data = payload.dict(exclude_unset=True)
    s = update_global_settings(db, data)
    return {
        "chunk_size": s.chunk_size,
        "chunk_overlap": s.chunk_overlap,
        "temperature": s.temperature,
        "similarity_threshold": s.similarity_threshold,
        "rag_limit": s.rag_limit,
        "model_name": s.model_name,

        "top_p": s.top_p,
        "presence_penalty": s.presence_penalty,
        "frequency_penalty": s.frequency_penalty,
        "max_tokens": s.max_tokens,
        "system_message": s.system_message,

        "expressions": s.expressions
    }
