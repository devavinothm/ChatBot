import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, session

from rag.chat import answer_question
from rag.config import ALLOWED_EXTENSIONS, DOCUMENTS_DIR
from rag.guidance import answer_guidance
from rag.indexer import build_index, load_or_build_index
from rag.multi_agent import build_thinking_flow, detect_metrics, orchestrate_multi_agent
from rag.solution import answer_solution
from rag.utility import answer_utility

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")

STORE = load_or_build_index()
CONVERSATIONS: dict[str, list] = {}
GUIDANCE_CONVERSATIONS: dict[str, list] = {}
GUIDANCE_GOALS: dict[str, dict] = {}
SOLUTION_CONVERSATIONS: dict[str, list] = {}
SOLUTION_SCENARIOS: dict[str, dict] = {}
MULTI_AGENT_CONVERSATIONS: dict[str, list] = {}
UTILITY_CONVERSATIONS: dict[str, list] = {}
UTILITY_DRAFTS: dict[str, dict] = {}


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
    matched_metrics = detect_metrics(question)
    primary_metric = matched_metrics[0]["id"] if matched_metrics else "revenue"

    try:
        answer_text, updated_goal, sources = answer_guidance(
            STORE, question, history, current_goal, metric_key=primary_metric
        )
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 500

    if updated_goal:
        GUIDANCE_GOALS[session_id] = updated_goal

    thinking_flow = build_thinking_flow(
        question,
        "guidance_guru",
        matched_metrics if matched_metrics else [{"name": "Monthly Revenue", "current": "$24,850", "target": "$50,000"}],
        "Single-metric coaching via Guidance Guru (Tier 2 Cost).",
        "Single-Metric Guidance",
    )

    history.append({"role": "user", "content": question})
    history.append({"role": "assistant", "content": answer_text})
    GUIDANCE_CONVERSATIONS[session_id] = history[-20:]

    return jsonify({
        "answer": answer_text,
        "goal_state": GUIDANCE_GOALS.get(session_id),
        "sources": sources,
        "thinking_flow": thinking_flow,
    })


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
    matched_metrics = detect_metrics(question)

    try:
        answer_text, updated_analysis, sources = answer_solution(STORE, question, history, current_scenario)
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 500

    if updated_analysis:
        SOLUTION_SCENARIOS[session_id] = updated_analysis

    thinking_flow = build_thinking_flow(
        question,
        "solution_mate",
        matched_metrics,
        "Multi-metric strategic diagnostic and scenario modeling via Solution Mate (Tier 3 Flagship Engine).",
        "Multi-Metric Strategic Diagnostic",
    )

    history.append({"role": "user", "content": question})
    history.append({"role": "assistant", "content": answer_text})
    SOLUTION_CONVERSATIONS[session_id] = history[-20:]

    return jsonify({
        "answer": answer_text,
        "analysis": SOLUTION_SCENARIOS.get(session_id),
        "sources": sources,
        "thinking_flow": thinking_flow,
    })


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


@app.route("/api/multi_agent/chat", methods=["POST"])
def multi_agent_chat():
    data = request.get_json(silent=True) or {}
    question = (data.get("message") or "").strip()
    if not question:
        return jsonify({"error": "message is required"}), 400

    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    session_id = session["session_id"]
    history = MULTI_AGENT_CONVERSATIONS.setdefault(session_id, [])

    session_state = {
        "goal_state": GUIDANCE_GOALS.get(session_id),
        "solution_analysis": SOLUTION_SCENARIOS.get(session_id),
        "utility_draft": UTILITY_DRAFTS.get(session_id),
    }

    try:
        result = orchestrate_multi_agent(STORE, question, history, session_state)
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 500

    meta = result.get("metadata", {})
    if meta.get("goal_state"):
        GUIDANCE_GOALS[session_id] = meta["goal_state"]
    if meta.get("solution_analysis"):
        SOLUTION_SCENARIOS[session_id] = meta["solution_analysis"]
    if meta.get("utility_draft"):
        UTILITY_DRAFTS[session_id] = meta["utility_draft"]

    history.append({"role": "user", "content": question})
    history.append({"role": "assistant", "content": result["answer"]})
    MULTI_AGENT_CONVERSATIONS[session_id] = history[-20:]

    return jsonify(result)


@app.route("/api/multi_agent/reset", methods=["POST"])
def multi_agent_reset():
    session_id = session.get("session_id")
    if session_id:
        MULTI_AGENT_CONVERSATIONS.pop(session_id, None)
    return jsonify({"status": "reset"})


@app.route("/api/utility/chat", methods=["POST"])
def utility_chat():
    data = request.get_json(silent=True) or {}
    question = (data.get("message") or "").strip()
    if not question:
        return jsonify({"error": "message is required"}), 400

    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    session_id = session["session_id"]
    history = UTILITY_CONVERSATIONS.setdefault(session_id, [])
    current_draft = UTILITY_DRAFTS.get(session_id)

    try:
        answer_text, updated_draft = answer_utility(question, history, current_draft)
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 500

    if updated_draft:
        UTILITY_DRAFTS[session_id] = updated_draft

    history.append({"role": "user", "content": question})
    history.append({"role": "assistant", "content": answer_text})
    UTILITY_CONVERSATIONS[session_id] = history[-20:]

    return jsonify({"answer": answer_text, "draft": UTILITY_DRAFTS.get(session_id)})


@app.route("/api/utility/reset", methods=["POST"])
def utility_reset():
    session_id = session.get("session_id")
    if session_id:
        UTILITY_CONVERSATIONS.pop(session_id, None)
        UTILITY_DRAFTS.pop(session_id, None)
    return jsonify({"status": "reset"})


@app.route("/api/clear_all", methods=["POST"])
def clear_all():
    session_id = session.get("session_id")
    if session_id:
        CONVERSATIONS.pop(session_id, None)
        GUIDANCE_CONVERSATIONS.pop(session_id, None)
        GUIDANCE_GOALS.pop(session_id, None)
        SOLUTION_CONVERSATIONS.pop(session_id, None)
        SOLUTION_SCENARIOS.pop(session_id, None)
        MULTI_AGENT_CONVERSATIONS.pop(session_id, None)
        UTILITY_CONVERSATIONS.pop(session_id, None)
        UTILITY_DRAFTS.pop(session_id, None)
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

