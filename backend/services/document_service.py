import os
import json
import re
import logging
from typing import List
from fastapi import UploadFile

from qdrant_client import QdrantClient
from qdrant_client.http import models
from openai import OpenAI

from analyzers.document_analyzer import DocumentAnalyzer
from core.config import settings, get_qdrant_client, get_openai_client
from services.settings_service import get_current_settings

logger = logging.getLogger(__name__)

def get_document_service():
    """
    FastAPI => crée une instance de DocumentService
    avec les clients Qdrant + OpenAI injectés.
    """
    return DocumentService(
        qdrant_client=get_qdrant_client(),
        openai_client=get_openai_client()
    )

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
        i += (max_length - overlap) if (max_length - overlap) > 0 else max_length
    return chunks

def load_expressions():
    """
    Charge les expressions à anonymiser depuis expressions.txt
    (ex. expr1;expr2;expr3)
    """
    expr_path = os.path.join(os.path.dirname(__file__), "..", "expressions.txt")
    if not os.path.exists(expr_path):
        logger.warning(f"{expr_path} does not exist.")
        return []
    with open(expr_path, "r", encoding="utf-8") as f:
        content = f.read()
    expressions = [ex.strip() for ex in content.split(';') if ex.strip()]
    return expressions

def anonymize_text(text: str, expressions: List[str]) -> str:
    """
    Exemple d’anonymisation : remplace expressions,
    + emails, téléphones, noms propres, etc.
    """
    logger.info(f"Expressions chargées : {expressions}")
    logger.info(f"Application de l'anonymisation avec {len(expressions)} expressions")

    for expr in expressions:
        pattern = re.compile(re.escape(expr), re.IGNORECASE)
        text = pattern.sub("XXX", text)

    email_pat = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'
    text = re.sub(email_pat, '[EMAIL]', text)

    phone_patterns = [
        r'\b\+?[0-9]{1,4}[-. ]?\(?[0-9]{1,3}\)?[-. ]?[0-9]{1,4}[-. ]?[0-9]{1,4}\b',
        r'\b0[1-9]([-. ]?[0-9]{2}){4}\b',
        r'\b[0-9]{3}[-.]?[0-9]{3}[-.]?[0-9]{4}\b'
    ]
    for pat in phone_patterns:
        text = re.sub(pat, '[PHONE]', text)

    countries = settings.COUNTRIES.split(',')
    exceptions_pattern = '|'.join(r'\b' + re.escape(word) + r'\b' for word in countries if word)

    sentences = text.split('. ')
    for i, sentence in enumerate(sentences):
        words = sentence.split()
        for j, w in enumerate(words):
            if j > 0 and len(w) > 1 and w[0].isupper() and not w.isupper():
                if not re.match(exceptions_pattern, w):
                    if not all(c.isupper() for c in w):
                        words[j] = '[NAME]'
        sentences[i] = ' '.join(words)
    text = '. '.join(sentences)

    return text

class DocumentService:
    def __init__(self, qdrant_client: QdrantClient, openai_client: OpenAI):
        self.qdrant = qdrant_client
        self.openai = openai_client
        self.collection = settings.COLLECTION_NAME

    async def process_document(self, file: UploadFile, collection_name: str = None):
        """
        1) Analyse (DocumentAnalyzer)
        2) Extrait le texte
        3) Anonymise
        4) Génère Q&A
        5) Retourne le JSON
        """
        logger.info(f"Début du traitement du document: {file.filename}")
        logger.info("First pass: analyzing image patterns...")
        logger.info("Second pass: extracting content...")

        use_collection = collection_name or self.collection

        content = await file.read()
        analyzer = DocumentAnalyzer(
            qdrant_client=self.qdrant,
            openai_client=self.openai
        )
        document_analysis = analyzer.analyze_document(content, file.filename)

        text_content = ""
        for page in document_analysis["pages"]:
            for c in page["content"]:
                if c["type"] == "text":
                    text_content += c["content"] + "\n"

        expressions = load_expressions()
        if expressions:
            text_content = anonymize_text(text_content, expressions)

        logger.info("Génération des Q&A...")
        qa_pairs = await self.generate_qa_from_text(text_content)
        logger.info(f"{len(qa_pairs)} paires Q&A générées")

        document_analysis["qa_pairs"] = qa_pairs

        return document_analysis

    async def generate_qa_from_text(self, text: str):
        """
        Découpe le texte selon chunk_size et chunk_overlap (depuis settings),
        appelle OpenAI pour créer des Q&A, puis parse.
        """
        current_settings = get_current_settings()
        chunk_size = current_settings.chunk_size 
        chunk_overlap = getattr(current_settings, "chunk_overlap", 0)

        chunks = tokenize_text(text, max_length=chunk_size, overlap=chunk_overlap)
        logger.info(f"Le texte est découpé en {len(chunks)} chunk(s), size={chunk_size}, overlap={chunk_overlap}")
        temperature = current_settings.temperature
        model_name = current_settings.model_name
        top_p = getattr(current_settings, "top_p", 1.0)
        presence_penalty = getattr(current_settings, "presence_penalty", 0.0)
        frequency_penalty = getattr(current_settings, "frequency_penalty", 0.0)
        max_tokens = getattr(current_settings, "max_tokens", 512)

        all_qa = []
        for idx, chunk in enumerate(chunks, start=1):
            logger.info(f"Génération Q&A dans le chunk #{idx}")
            try:
                prompt = [
                    {
                        "role": "system",
                        "content": "Create clear Q&A pairs for a treasury/finance context. Output them as:\nQ: ...\nA: ...\nQ: ...\nA: ... etc."
                    },
                    {
                        "role": "user",
                        "content": f"Generate relevant Q&A from the following text:\n{chunk}"
                    }
                ]
                resp = self.openai.chat.completions.create(
                    model=model_name,
                    messages=prompt,
                    temperature=temperature,
                    top_p=top_p,
                    presence_penalty=presence_penalty,
                    frequency_penalty=frequency_penalty,
                    max_tokens=max_tokens
                )
                content = resp.choices[0].message.content
                logger.debug(f"Réponse brute GPT:\n{content}")
                lines = content.split("\n")
                current_q = None
                current_a = None

                for line in lines:
                    line = line.strip()
                    if line.lower().startswith("q:"):
                        if current_q and current_a:
                            all_qa.append({
                                "question": current_q,
                                "answer": current_a
                            })
                        current_q = line.split(":", 1)[1].strip()
                        current_a = None
                    elif line.lower().startswith("a:"):
                        current_a = line.split(":", 1)[1].strip()

                if current_q and current_a:
                    all_qa.append({
                        "question": current_q,
                        "answer": current_a
                    })

            except Exception as e:
                logger.error(f"Error generating QA in chunk #{idx}: {e}")

        return all_qa

    async def save_to_qdrant(self, file: UploadFile, document_analysis: str, collection_name: str = None):
        """
        Enregistre l'analyse (texte + Q&A) dans Qdrant.
        """
        use_collection = collection_name or self.collection
        logger.info(f"Enregistrement dans Qdrant pour le fichier {file.filename} (collection='{use_collection}')")
        analysis_data = json.loads(document_analysis)
        qa_pairs = analysis_data.get("qa_pairs", [])
        pages = analysis_data.get("pages", [])
        current_count = self.qdrant.count(collection_name=use_collection).count
        logger.info(f"Nombre de points actuel dans Qdrant (collection='{use_collection}'): {current_count}")
        points = []
        base_id = current_count
        embedding_count = 0

        logger.info(f"Embeddings pour {len(qa_pairs)} paires Q&A")
        for qa in qa_pairs:
            combined_text = f"Question: {qa['question']} Answer: {qa['answer']}"
            try:
                if embedding_count > 0 and (embedding_count % 20) == 0:
                    logger.info("Pause pour éviter le rate limit OpenAI...")
                    import asyncio
                    await asyncio.sleep(3)

                emb_resp = self.openai.embeddings.create(
                    model="text-embedding-ada-002",
                    input=combined_text
                )
                emb_vec = emb_resp.data[0].embedding
                points.append(
                    models.PointStruct(
                        id=base_id + len(points),
                        vector=emb_vec,
                        payload={
                            "type": "qa_pair",
                            "question": qa["question"],
                            "answer": qa["answer"],
                            "filename": file.filename
                        }
                    )
                )
                embedding_count += 1

            except Exception as e:
                logger.error(f"Error embedding QA: {e}")

        logger.info("Embeddings pour le contenu du document (texte, images...)")
        for page in pages:
            page_number = page["page_number"]
            for c in page["content"]:
                if c["type"] == "text":
                    subchunks = tokenize_text(c["content"], max_length=500, overlap=0)
                    for sc in subchunks:
                        if sc.strip():
                            try:
                                if embedding_count > 0 and (embedding_count % 20) == 0:
                                    logger.info("Pause pour éviter le rate limit OpenAI...")
                                    import asyncio
                                    await asyncio.sleep(3)

                                emb_resp = self.openai.embeddings.create(
                                    model="text-embedding-ada-002",
                                    input=sc
                                )
                                emb_vec = emb_resp.data[0].embedding
                                points.append(
                                    models.PointStruct(
                                        id=base_id + len(points),
                                        vector=emb_vec,
                                        payload={
                                            "type": "document_chunk",
                                            "content": sc,
                                            "page_number": page_number,
                                            "filename": file.filename
                                        }
                                    )
                                )
                                embedding_count += 1
                            except Exception as e:
                                logger.error(f"Error embedding chunk: {e}")

                elif c["type"] == "image_description":
                    try:
                        desc = c["content"]["general_description"]
                        if embedding_count > 0 and (embedding_count % 20) == 0:
                            logger.info("Pause pour éviter le rate limit OpenAI...")
                            import asyncio
                            await asyncio.sleep(3)

                        emb_resp = self.openai.embeddings.create(
                            model="text-embedding-ada-002",
                            input=desc
                        )
                        emb_vec = emb_resp.data[0].embedding
                        points.append(
                            models.PointStruct(
                                id=base_id + len(points),
                                vector=emb_vec,
                                payload={
                                    "type": "image_description",
                                    "content": c["content"],
                                    "page_number": page_number,
                                    "filename": file.filename
                                }
                            )
                        )
                        embedding_count += 1
                    except Exception as e:
                        logger.error(f"Error embedding image description: {e}")

        logger.info(f"Total points à insérer: {len(points)}")

        BATCH_SIZE = 10
        for i in range(0, len(points), BATCH_SIZE):
            batch = points[i:i+BATCH_SIZE]
            self.qdrant.upsert(
                collection_name=use_collection,
                points=batch
            )
            logger.info(f"Batch de {len(batch)} points insérés dans Qdrant (collection='{use_collection}')")

        return {
            "status": "success",
            "points_added": len(points),
            "qa_pairs_count": len(qa_pairs)
        }

    async def process_directory(self, files: List[UploadFile], collection_name: str = None):
        """
        Traite plusieurs documents en séquence.
        """
        use_collection = collection_name or self.collection

        logger.info(f"Nombre de fichiers à traiter : {len(files)} (collection='{use_collection}')")
        processed_files = []
        total_points_added = 0
        all_qa_pairs = []

        initial_count = self.qdrant.count(collection_name=use_collection).count
        logger.info(f"Nombre initial de points dans Qdrant (collection='{use_collection}'): {initial_count}")

        for f in files:
            try:
                logger.info(f"=== Début du traitement de {f.filename} ===")
                analysis = await self.process_document(f, collection_name=use_collection)
                analysis_str = json.dumps(analysis)
                save_result = await self.save_to_qdrant(f, analysis_str, collection_name=use_collection)

                processed_files.append(f.filename)
                total_points_added += save_result["points_added"]
                all_qa_pairs.extend(analysis.get("qa_pairs", []))

                logger.info(f"Fichier {f.filename} traité : {save_result['points_added']} points ajoutés")
            except Exception as e:
                logger.error(f"Erreur lors du traitement de {f.filename}: {e}")

        final_count = self.qdrant.count(collection_name=use_collection).count
        logger.info("=== Résumé du traitement de directory ===")
        logger.info(f"Fichiers traités : {processed_files}")
        logger.info(f"Points initiaux : {initial_count}, Points finaux : {final_count}")
        logger.info(f"Total points ajoutés : {total_points_added}")
        logger.info(f"Q&A total : {len(all_qa_pairs)}")

        return {
            "status": "success",
            "processed_files": processed_files,
            "stats": {
                "initial_qdrant_count": initial_count,
                "final_qdrant_count": final_count,
                "points_added": total_points_added,
                "qa_pairs_total": len(all_qa_pairs)
            }
        }
