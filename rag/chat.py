from .config import TOP_K
from .llm import generate_completion
from .vector_store import VectorStore

SYSTEM_PROMPT = (
    "You are an internal assistant that answers employee questions about "
    "enterprise policy documents. Answer only using the policy excerpts "
    "provided in the user's message. If the excerpts do not contain enough "
    "information to answer, say you don't know and suggest the employee "
    "contact HR or Compliance. Always mention which source document(s) "
    "support your answer."
)


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

    answer_text = generate_completion(
        messages=messages,
        system_prompt=SYSTEM_PROMPT,
        max_tokens=1024,
    )
    return answer_text, sources
