import json
import re
from typing import Any, Dict, List, Optional, Tuple

from .config import TOP_K
from .llm import generate_completion
from .store_data import get_solution_store_summary
from .vector_store import VectorStore

SOLUTION_SYSTEM_PROMPT = """You are Solution Mate, the primary strategic diagnostic and reasoning engine for Giri's Fried Chicken.

Client Architectural Concept:
- Solution Mate is the PRIMARY high-power engine deployed whenever a question accesses MORE THAN TWO METRICS (or multi-metric cross-analysis, e.g. correlating Revenue, Conversion Rate, Traffic, CAC, and ROAS).
- Solution Mate operates at Tier 3 (primary deep reasoning, comprehensive context) to uncover root causes and model trade-offs across multiple interacting business levers.
- If a query is strictly about a single metric, that is handled at lower cost by Guidance Guru (Tier 2).

Core Capabilities:
1. Multi-Metric Cross-Analysis (>2 metrics):
   - Synthesize multiple metrics simultaneously (Traffic × Conversion Rate × AOV × Retention × Margin).
   - Trace cross-metric ripple effects (e.g., how shifting Meta ad spend to Google impacts blended CAC, ROAS, and total monthly revenue).
2. Root-Cause Diagnosis:
   - Diagnose why sales plateaued at ~$24.8K despite steady traffic (66.6% checkout shipping shock leak).
3. "What-If" Scenario Modeling:
   - Evaluate trade-offs with mathematical rigor and behavioral logic.
4. Confidence Rating & Risk Assessment:
   - Provide an explicit Confidence Level: High, Medium, or Low (with limitations noted).
5. Human Escalation:
   - If an action requires authorized policy sign-off or significant risk, suggest escalation to human leadership.

Formatting Guidelines:
- Keep the response structured, crisp, and analytical (around 300-500 words).
- Use clear bullet points and comparison tables where helpful.
- ALWAYS end your response with this exact metadata block:
```solution_analysis
{
  "primary_driver": "Short summary of main lever or root cause",
  "scenario_evaluated": "What-if scenario or problem evaluated across multiple metrics",
  "expected_impact": "Summary of expected outcome (e.g. '+20% revenue' or 'Mitigate churn')",
  "confidence": "High",
  "requires_human_review": false
}
```
Valid values for "confidence" are: "High", "Medium", "Low".
"""

ANALYSIS_PATTERN = re.compile(
    r"```(?:solution_analysis|json)?\s*(\{[\s\S]*?\"primary_driver\"[\s\S]*?\})\s*```", re.DOTALL
)


def extract_solution_analysis(text: str) -> Tuple[str, Optional[Dict[str, Any]]]:
    """Extract and parse the solution_analysis JSON block from LLM output."""
    match = ANALYSIS_PATTERN.search(text)
    if match:
        json_str = match.group(1)
        clean_text = ANALYSIS_PATTERN.sub("", text).strip()
        try:
            analysis_data = json.loads(json_str)
            return clean_text, analysis_data
        except Exception:
            pass

    # Fallback: check for raw JSON object at the end containing primary_driver
    raw_match = re.search(r"(\{\s*\"primary_driver\"\s*:[\s\S]*?\})$", text.strip())
    if raw_match:
        try:
            analysis_data = json.loads(raw_match.group(1))
            clean_text = text[:raw_match.start()].strip()
            return clean_text, analysis_data
        except Exception:
            pass

    return text.strip(), None


def answer_solution(
    store: VectorStore,
    question: str,
    history: List[dict],
    current_scenario: Optional[Dict[str, Any]] = None,
) -> Tuple[str, Optional[Dict[str, Any]], List[str]]:
    """Generate deep diagnostic reasoning, scenario modeling, and recommendations."""
    # Search document store for relevant policy or guideline excerpts
    results = store.search(question, top_k=3)
    sources = []
    policy_context = ""
    if results:
        top_chunk, top_score = results[0]
        if top_score > 0.35:
            sources = sorted({c.source for c, s in results if s > 0.35})
            lines = [f"[{i+1}] Source: {c.source}\n{c.text}" for i, (c, s) in enumerate(results) if s > 0.35]
            if lines:
                policy_context = "Relevant Company / Policy Excerpts:\n" + "\n\n".join(lines) + "\n\n"

    scenario_context = ""
    if current_scenario:
        scenario_context = (
            f"[Prior Scenario Context: Key Driver: {current_scenario.get('primary_driver', 'N/A')} | "
            f"Evaluated: {current_scenario.get('scenario_evaluated', 'N/A')} | "
            f"Confidence: {current_scenario.get('confidence', 'N/A')}]\n\n"
        )

    # Inject live e-commerce store analytics & historical trends
    store_summary = get_solution_store_summary()
    store_context = f"[Live Store Intelligence & Historical Data:\n{store_summary}]\n\n" if store_summary else ""

    user_content = f"{store_context}{scenario_context}{policy_context}User Problem / Scenario: {question}".strip()

    messages = [{"role": m["role"], "content": m["content"]} for m in history]
    messages.append({"role": "user", "content": user_content})

    raw_response = generate_completion(
        messages=messages,
        system_prompt=SOLUTION_SYSTEM_PROMPT,
        tier="tier3",
        max_tokens=1500,
    )

    clean_answer, updated_analysis = extract_solution_analysis(raw_response)
    final_analysis = updated_analysis or current_scenario

    return clean_answer, final_analysis, sources
