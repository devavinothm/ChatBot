from dataclasses import dataclass


@dataclass
class Chunk:
    text: str
    source: str
    chunk_index: int


def chunk_text(text: str, source: str, chunk_size: int, overlap: int):
    """Split text into overlapping word-count windows."""
    words = text.split()
    chunks = []
    step = max(chunk_size - overlap, 1)
    index = 0
    for start in range(0, len(words), step):
        piece = words[start:start + chunk_size]
        if not piece:
            continue
        chunks.append(Chunk(text=" ".join(piece), source=source, chunk_index=index))
        index += 1
        if start + chunk_size >= len(words):
            break
    return chunks
