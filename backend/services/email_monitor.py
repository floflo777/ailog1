import os
import re
import imaplib
import email
import logging
import asyncio
from datetime import datetime, timezone
from typing import List, Tuple

from qdrant_client import QdrantClient
from openai import OpenAI

from services.settings_service import get_current_settings

logger = logging.getLogger(__name__)

def tokenize_text(text: str, max_length: int, overlap: int = 0) -> List[str]:
    """
    Découpe 'text' en chunks de taille 'max_length', avec un chevauchement 'overlap' (en tokens).
    Exemple : si max_length=500 et overlap=50,
    on avance de 450 tokens à chaque chunk, chevauchant 50 tokens du chunk précédent.
    """
    tokens = text.split()
    chunks = []
    i = 0
    while i < len(tokens):
        end = i + max_length
        chunk = " ".join(tokens[i:end])
        chunks.append(chunk)
        stride = max_length - overlap if (max_length - overlap) > 0 else max_length
        i += stride
    return chunks

def anonymize_text(text: str, expressions_list: List[str]) -> str:
    """
    Exemple d'anonymisation simple : remplace chaque expression par 'XXX'.
    """
    for expr in expressions_list:
        pattern = re.compile(re.escape(expr), re.IGNORECASE)
        text = pattern.sub("XXX", text)
    return text

class EmailMonitor:
    def __init__(
        self,
        email_address: str,
        email_password: str,
        imap_server: str,
        check_interval: int,
        qdrant_client: QdrantClient,
        openai_client: OpenAI
    ):
        self.email_address = email_address
        self.email_password = email_password
        self.imap_server = imap_server
        self.check_interval = check_interval
        self.last_processed_date = datetime.now(timezone.utc)
        self.qdrant_client = qdrant_client
        self.openai_client = openai_client

        logger.info(f"EmailMonitor initialized: {email_address} / {imap_server}")

    async def connect_to_email(self) -> imaplib.IMAP4_SSL:
        """
        Etablit la connexion IMAP (SSL) et se logge.
        """
        try:
            logger.info(f"Attempting to connect to {self.imap_server}")
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.email_address, self.email_password)
            logger.info("Email login successful")
            return mail
        except imaplib.IMAP4.error as e:
            logger.error(f"IMAP Error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Connection error: {str(e)}")
            raise

    async def get_new_emails(self, folder: str = "INBOX") -> List[Tuple[str, List[str]]]:
        """
        Récupère les e-mails (depuis last_processed_date), 
        et retourne une liste de tuples (body, [paths_attachments]).
        """
        try:
            mail = await self.connect_to_email()
            mail.select(folder)
            date_str = self.last_processed_date.strftime("%d-%b-%Y")
            search_criterion = f'(SINCE {date_str})'
            
            _, messages = mail.search(None, search_criterion)
            email_data = []
            
            for num in messages[0].split():
                try:
                    _, msg_data = mail.fetch(num, "(RFC822)")
                    email_body = msg_data[0][1]
                    message = email.message_from_bytes(email_body)
                    
                    email_date = email.utils.parsedate_to_datetime(message["Date"])
                    if email_date.tzinfo is None:
                        email_date = email_date.replace(tzinfo=timezone.utc)
                    else:
                        email_date = email_date.astimezone(timezone.utc)

                    if email_date <= self.last_processed_date:
                        continue

                    body = ""
                    attachments = []

                    if message.is_multipart():
                        for part in message.walk():
                            if part.get_content_type() == "text/plain":
                                try:
                                    body += part.get_payload(decode=True).decode()
                                except Exception as e:
                                    logger.error(f"Error decoding body: {str(e)}")
                            elif part.get_content_maintype() != 'multipart':
                                raw_filename = part.get_filename()
                                if raw_filename:
                                    from email.header import decode_header
                                    decoded_parts = decode_header(raw_filename)
                                    filename = "".join(
                                        part_c.decode("utf-8") if isinstance(part_c, bytes) else part_c
                                        for part_c, _ in decoded_parts
                                    )
                                    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
                                    filepath = f"temp_{filename}"
                                    with open(filepath, "wb") as f:
                                        f.write(part.get_payload(decode=True))
                                    attachments.append(filepath)
                                    logger.info(f"Saved attachment: {filepath}")
                    else:
                        try:
                            body = message.get_payload(decode=True).decode()
                        except Exception as e:
                            logger.error(f"Error decoding single-part message: {str(e)}")
                    
                    email_data.append((body, attachments))
                except Exception as e:
                    logger.error(f"Error processing email {num}: {str(e)}")
            
            mail.close()
            mail.logout()

            self.last_processed_date = datetime.now(timezone.utc)
            logger.info(f"Found {len(email_data)} new emails.")
            return email_data
        
        except Exception as e:
            logger.error(f"get_new_emails error: {str(e)}")
            raise

    async def process_and_embed_email_content(self, content: str, filename: str):
        """
        Découpe le corps d'email en chunks (selon chunk_size/overlap),
        anonymise (selon expressions),
        crée l'embedding (modèle text-embedding-ada-002),
        et upsert dans Qdrant.
        """
        try:
            current_settings = get_current_settings()

            chunk_size = current_settings.chunk_size or 500
            chunk_overlap = current_settings.chunk_overlap or 0
            model_name = "text-embedding-ada-002"
            exprs = current_settings.expressions or ""
            expressions_list = [e.strip() for e in exprs.split(";") if e.strip()]
            content = anonymize_text(content, expressions_list)
            chunks = tokenize_text(content, max_length=chunk_size, overlap=chunk_overlap)
            collection = os.getenv("COLLECTION_NAME", "customgpt_embeddings")
            current_count = self.qdrant_client.count(collection_name=collection).count

            points = []
            for idx, chunk in enumerate(chunks):
                if chunk.strip():
                    try:
                        emb_resp = self.openai_client.embeddings.create(
                            model=model_name,
                            input=chunk
                        )
                        emb_vec = emb_resp.data[0].embedding
                        points.append({
                            "id": current_count + idx,
                            "vector": emb_vec,
                            "payload": {
                                "type": "email_content",
                                "content": chunk,
                                "chunk_index": idx,
                                "filename": filename,
                                "source": "email"
                            }
                        })
                    except Exception as e:
                        logger.error(f"Error embedding chunk {idx}: {e}")

            if points:
                BATCH_SIZE = 50
                for i in range(0, len(points), BATCH_SIZE):
                    batch = points[i:i + BATCH_SIZE]
                    self.qdrant_client.upsert(collection_name=collection, points=batch)
                    logger.info(f"Indexed {len(batch)} email content chunks.")

        except Exception as e:
            logger.error(f"Error in process_and_embed_email_content: {e}")

    async def start_monitoring(self):
        """
        Boucle asynchrone qui check les nouveaux mails à intervalle régulier
        et indexe le contenu + pièces jointes si besoin.
        """
        logger.info(f"Starting email monitoring for {self.email_address}")
        
        while True:
            try:
                email_data = await self.get_new_emails()
                if email_data:
                    logger.info(f"Processing {len(email_data)} new emails.")
                    for body, attachments in email_data:
                        if body:
                            await self.process_and_embed_email_content(
                                body,
                                f"email_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                            )
                        for attach in attachments:
                            logger.info(f"Attachment found: {attach}")
                            try:
                                pass
                            finally:
                                import os
                                os.remove(attach)
            except Exception as e:
                logger.error(f"Error in email loop: {e}", exc_info=True)
                await asyncio.sleep(15)
            
            await asyncio.sleep(self.check_interval)
