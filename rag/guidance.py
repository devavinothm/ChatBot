import json
import re
from typing import Any, Dict, List, Optional, Tuple

from .config import TOP_K
from .llm import generate_completion
from .vector_store import VectorStore

GUIDANCE_SYSTEM_PROMPT = """You are Guidance Guru, a dedicated goal-oriented coach and progress guide.
Your purpose is to guide the user from their Current State to their Target State for any goal or task they are working on.

Core Principles:
1. Current State vs Target State:
   - Identify where the user is right now (e.g., "$2K in monthly sales", "stuck on step 2 of store launch").
   - Clarify where they want to be (e.g., "$5K monthly sales in 2 months", "live store with 10 products").
   - Quantify or define the gap clearly.
2. Actionable Sequential Milestones:
   - Break the journey down into realistic, bite-sized milestones (Milestone 1, Milestone 2, Milestone 3).
   - Don't overwhelm: focus on the immediate next milestone first.
3. 'Are We There Yet?' & Progress Checks:
   - When asked "Are we there yet?", "How are we doing?", or when progress is reported, evaluate whether they are "On Track", "At Risk", or "Achieved".
   - State progress clearly (estimated % completed, milestones done, remaining gap).
4. Proactive Next Steps:
   - Always conclude each turn with an encouraging, concrete "Next Step" the user can execute today.
5. Solution Escalation:
   - If the user asks deep causal, diagnostic, or "what-if" questions ("Why did progress stall?", "What if I discount 20%?"), provide immediate practical guidance and mention that deep root-cause analysis can be tackled with Solution Mate.
6. Domain Knowledge:
   - If relevant policy or company document excerpts are provided, reference them and cite sources.

CRITICAL: Whenever a goal is active, created, or updated, append an exact metadata block at the very end of your response:
```goal_state
{
  "goal": "Short title of the goal",
  "current": "Current state or value",
  "target": "Target state or value",
  "progress_pct": 40,
  "status": "On Track",
  "next_milestone": "Short description of immediate next action"
}
```
Valid values for "status" are: "Setting Up", "On Track", "At Risk", "Achieved".
If no goal is being discussed (e.g. general greeting), omit the ```goal_state block entirely.
Keep your conversational response formatted with clean markdown, bullet points, and encouraging tone.
"""

GOAL_STATE_PATTERN = re.compile(
    r"```(?:goal_state|json)?\s*(\{[\s\S]*?\"goal\"[\s\S]*?\})\s*```", re.DOTALL
)


def extract_goal_state(text: str) -> Tuple[str, Optional[Dict[str, Any]]]:
    """Extract and parse the goal_state JSON block from LLM output, returning clean text and dict."""
    match = GOAL_STATE_PATTERN.search(text)
    if match:
        json_str = match.group(1)
        clean_text = GOAL_STATE_PATTERN.sub("", text).strip()
        try:
            goal_data = json.loads(json_str)
            return clean_text, goal_data
        except Exception:
            pass

    # Fallback: check for raw JSON object at the end containing "goal"
    raw_match = re.search(r"(\{\s*\"goal\"\s*:[\s\S]*?\})$", text.strip())
    if raw_match:
        try:
            goal_data = json.loads(raw_match.group(1))
            clean_text = text[:raw_match.start()].strip()
            return clean_text, goal_data
        except Exception:
            pass

    return text.strip(), None


def answer_guidance(
    store: VectorStore,
    question: str,
    history: List[dict],
    current_goal_state: Optional[Dict[str, Any]] = None,
) -> Tuple[str, Optional[Dict[str, Any]], List[str]]:
    """Generate guidance response tracking current state vs target state."""
    # Search document store for relevant excerpts
    results = store.search(question, top_k=3)
    sources = []
    policy_context = ""
    if results:
        top_chunk, top_score = results[0]
        if top_score > 0.35:
            sources = sorted({c.source for c, s in results if s > 0.35})
            lines = [f"[{i+1}] Source: {c.source}\n{c.text}" for i, (c, s) in enumerate(results) if s > 0.35]
            if lines:
                policy_context = "Reference Policy/Domain Excerpts:\n" + "\n\n".join(lines) + "\n\n"

    # Augment query with active goal context if present
    state_context = ""
    if current_goal_state:
        state_context = (
            f"[Current Tracked Goal: {current_goal_state.get('goal', 'N/A')} | "
            f"Current: {current_goal_state.get('current', 'N/A')} | "
            f"Target: {current_goal_state.get('target', 'N/A')} | "
            f"Status: {current_goal_state.get('status', 'In Progress')} | "
            f"Progress: {current_goal_state.get('progress_pct', 0)}%]\n\n"
        )

    user_content = f"{state_context}{policy_context}User: {question}".strip()

    messages = [{"role": m["role"], "content": m["content"]} for m in history]
    messages.append({"role": "user", "content": user_content})

    raw_response = generate_completion(
        messages=messages,
        system_prompt=GUIDANCE_SYSTEM_PROMPT,
        max_tokens=2048,
    )

    clean_answer, updated_goal_state = extract_goal_state(raw_response)

    # Merge or retain existing goal state if not explicitly updated
    final_goal_state = updated_goal_state or current_goal_state

    return clean_answer, final_goal_state, sources
