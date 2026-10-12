from typing import List, Optional

import chromadb
from sentence_transformers import SentenceTransformer

from .chunker import Chunk
from .config import CHROMA_DIR, COLLECTION_NAME, EMBEDDING_MODEL_NAME

_model: Optional[SentenceTransformer] = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _model


class VectorStore:
    def __init__(self):
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        self._collection = self._client.get_or_create_collection(
            COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
        )

    def count(self) -> int:
        return self._collection.count()

    def build(self, chunks: List[Chunk]) -> None:
        self._client.delete_collection(COLLECTION_NAME)
        self._collection = self._client.get_or_create_collection(
            COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
        )
        if not chunks:
            return
        model = get_model()
        texts = [c.text for c in chunks]
        vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False).tolist()
        ids = [f"{c.source}::{c.chunk_index}" for c in chunks]
        metadatas = [{"source": c.source, "chunk_index": c.chunk_index} for c in chunks]
        self._collection.add(ids=ids, embeddings=vectors, documents=texts, metadatas=metadatas)

    def search(self, query: str, top_k: int):
        if self._collection.count() == 0:
            return []
        model = get_model()
        query_vector = model.encode([query], normalize_embeddings=True, show_progress_bar=False)[0].tolist()
        results = self._collection.query(query_embeddings=[query_vector], n_results=top_k)
        pairs = []
        for text, metadata, distance in zip(
            results["documents"][0], results["metadatas"][0], results["distances"][0]
        ):
            chunk = Chunk(text=text, source=metadata["source"], chunk_index=metadata["chunk_index"])
            pairs.append((chunk, 1 - distance))
        return pairs
