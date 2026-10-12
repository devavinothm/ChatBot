from .chunker import chunk_text
from .config import CHUNK_OVERLAP_WORDS, CHUNK_SIZE_WORDS, DOCUMENTS_DIR
from .document_loader import iter_documents
from .vector_store import VectorStore


def _collect_chunks():
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    all_chunks = []
    for source_name, text in iter_documents(DOCUMENTS_DIR):
        all_chunks.extend(chunk_text(text, source_name, CHUNK_SIZE_WORDS, CHUNK_OVERLAP_WORDS))
    return all_chunks


def build_index() -> VectorStore:
    store = VectorStore()
    store.build(_collect_chunks())
    return store


def load_or_build_index() -> VectorStore:
    store = VectorStore()
    if store.count() > 0:
        return store
    store.build(_collect_chunks())
    return store
