# backend/analyzers/document_analyzer.py

import os
import io
import logging
from docx import Document
from PIL import Image
import base64

from .pdf_analyzer import PDFAnalyzer

logger = logging.getLogger(__name__)

class DocumentAnalyzer(PDFAnalyzer):
    """
    Hérite de PDFAnalyzer pour réutiliser la logique
    et gère Word (doc/docx).
    """
    def analyze_word_document(self, content: bytes) -> dict:
        doc = Document(io.BytesIO(content))
        pages_content = []
        
        # Word n'a pas la notion de "pages" native, 
        # on simule une unique "page"
        current_page = {
            "page_number": 1,
            "content": [{"type": "text", "content": ""}],
            "images": []
        }

        image_count = 0

        for para in doc.paragraphs:
            # Ajout du texte
            current_page["content"][0]["content"] += para.text + "\n"
            # Si tu veux détecter des images inline, c’est plus complexe...
            # Ce code est minimal.

        pages_content.append(current_page)

        # On “analyse” les images ?
        # Pour l’instant, on n’a pas mis de code d’extraction d’images inline docx
        # Cf. ton code original si tu veux approfondir

        # Convertissons ce pages_content en structure "analyzed_content"
        analyzed_content = []
        for page in pages_content:
            page_analysis = {
                "page_number": page["page_number"],
                "content": []
            }
            page_analysis["content"].append({
                "type": "text",
                "content": page["content"][0]["content"]
            })
            # s’il y avait des images
            for img in page.get("images", []):
                page_analysis["content"].append(self.analyze_image(img["image_data"]))

            analyzed_content.append(page_analysis)

        return {
            "document_structure": "docx",
            "total_pages": len(analyzed_content),
            "pages": analyzed_content
        }

    def analyze_document(self, file_content: bytes, filename: str) -> dict:
        lower = filename.lower()
        if lower.endswith(".pdf"):
            temp_path = f"temp_{filename}"
            with open(temp_path, "wb") as f:
                f.write(file_content)
            try:
                result = self.analyze_pdf(temp_path)
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            return result
        elif lower.endswith(".doc") or lower.endswith(".docx"):
            return self.analyze_word_document(file_content)
        else:
            raise ValueError(f"Unsupported file format: {filename}")
