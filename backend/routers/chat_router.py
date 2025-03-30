from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session

from services.chat_service import get_chat_service
from services.auth_service import admin_required, get_current_user
from database import get_db
from models import Collection, User

router = APIRouter()

class ChatMessage(BaseModel):
    role: str
    content: str
    context: Optional[List[str]] = None

class ChatRequest(BaseModel):
    message: str
    useRAG: bool
    history: List[ChatMessage]

@router.post("")
async def chat_endpoint(
    request: ChatRequest,
    collection_id: int = Query(...),
    chat_service=Depends(get_chat_service),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(admin_required)
):
    """
    Endpoint pour le chat RAG (admin only).
    L'utilisateur spécifie la collection sur laquelle faire la recherche.
    """
    coll = db.query(Collection).get(collection_id)
    if not coll:
        raise HTTPException(status_code=404, detail="Collection inconnue")
    if coll not in current_user.collections:
        raise HTTPException(status_code=403, detail="Accès refusé à cette collection")

    try:
        response, source_titles = await chat_service.process_chat_request(
            request_data=request,
            collection_name=coll.name
        )
        return {"response": response, "context": source_titles}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
