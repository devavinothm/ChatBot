import json
import re
from typing import Any, Dict, List, Optional, Tuple

from .config import TOP_K
from .llm import generate_completion
from .vector_store import VectorStore

SOLUTION_SYSTEM_PROMPT = """You are Solution Mate, an advanced strategic diagnostic and reasoning partner.
Your mission is to perform deep causal analysis, diagnose roadblocks, and evaluate "what-if" scenarios.

Core Capabilities:
1. Past vs Present vs Target State Analysis:
   - Analyze where performance came from (past), why it stalled (present), and what is needed to reach the goal (target).
   - Uncover the true root cause (e.g. drop in conversion, churn, pricing friction, operational bottleneck).
2. "What-If" Scenario Modeling:
   - Handle hypothetical questions (e.g. "If I increase price by 20%, what happens?", "If I want to grow by 50%, what moves the needle fastest?").
   - Compare alternatives with clear pros, cons, and mathematical or behavioral trade-offs.
3. Structured Problem Decomposition:
   - Break broad problems into core diagnostic drivers (Traffic × Conversion Rate × AOV × Retention).
4. Explainable Recommendations & Confidence Rating:
   - Present reasoning clearly with data-driven logic.
   - Provide an explicit Confidence Level: High, Medium, or Low (with limitations noted).
5. Human Escalation:
   - If an action requires authorized policy sign-off, legal compliance, or high risk, suggest escalation to a human domain expert.

Formatting Guidelines:
- Keep the response structured, crisp, and punchy (around 300-500 words).
- Use clear bullet points and comparison tables where helpful.
- ALWAYS end your response with this exact metadata block:
```solution_analysis
{
  "primary_driver": "Short summary of main lever or root cause",
  "scenario_evaluated": "What-if scenario or problem evaluated",
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

    user_content = f"{scenario_context}{policy_context}User Problem / Scenario: {question}".strip()

    messages = [{"role": m["role"], "content": m["content"]} for m in history]
    messages.append({"role": "user", "content": user_content})

    raw_response = generate_completion(
        messages=messages,
        system_prompt=SOLUTION_SYSTEM_PROMPT,
        max_tokens=3000,
    )

    clean_answer, updated_analysis = extract_solution_analysis(raw_response)
    final_analysis = updated_analysis or current_scenario

    return clean_answer, final_analysis, sources
