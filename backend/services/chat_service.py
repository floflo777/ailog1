import logging
from typing import Tuple, List
from qdrant_client import QdrantClient
from openai import OpenAI

from core.config import get_qdrant_client, get_openai_client, settings
from services.settings_service import get_current_settings

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_MESSAGE = """Tu es un directeur des ressources humaines qualifiés. pour 
chaque prompt parlant de CV donne une note globale au CV dès le début de ta réponse."""

def get_chat_service():
    """
    FastAPI va instancier le ChatService via Depends().
    """
    return ChatService(
        qdrant_client=get_qdrant_client(),
        openai_client=get_openai_client()
    )

class ChatService:
    def __init__(self, qdrant_client: QdrantClient, openai_client: OpenAI):
        self.qdrant = qdrant_client
        self.openai = openai_client
        self.collection = settings.COLLECTION_NAME

    async def get_relevant_chunks(
        self,
        query: str,
        threshold: float,
        limit: int,
        collection_name: str = None
    ) -> Tuple[List[str], List[str]]:
        """
        Cherche des chunks dans Qdrant correspondant à la requête (embedding).
        Retourne (liste_textes, liste_sources).
        """
        try:
            use_collection = collection_name or self.collection
            logger.info(f"Recherche RAG pour la requête: {query}, collection='{use_collection}'")

            emb_response = self.openai.embeddings.create(
                model="text-embedding-ada-002",
                input=query
            )
            query_vector = emb_response.data[0].embedding

            results = self.qdrant.search(
                collection_name=use_collection,
                query_vector=query_vector,
                score_threshold=threshold,
                limit=limit
            )

            logger.info(f"Nb de résultats au-dessus du threshold={threshold}: {len(results)}")

            context_texts = []
            source_titles = []

            for idx, r in enumerate(results, start=1):
                payload = r.payload
                doc_type = payload.get("type", "")
                filename = payload.get("filename", "unknown")
                score = r.score

                logger.debug(f"Résultat #{idx} - type: {doc_type}, fichier: {filename}, score={score:.3f}")

                if doc_type == "qa_pair":
                    question = payload.get("question", "").strip()
                    answer = payload.get("answer", "").strip()
                    if question or answer:
                        combined_text = f"Q: {question}\nA: {answer}"
                        context_texts.append(combined_text)
                        source_titles.append(f"qa_pair from {filename} (score: {score:.3f})")

                elif doc_type in ["document_chunk", "attachment_text", "email_content"]:
                    content = payload.get("content", "").strip()
                    if content:
                        context_texts.append(content)
                        source_titles.append(f"{doc_type} from {filename} (score: {score:.3f})")

                elif doc_type == "image_description":
                    desc = payload.get("content", {})
                    if isinstance(desc, dict):
                        text_desc = desc.get("general_description", "").strip()
                        if text_desc:
                            context_texts.append(f"Image description: {text_desc}")
                            source_titles.append(f"image from {filename} (score: {score:.3f})")

                else:
                    logger.debug(f"Type inconnu ou non géré: {doc_type}")

            logger.info(f"Total de contextes retenus: {len(context_texts)}")
            return context_texts, source_titles

        except Exception as e:
            logger.error(f"Error in get_relevant_chunks: {e}", exc_info=True)
            return [], []

    async def process_chat_request(self, request_data, collection_name: str = None):
        """
        Gère la requête de chat:
          - lit les paramètres RAG (threshold, limit, temperature, top_p, presence_penalty, etc.)
          - si RAG => fait get_relevant_chunks + injection de contexte
          - sinon => prompt classique
          - appelle l'API Chat
        """
        messages = []
        source_titles = []

        try:
            current_settings = get_current_settings()

            # Paramètres pour la recherche dans Qdrant
            similarity_threshold = current_settings.similarity_threshold
            rag_limit = current_settings.rag_limit

            # Paramètres pour l'appel OpenAI
            temperature = current_settings.temperature
            model_name = current_settings.model_name
            top_p = getattr(current_settings, "top_p", 1.0)  # si pas défini, fallback
            presence_penalty = getattr(current_settings, "presence_penalty", 0.0)
            frequency_penalty = getattr(current_settings, "frequency_penalty", 0.0)
            max_tokens = getattr(current_settings, "max_tokens", 512)

            system_msg_setting = getattr(current_settings, "system_message", "") or DEFAULT_SYSTEM_MESSAGE
            use_collection = collection_name or self.collection

            logger.info(f"process_chat_request - useRAG={request_data.useRAG}, user message={request_data.message}, collection='{use_collection}'")
            logger.info(
                f"Paramètres RAG => threshold={similarity_threshold}, limit={rag_limit}, "
                f"temperature={temperature}, model={model_name}, top_p={top_p}, "
                f"presence_penalty={presence_penalty}, frequency_penalty={frequency_penalty}, "
                f"max_tokens={max_tokens}"
            )

            if request_data.useRAG:
                context_texts, source_titles = await self.get_relevant_chunks(
                    request_data.message,
                    threshold=similarity_threshold,
                    limit=rag_limit,
                    collection_name=use_collection
                )

                if not request_data.history:
                    full_system_msg = (
                        f"{system_msg_setting}\n\n"
                        f"Context information:\n{' '.join(context_texts)}"
                    )
                    messages.append({"role": "system", "content": full_system_msg})
                else:
                    for msg in request_data.history:
                        messages.append({"role": msg.role, "content": msg.content})

                messages.append({"role": "user", "content": request_data.message})

            else:
                if not request_data.history:
                    messages.append({"role": "system", "content": system_msg_setting})
                else:
                    for msg in request_data.history:
                        messages.append({"role": msg.role, "content": msg.content})

                messages.append({"role": "user", "content": request_data.message})

            logger.info(f"Appel à OpenAI Chat complet: model={model_name}")
            resp = self.openai.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=temperature,
                top_p=top_p,
                presence_penalty=presence_penalty,
                frequency_penalty=frequency_penalty,
                max_tokens=max_tokens
            )

            answer = resp.choices[0].message.content
            logger.info("Réponse renvoyée par OpenAI.")

            return answer, source_titles

        except Exception as e:
            logger.error(f"Erreur lors du process_chat_request: {e}", exc_info=True)
            return "Désolé, une erreur s'est produite.", []
