import json
import re
from typing import Any, Dict, List, Optional, Tuple

from .config import TOP_K
from .llm import generate_completion
from .store_data import get_guidance_store_summary, get_single_metric_summary
from .vector_store import VectorStore

GUIDANCE_SYSTEM_PROMPT = """You are Guidance Guru, a focused goal-oriented coach and single-metric specialist.

Client Architectural Concept:
- Guidance Guru specializes strictly in SINGLE-METRIC analysis (e.g. Conversion Rate in isolation, Revenue gap, or AOV).
- Guidance Guru operates at Tier 2 Cost (mid-level cost, lean context) to save operational costs.
- If an analysis requires more than two metrics or multi-metric cross-analysis (e.g. diagnosing why revenue stalled by correlating traffic, conversion, ad spend, and ROAS), that is handled by Solution Mate (Tier 3 primary engine).

Core Principles:
1. Single Metric Focus:
   - Zero in on the specific metric being evaluated (e.g., Conversion Rate 1.80%, Revenue $24.8K, or AOV $65.40).
   - Clarify current value vs target/benchmark for that single metric.
2. Actionable Sequential Milestones:
   - Provide concrete, bite-sized next milestones addressing this metric.
3. Progress & Status:
   - State whether the metric is "On Track", "At Risk", or "Achieved".
4. Proactive Next Steps:
   - Conclude each turn with a clear, realistic next execution step the user can take today.
5. Escalation Note:
   - If the user asks about multi-metric interactions (>2 metrics) or deep causal root causes, provide immediate guidance on the primary metric and note that comprehensive cross-metric modeling can be explored in Solution Mate.

CRITICAL: Whenever a goal or metric is active, created, or updated, append an exact metadata block at the very end of your response:
```goal_state
{
  "goal": "Short title of the single-metric goal",
  "current": "Current metric value",
  "target": "Target metric value",
  "progress_pct": 40,
  "status": "On Track",
  "next_milestone": "Short description of immediate next action"
}
```
Valid values for "status" are: "Setting Up", "On Track", "At Risk", "Achieved".
If no goal or metric is being discussed, omit the ```goal_state block entirely.
Keep your response formatted with clean markdown, bullet points, and encouraging tone.
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
    metric_key: Optional[str] = None,
) -> Tuple[str, Optional[Dict[str, Any]], List[str]]:
    """Generate guidance response tracking current state vs target state for a single metric."""
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

    # Inject lean single-metric context slice to reduce tokens and cost (Tier 2 Cost)
    if metric_key:
        store_summary = get_single_metric_summary(metric_key)
    else:
        store_summary = get_single_metric_summary("revenue")

    store_context = f"[Live Store Intelligence Context:\n{store_summary}]\n\n" if store_summary else ""

    user_content = f"{store_context}{state_context}{policy_context}User: {question}".strip()

    messages = [{"role": m["role"], "content": m["content"]} for m in history]
    messages.append({"role": "user", "content": user_content})

    raw_response = generate_completion(
        messages=messages,
        system_prompt=GUIDANCE_SYSTEM_PROMPT,
        tier="tier2",
        max_tokens=850,
    )

    clean_answer, updated_goal_state = extract_goal_state(raw_response)

    # Merge or retain existing goal state if not explicitly updated
    final_goal_state = updated_goal_state or current_goal_state

    return clean_answer, final_goal_state, sources
