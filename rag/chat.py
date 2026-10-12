import os
from typing import Optional

from anthropic import Anthropic

from .config import CLAUDE_MODEL, TOP_K
from .vector_store import VectorStore

SYSTEM_PROMPT = (
    "You are an internal assistant that answers employee questions about "
    "enterprise policy documents. Answer only using the policy excerpts "
    "provided in the user's message. If the excerpts do not contain enough "
    "information to answer, say you don't know and suggest the employee "
    "contact HR or Compliance. Always mention which source document(s) "
    "support your answer."
)

_client: Optional[Anthropic] = None


def get_client() -> Anthropic:
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set. Add it to your .env file.")
        _client = Anthropic(api_key=api_key)
    return _client


def format_context(results) -> str:
    if not results:
        return "No matching policy excerpts were found."
    lines = []
    for i, (chunk, _score) in enumerate(results, start=1):
        lines.append(f"[{i}] Source: {chunk.source}\n{chunk.text}")
    return "\n\n".join(lines)


def answer_question(store: VectorStore, question: str, history: list):
    """history is a list of {'role': 'user'|'assistant', 'content': str} using plain
    (non-context-augmented) text, so the conversation stays compact across turns."""
    results = store.search(question, TOP_K)
    context = format_context(results)
    sources = sorted({chunk.source for chunk, _ in results})

    augmented_question = f"Policy excerpts:\n\n{context}\n\nEmployee question: {question}"

    messages = [{"role": m["role"], "content": m["content"]} for m in history]
    messages.append({"role": "user", "content": augmented_question})

    client = get_client()
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=messages,
    )
    answer_text = "".join(block.text for block in response.content if block.type == "text")
    return answer_text, sources
