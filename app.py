import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, session

from rag.chat import answer_question
from rag.config import ALLOWED_EXTENSIONS, DOCUMENTS_DIR
from rag.indexer import build_index, load_or_build_index

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")

STORE = load_or_build_index()
CONVERSATIONS: dict[str, list] = {}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/documents")
def list_documents():
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    docs = sorted(p.name for p in DOCUMENTS_DIR.glob("*") if p.is_file())
    return jsonify({"documents": docs, "chunks_indexed": STORE.count()})


@app.route("/api/reindex", methods=["POST"])
def reindex():
    global STORE
    STORE = build_index()
    return jsonify({"status": "ok", "chunks_indexed": STORE.count()})


@app.route("/api/upload", methods=["POST"])
def upload():
    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"error": "No file provided"}), 400
    filename = Path(file.filename).name
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({"error": f"Unsupported file type: {ext}"}), 400
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    file.save(DOCUMENTS_DIR / filename)
    return jsonify({"status": "uploaded", "filename": filename})


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    question = (data.get("message") or "").strip()
    if not question:
        return jsonify({"error": "message is required"}), 400

    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    session_id = session["session_id"]
    history = CONVERSATIONS.setdefault(session_id, [])

    try:
        answer_text, sources = answer_question(STORE, question, history)
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 500

    history.append({"role": "user", "content": question})
    history.append({"role": "assistant", "content": answer_text})
    CONVERSATIONS[session_id] = history[-20:]

    return jsonify({"answer": answer_text, "sources": sources})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
