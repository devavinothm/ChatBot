# Technical Specification — Enterprise Policy Assistant

## 1. Overview

A single-process Flask web application that answers natural-language
questions about a corpus of enterprise policy documents using a
retrieval-augmented generation (RAG) pattern: relevant document excerpts are
retrieved locally via embedding similarity, then passed to Claude (Anthropic
API) as grounding context for the answer.

## 2. Architecture

```
Browser (templates/index.html + static/app.js)
        │  fetch() JSON over HTTP
        ▼
Flask app (app.py)
        │
        ├─ /api/documents   → list indexed files + chunk count
        ├─ /api/upload      → save file into documents/
        ├─ /api/reindex     → rebuild VectorStore from documents/
        └─ /api/chat        → retrieve + call Claude → answer + sources
        │
        ▼
rag/ package
        ├─ document_loader.py  (PDF/DOCX/TXT/MD → plain text)
        ├─ chunker.py           (text → overlapping word-window Chunks)
        ├─ vector_store.py       (SentenceTransformer embeddings, ChromaDB cosine search)
        ├─ indexer.py             (orchestrates load → chunk → embed → Chroma persistence)
        ├─ llm.py                 (swappable LLM client adapter for Groq & Anthropic)
        └─ chat.py                 (builds grounded prompt, invokes LLM adapter)
```

There is no external database or vector-store service. State lives in two
places on disk:

- `documents/` — source files (source of truth).
- `data/index.pkl` — derived cache of chunks + embeddings, safe to delete
  and rebuild at any time via `/api/reindex`.

Conversation history is kept in an in-process dict (`CONVERSATIONS` in
`app.py`), keyed by a UUID stored in a signed Flask session cookie. It is not
persisted and is lost on process restart. This is a single-worker design —
it does not scale to multiple app processes/workers without moving
`CONVERSATIONS` to a shared store (e.g. Redis).

## 3. Data flow

### 3.1 Indexing (`rag/indexer.py: build_index`)

1. Walk `documents/` recursively; for each file with an extension in
   `ALLOWED_EXTENSIONS` (`.pdf`, `.docx`, `.txt`, `.md`), extract plain text
   (`document_loader.py`).
2. Split each document's text into overlapping chunks
   (`chunker.chunk_text`): word-count windows of `CHUNK_SIZE_WORDS` (220)
   with `CHUNK_OVERLAP_WORDS` (40) overlap, stepping by
   `chunk_size - overlap` words.
3. Embed all chunk texts in one batch using `sentence-transformers`
   (`all-MiniLM-L6-v2`, 384-dim, L2-normalized output).
4. Store `(Chunk, embedding)` pairs in a `VectorStore` and pickle it to
   `data/index.pkl`.

This is a full rebuild every time — there is no incremental/delta indexing.
Acceptable for typical policy-document corpora (tens to low hundreds of
files); will get slow as the corpus grows into the thousands of chunks
because `SentenceTransformer.encode` re-embeds everything.

### 3.2 Retrieval (`vector_store.VectorStore.search`)

1. Embed the user's question with the same model, L2-normalized.
2. Compute cosine similarity as a dot product against all stored chunk
   embeddings (`self.embeddings @ query_vector`) — valid because both sides
   are unit-normalized.
3. Return the top `TOP_K` (5) `(Chunk, score)` pairs by score, descending.

This is exact (brute-force) search, O(n) per query. No approximate index
(FAISS/HNSW) is used; fine at the target corpus scale.

### 3.3 Answering (`rag/chat.py: answer_question`)

1. Retrieve top-K chunks for the question.
2. Format them as a numbered context block: `[i] Source: <filename>\n<chunk text>`.
3. Build the outgoing message list: prior conversation turns (plain
   text, capped at the last 20 entries by `app.py`) + a new user turn whose
   content is `"Policy excerpts:\n\n<context>\n\nEmployee question: <question>"`.
4. Delegate generation to `rag.llm: generate_completion`, which routes
   to Groq (`llama-3.3-70b-versatile` by default) or Anthropic Claude
   (`claude-sonnet-5` by default) depending on `LLM_PROVIDER` and available API keys.
5. Extract the generated text from the provider response.
6. Return `(answer_text, sources)` where `sources` is the sorted, deduped
   set of source filenames among the retrieved chunks — regardless of
   whether Claude's answer text actually cited them.

Important: the conversation history stored and replayed to the model is the
**plain** question/answer text, not the context-augmented version — this
keeps the multi-turn prompt from re-sending retrieved excerpts on every turn.
Each turn re-retrieves fresh context based on the latest question only (no
query rewriting using prior turns).

`SYSTEM_PROMPT` instructs the model to answer only from the provided
excerpts, say it doesn't know if the excerpts are insufficient, suggest
contacting HR/Compliance, and cite sources. This is prompt-level grounding
only — there is no post-hoc verification that the answer is actually
supported by the retrieved text.

## 4. API reference

All endpoints are same-origin, JSON in/out (except `/api/upload`, which is
`multipart/form-data`).

| Method | Path             | Body                                | Response                                                  |
|--------|------------------|--------------------------------------|------------------------------------------------------------|
| GET    | `/`              | —                                     | Renders the chat UI (`templates/index.html`)               |
| GET    | `/api/documents` | —                                     | `{documents: [filename...], chunks_indexed: int}`          |
| POST   | `/api/upload`    | form field `file`                    | `{status: "uploaded", filename}` or `{error}` (400)        |
| POST   | `/api/reindex`   | —                                     | `{status: "ok", chunks_indexed: int}`                      |
| POST   | `/api/chat`      | `{message: string}`                  | `{answer: string, sources: [filename...]}` or `{error}` (400/500) |

`/api/chat` errors:
- `400` if `message` is missing/empty.
- `500` if `ANTHROPIC_API_KEY` is unset (raised as `RuntimeError` in
  `rag/chat.py: get_client`).

`/api/upload` rejects (`400`) any extension not in `ALLOWED_EXTENSIONS`.
The uploaded filename is sanitized via `Path(file.filename).name`, which
strips directory components to prevent path traversal outside
`documents/`. Upload does **not** automatically reindex server-side; the
frontend (`static/app.js`) calls `/api/reindex` itself right after a
successful upload.

## 5. Configuration (`rag/config.py`)

| Setting                | Default                   | Effect                                                   |
|-------------------------|---------------------------|-----------------------------------------------------------|
| `EMBEDDING_MODEL_NAME` | `all-MiniLM-L6-v2`        | Sentence-transformers model for embeddings (384-dim)      |
| `LLM_PROVIDER`          | `auto`                    | Active provider: `auto`, `groq`, or `anthropic`           |
| `GROQ_MODEL`            | `llama-3.3-70b-versatile` | Groq model used when Groq provider is active              |
| `CLAUDE_MODEL`          | `claude-sonnet-5`         | Anthropic model used when Anthropic provider is active    |
| `CHUNK_SIZE_WORDS`      | 220                       | Words per chunk                                            |
| `CHUNK_OVERLAP_WORDS`   | 40                        | Overlap between consecutive chunks                        |
| `TOP_K`                 | 5                         | Number of chunks retrieved per question                   |
| `MAX_HISTORY_TURNS`     | 6                         | Defined but not currently applied (history capped in `app.py` at 20 entries instead — see §7) |
| `ALLOWED_EXTENSIONS`    | `.pdf .docx .txt .md`     | File types accepted for indexing and upload                |

Environment variables (via `.env`, loaded by `python-dotenv`):

- `LLM_PROVIDER` — optional provider override (`auto`, `groq`, `anthropic`).
- `GROQ_API_KEY` — API key for Groq (dev / testing).
- `GROQ_MODEL` — optional model override for Groq.
- `ANTHROPIC_API_KEY` — API key for Anthropic Claude (target / production).
- `CLAUDE_MODEL` — optional model override for Claude.
- `PORT` — web server port (defaults to 5001 on macOS).
- `FLASK_SECRET_KEY` — signs the session cookie that carries `session_id`;
  defaults to a hardcoded dev value if unset (**must** be overridden for any
  non-local deployment).

## 6. Persistence and file formats

- `data/index.pkl`: a pickled dict `{"chunks": List[Chunk], "embeddings": np.ndarray}`.
  `Chunk` is a `@dataclass(text, source, chunk_index)` defined in
  `rag/chunker.py`. Unpickling requires that module path to still exist and
  be import-compatible — the file is not a portable/versioned format and
  should be treated as a disposable cache, not a backup.
- No database. No migrations.

## 7. Known gaps / deliberate simplifications

- `MAX_HISTORY_TURNS` in `config.py` is unused; `app.py` truncates
  `CONVERSATIONS[session_id]` to the last 20 messages instead. If tightening
  history length matters, wire `MAX_HISTORY_TURNS` through explicitly.
- Full reindex on every `/api/reindex` call — no per-file change detection.
- No authentication/authorization layer — anyone who can reach the Flask
  process can query, upload, and trigger reindexing. Not suitable to expose
  beyond a trusted network without adding auth.
- No rate limiting on `/api/chat` (direct exposure to Anthropic API costs
  per request).
- Single-process, single-worker: `STORE` and `CONVERSATIONS` are Python
  process globals, not safe to run under multiple gunicorn/uwsgi workers as
  written.
- No automated test suite.

## 8. Deployment notes

The bundled `app.run(debug=True)` is a development server only (per Flask's
own warning). For anything beyond local use: run behind a production WSGI
server (e.g. `waitress` on Windows, or `gunicorn` on Linux), disable debug
mode, set a strong `FLASK_SECRET_KEY`, and put the app behind the
organization's SSO/reverse proxy given that policy content and Q&A may be
sensitive.
