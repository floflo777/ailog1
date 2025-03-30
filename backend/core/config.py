import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from openai import OpenAI

load_dotenv()

class Settings:
    # Qdrant
    QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
    COLLECTION_NAME = os.getenv("COLLECTION_NAME", "customgpt_embeddings")

    # OpenAI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

    # Email
    EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
    IMAP_SERVER = os.getenv("IMAP_SERVER")
    EMAIL_CHECK_INTERVAL = int(os.getenv("EMAIL_CHECK_INTERVAL", "60"))

    # Autre
    COUNTRIES = os.getenv("COUNTRIES", "")

    # Sécurité
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "secret")
    JWT_SECRET = os.getenv("JWT_SECRET", "changeMeToRandom")

settings = Settings()

_qdrant_client = None
_openai_client = None

def get_qdrant_client() -> QdrantClient:
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY
        )
    return _qdrant_client

def get_openai_client() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        if not settings.OPENAI_API_KEY:
            raise ValueError("Missing OPENAI_API_KEY in environment.")
        _openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client
