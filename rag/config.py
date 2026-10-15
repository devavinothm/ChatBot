import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DOCUMENTS_DIR = BASE_DIR / "documents"
DATA_DIR = BASE_DIR / "data"
CHROMA_DIR = DATA_DIR / "chroma"
COLLECTION_NAME = "policy_docs"

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "auto")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5")

CHUNK_SIZE_WORDS = 220
CHUNK_OVERLAP_WORDS = 40
TOP_K = 5
MAX_HISTORY_TURNS = 6

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}
