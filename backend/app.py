import os
import asyncio
import logging

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from core.config import settings, get_qdrant_client, get_openai_client

from routers.chat_router import router as chat_router
from routers.documents_router import router as documents_router
from routers.settings_router import router as settings_router
from routers.auth_router import router as auth_router
from routers.admin_router import router as admin_router
from routers.collections_router import router as collections_router  # gestion collections

from services.email_monitor import EmailMonitor

from database import init_db

import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from fastapi import HTTPException

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Démarre (puis arrête) le monitoring d’emails
    au lancement/arrêt de l'application FastAPI.
    """
    email_address = settings.EMAIL_ADDRESS
    email_password = settings.EMAIL_PASSWORD

    if email_address and email_password:
        monitor = EmailMonitor(
            email_address=email_address,
            email_password=email_password,
            imap_server=settings.IMAP_SERVER,
            check_interval=settings.EMAIL_CHECK_INTERVAL,
            qdrant_client=get_qdrant_client(),
            openai_client=get_openai_client()
        )
        try:
            mail = await monitor.connect_to_email()
            mail.logout()
            logger.info("Email connection test successful.")
            app.state.email_monitor_task = asyncio.create_task(monitor.start_monitoring())
            logger.info("Started email monitoring.")
        except Exception as e:
            logger.error(f"Email connection test failed: {e}")
    else:
        logger.info("No email credentials provided. Skipping email monitoring.")

    yield

    if hasattr(app.state, "email_monitor_task"):
        app.state.email_monitor_task.cancel()
        try:
            await app.state.email_monitor_task
        except asyncio.CancelledError:
            pass
        logger.info("Email monitoring stopped.")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600
)

app.include_router(chat_router, prefix="/chat", tags=["Chat"])
app.include_router(documents_router, prefix="/documents", tags=["Documents"])
app.include_router(settings_router, prefix="/settings", tags=["Settings"])
app.include_router(auth_router, tags=["Auth"])
app.include_router(admin_router, prefix="/admin", tags=["Admin"])
app.include_router(collections_router, prefix="/admin", tags=["Admin"])

@app.options("/{full_path:path}")
async def options_route(full_path: str):
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "http://localhost:5173",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
            "Access-Control-Allow-Credentials": "true",
        }
    )

@app.get("/test-email-connection")
async def test_email_connection():
    """
    Simple endpoint pour tester la connexion IMAP (Gmail / OVH, etc.).
    """
    import imaplib
    try:
        mail = imaplib.IMAP4_SSL(settings.IMAP_SERVER)
        mail.login(settings.EMAIL_ADDRESS, settings.EMAIL_PASSWORD)
        mail.logout()
        return {"status": "success", "message": "Connection test successful"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.on_event("startup")
async def provide_clients():
    init_db()
    logger.info(">>> init_db() called successfully!")
    app.state.qdrant_client = get_qdrant_client()
    app.state.openai_client = get_openai_client()
