import math
from typing import List, Dict

class LightweightVectorStore:
    """In-memory cosine search migrated from knowledgeBase.ts (No heavy dependencies)"""
    def __init__(self):
        self.documents = []

    def add_document(self, content: str, metadata: Dict = None):
        self.documents.append({"content": content, "metadata": metadata or {}})

    def search(self, query: str, top_k: int = 3) -> List[Dict]:
        # Mock cosine similarity logic
        # In reality, this would use numpy for fast dot products on embeddings
        return self.documents[:top_k]
