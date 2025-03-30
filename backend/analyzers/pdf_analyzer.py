# backend/analyzers/pdf_analyzer.py

import os
import io
import base64
import logging
from PIL import Image
import imagehash
import fitz 
from openai import OpenAI
from dotenv import load_dotenv
from typing import Dict, List

logger = logging.getLogger(__name__)

class PDFAnalyzer:
    def __init__(self, qdrant_client=None, openai_client=None):
        load_dotenv()
        self.qdrant_client = qdrant_client
        self.client = openai_client
        self.image_hashes = {}
        self.min_image_size = 100
        self.hash_threshold = 5

    def compute_image_hash(self, image: Image.Image) -> str:
        return str(imagehash.average_hash(image))

    def is_recurring_image(self, image: Image.Image) -> bool:
        """Détermine si l’image est récurrente (logo, etc.)"""
        if image.size[0] < self.min_image_size or image.size[1] < self.min_image_size:
            return True
        img_hash = self.compute_image_hash(image)
        self.image_hashes[img_hash] = self.image_hashes.get(img_hash, 0) + 1
        return self.image_hashes[img_hash] > self.hash_threshold

    def extract_text_and_images(self, pdf_path: str) -> List[Dict]:
        doc = fitz.open(pdf_path)
        for page_num in range(len(doc)):
            page = doc[page_num]
            image_list = page.get_images()
            for img in image_list:
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image = Image.open(io.BytesIO(image_bytes))
                self.compute_image_hash(image)

        pages_content = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_dict = {
                "page_number": page_num + 1,
                "text": page.get_text(),
                "images": []
            }
            image_list = page.get_images()
            for img_index, img in enumerate(image_list):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image = Image.open(io.BytesIO(image_bytes))
                if self.is_recurring_image(image):
                    continue
                buffered = io.BytesIO()
                image.save(buffered, format="PNG")
                img_base64 = base64.b64encode(buffered.getvalue()).decode()
                page_dict["images"].append({
                    "image_index": img_index,
                    "image_data": img_base64
                })
            pages_content.append(page_dict)

        doc.close()
        return pages_content

    def analyze_image(self, image_base64: str) -> Dict:
        """
        (Facultatif) Tu peux appeler un modèle vision GPT-4, 
        ou renvoyer un JSON minimal.
        """
        return {
            "type": "image description",
            "content": {
                "general_description": "Not implemented",
                "tables": [],
                "figures": [],
                "text_elements": []
            }
        }

    def analyze_pdf(self, pdf_path: str) -> Dict:
        pages_content = self.extract_text_and_images(pdf_path)
        analyzed_pages = []
        for page in pages_content:
            page_analysis = {
                "page_number": page["page_number"],
                "content": []
            }
            page_analysis["content"].append({
                "type": "text",
                "content": page["text"]
            })
            for img in page["images"]:
                page_analysis["content"].append(self.analyze_image(img["image_data"]))

            analyzed_pages.append(page_analysis)

        return {
            "document_structure": "pdf",
            "total_pages": len(analyzed_pages),
            "pages": analyzed_pages
        }
