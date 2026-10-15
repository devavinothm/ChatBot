import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, session

from rag.chat import answer_question
from rag.config import ALLOWED_EXTENSIONS, DOCUMENTS_DIR
from rag.guidance import answer_guidance
from rag.indexer import build_index, load_or_build_index
from rag.solution import answer_solution

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")

STORE = load_or_build_index()
CONVERSATIONS: dict[str, list] = {}
GUIDANCE_CONVERSATIONS: dict[str, list] = {}
GUIDANCE_GOALS: dict[str, dict] = {}
SOLUTION_CONVERSATIONS: dict[str, list] = {}
SOLUTION_SCENARIOS: dict[str, dict] = {}


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


@app.route("/api/guidance/chat", methods=["POST"])
def guidance_chat():
    data = request.get_json(silent=True) or {}
    question = (data.get("message") or "").strip()
    if not question:
        return jsonify({"error": "message is required"}), 400

    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    session_id = session["session_id"]
    history = GUIDANCE_CONVERSATIONS.setdefault(session_id, [])
    current_goal = GUIDANCE_GOALS.get(session_id)

    try:
        answer_text, updated_goal, sources = answer_guidance(STORE, question, history, current_goal)
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 500

    if updated_goal:
        GUIDANCE_GOALS[session_id] = updated_goal

    history.append({"role": "user", "content": question})
    history.append({"role": "assistant", "content": answer_text})
    GUIDANCE_CONVERSATIONS[session_id] = history[-20:]

    return jsonify({"answer": answer_text, "goal_state": GUIDANCE_GOALS.get(session_id), "sources": sources})


@app.route("/api/guidance/reset", methods=["POST"])
def guidance_reset():
    session_id = session.get("session_id")
    if session_id:
        GUIDANCE_CONVERSATIONS.pop(session_id, None)
        GUIDANCE_GOALS.pop(session_id, None)
    return jsonify({"status": "reset"})


@app.route("/api/guidance/state")
def guidance_state():
    session_id = session.get("session_id")
    return jsonify({
        "goal_state": GUIDANCE_GOALS.get(session_id) if session_id else None,
        "history_count": len(GUIDANCE_CONVERSATIONS.get(session_id, [])) if session_id else 0
    })


@app.route("/api/solution/chat", methods=["POST"])
def solution_chat():
    data = request.get_json(silent=True) or {}
    question = (data.get("message") or "").strip()
    if not question:
        return jsonify({"error": "message is required"}), 400

    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    session_id = session["session_id"]
    history = SOLUTION_CONVERSATIONS.setdefault(session_id, [])
    current_scenario = SOLUTION_SCENARIOS.get(session_id)

    try:
        answer_text, updated_analysis, sources = answer_solution(STORE, question, history, current_scenario)
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 500

    if updated_analysis:
        SOLUTION_SCENARIOS[session_id] = updated_analysis

    history.append({"role": "user", "content": question})
    history.append({"role": "assistant", "content": answer_text})
    SOLUTION_CONVERSATIONS[session_id] = history[-20:]

    return jsonify({"answer": answer_text, "analysis": SOLUTION_SCENARIOS.get(session_id), "sources": sources})


@app.route("/api/solution/reset", methods=["POST"])
def solution_reset():
    session_id = session.get("session_id")
    if session_id:
        SOLUTION_CONVERSATIONS.pop(session_id, None)
        SOLUTION_SCENARIOS.pop(session_id, None)
    return jsonify({"status": "reset"})


@app.route("/api/solution/state")
def solution_state():
    session_id = session.get("session_id")
    return jsonify({
        "analysis": SOLUTION_SCENARIOS.get(session_id) if session_id else None,
        "history_count": len(SOLUTION_CONVERSATIONS.get(session_id, [])) if session_id else 0
    })


@app.route("/api/clear_all", methods=["POST"])
def clear_all():
    session_id = session.get("session_id")
    if session_id:
        CONVERSATIONS.pop(session_id, None)
        GUIDANCE_CONVERSATIONS.pop(session_id, None)
        GUIDANCE_GOALS.pop(session_id, None)
        SOLUTION_CONVERSATIONS.pop(session_id, None)
        SOLUTION_SCENARIOS.pop(session_id, None)
    return jsonify({"status": "cleared"})


@app.route("/api/store_info")
def store_info():
    from rag.store_data import get_store_badge_info
    return jsonify(get_store_badge_info())


@app.route("/api/store_analytics")
def store_analytics():
    from rag.store_data import get_store_analytics
    return jsonify(get_store_analytics())


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(debug=True, port=port)

