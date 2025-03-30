import logging
from sqlalchemy.orm import Session
from database import SessionLocal
from models import GlobalSettings

logger = logging.getLogger(__name__)

def get_global_settings(db: Session) -> GlobalSettings:
    """
    Récupère la row unique (id=1) dans la table GlobalSettings.
    La crée avec des valeurs par défaut si elle n'existe pas encore.
    """
    settings = db.query(GlobalSettings).filter_by(id=1).first()
    if not settings:
        settings = GlobalSettings(id=1)
        db.add(settings)
        db.commit()
        db.refresh(settings)
        logger.info("Created default GlobalSettings with id=1.")
    return settings

def update_global_settings(db: Session, data: dict) -> GlobalSettings:
    """
    Met à jour les champs de GlobalSettings(id=1) avec les valeurs passées.
    data peut ressembler à : {"chunk_size": 600, "temperature": 0.5, ...}
    """
    settings = get_global_settings(db)
    for k, v in data.items():
        if hasattr(settings, k):
            setattr(settings, k, v)
    db.commit()
    db.refresh(settings)
    return settings

def get_current_settings():
    """
    Compatibilité pour le code existant (chat_service, document_service)
    qui appelle get_current_settings() sans session DB.

    On ouvre une session "locale", on lit (ou crée) GlobalSettings(id=1),
    et on renvoie l'objet.
    """
    db = SessionLocal()
    try:
        settings = get_global_settings(db)
        return settings
    finally:
        db.close()
