# Enterprise Policy Assistant

A web-based chatbot that answers questions about your company's policy
documents. It retrieves the most relevant excerpts from your documents using
local embeddings, then asks Claude to answer using only those excerpts, with
source citations.

## How it works

1. Drop policy documents (PDF, DOCX, TXT, or Markdown) into `documents/`, or
   upload them from the web UI.
2. On startup (or when you click "Reindex"), the app splits documents into
   overlapping chunks and embeds them locally using a small sentence-transformer
   model (`all-MiniLM-L6-v2`). The index is cached in `data/index.pkl`.
3. When a user asks a question, the app finds the most relevant chunks by
   cosine similarity and sends them to Claude along with the question.
   Claude is instructed to answer only from those excerpts and to cite the
   source document(s).

## Setup

1. Create a virtual environment and install dependencies:

   ```
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

   The first install downloads `sentence-transformers` (and PyTorch), so it
   may take a few minutes and a few hundred MB of disk space.

2. Copy `.env.example` to `.env` and fill in your Anthropic API key:

   ```
   copy .env.example .env
   ```

   Set `ANTHROPIC_API_KEY` to a key from https://console.anthropic.com/.

3. Run the app:

   ```
   python app.py
   ```

   Open http://127.0.0.1:5000 in your browser.

A sample policy document (`documents/remote_work_policy.txt`) is included so
you can try it out immediately — e.g. ask "How much PTO do I get?" or "Can I
use public Wi-Fi for work?".

## Adding your own documents

- **Bulk load**: put PDF/DOCX/TXT/MD files in `documents/`, then click
  "Reindex documents/ folder" in the sidebar (or restart the app if the index
  doesn't exist yet).
- **From the browser**: use the "Upload & Reindex" form in the sidebar. This
  saves the file into `documents/` and rebuilds the index automatically.

Reindexing re-embeds every file in `documents/`, so it's fast for typical
policy-document collections (tens to low hundreds of files) but will get
slower as the collection grows into the thousands.

## Notes and limitations

- Retrieval quality depends on chunking and embedding a general-purpose
  model — for very large or highly technical policy sets you may want to
  tune `CHUNK_SIZE_WORDS`, `CHUNK_OVERLAP_WORDS`, and `TOP_K` in
  `rag/config.py`.
- Conversation history is kept in server memory per browser session (via a
  signed cookie) and is lost on restart. For production use, back this with a
  real session store or database.
- This app does not implement authentication — if you deploy it beyond local
  use, put it behind your organization's SSO/auth layer, since policy
  documents may be sensitive.
- `data/` (the built index) and `.env` are git-ignored since they may contain
  sensitive content or secrets. Decide deliberately whether `documents/`
  should be committed to source control given the sensitivity of your policy
  content.

## Project structure

```
app.py                  Flask app: routes for chat, upload, reindex, documents
rag/
  config.py             Paths, model names, chunking/retrieval settings
  document_loader.py    PDF/DOCX/TXT/MD text extraction
  chunker.py             Splits text into overlapping chunks
  vector_store.py        Embedding + cosine-similarity search, persistence
  indexer.py             Builds/loads the index from documents/
  chat.py                 Retrieval + Claude prompt/response handling
templates/index.html    Chat UI
static/style.css         Styling
static/app.js             Chat, upload, and reindex client logic
documents/               Source policy documents (drop files here)
data/                     Cached index (created at runtime)
```
