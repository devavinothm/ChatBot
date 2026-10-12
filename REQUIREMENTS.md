# Project Requirement

## Original request
Make a web-based chatbot using Python that responds to questions related to
enterprise policy documents.

## Decisions made

- **LLM backend**: Anthropic Claude API (`claude-sonnet-5`), via `ANTHROPIC_API_KEY`.
- **Web framework**: Flask, serving a REST API plus a plain HTML/CSS/JS frontend.
- **Document ingestion**: both a local `documents/` folder (drop files + reindex)
  and in-browser upload.
- **Retrieval approach**: local sentence-transformer embeddings
  (`all-MiniLM-L6-v2`) with cosine-similarity search over chunked document
  text (no external vector DB — a pickled numpy index in `data/`).
- **Supported document types**: PDF, DOCX, TXT, Markdown.

See [README.md](README.md) for setup/run instructions and project structure,
and [TECHNICAL_SPEC.md](TECHNICAL_SPEC.md) for the detailed architecture,
data flow, and API reference.
