from pathlib import Path

import docx
from pypdf import PdfReader

from .config import ALLOWED_EXTENSIONS


def load_text_from_file(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".pdf":
        return _load_pdf(path)
    if ext == ".docx":
        return _load_docx(path)
    if ext in (".txt", ".md"):
        return path.read_text(encoding="utf-8", errors="ignore")
    raise ValueError(f"Unsupported file type: {ext}")


def _load_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _load_docx(path: Path) -> str:
    document = docx.Document(str(path))
    return "\n".join(p.text for p in document.paragraphs)


def iter_documents(documents_dir: Path):
    """Yield (source_name, full_text) for every supported file in documents_dir."""
    for path in sorted(documents_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() in ALLOWED_EXTENSIONS:
            text = load_text_from_file(path)
            if text.strip():
                yield path.name, text
