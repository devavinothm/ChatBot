import json
import re
from typing import Any, Dict, List, Optional, Tuple

from .chat import answer_question
from .guidance import answer_guidance
from .llm import generate_completion
from .solution import answer_solution
from .store_data import get_guidance_store_summary, get_solution_store_summary, get_utility_store_summary
from .utility import answer_utility
from .vector_store import VectorStore

AGENT_REGISTRY = {
    "information_escort": {
        "id": "information_escort",
        "name": "Information Escort",
        "icon": "📚",
        "tab_id": "information-escort",
        "role": "Policy, SLAs & Compliance",
        "description": "Grounds answers in merchant agreements, commission tiers, fulfillment SLAs, and return policies.",
    },
    "guidance_guru": {
        "id": "guidance_guru",
        "name": "Guidance Guru",
        "icon": "🧭",
        "tab_id": "guidance-guru",
        "role": "Goal Coaching & Milestones",
        "description": "Tracks $24.8K ➔ $50K progress, breaks down milestones (MS-01 to MS-04), and provides daily execution steps.",
    },
    "solution_mate": {
        "id": "solution_mate",
        "name": "Solution Mate",
        "icon": "💡",
        "tab_id": "solution-mate",
        "role": "Strategic Diagnostic & Reasoning",
        "description": "Performs root-cause analysis (why sales plateaued), models what-if scenarios, and evaluates ROAS/margins.",
    },
    "utility_minion": {
        "id": "utility_minion",
        "name": "Utility Minion",
        "icon": "🛠️",
        "tab_id": "utility-minion",
        "role": "Creative Execution & Copywriting",
        "description": "Generates marketing copy, abandoned cart email flows, product descriptions, and image creative briefs.",
    },
}

ROUTER_SYSTEM_PROMPT = """You are the Multi-Agent Router and Dispatcher for Giri's Fried Chicken and Gimbll platform.
Your task is to analyze the user question and classify which agent (or combination of agents) should handle it.

The Available Agents:
1. 'information_escort' (Information Escort 📚):
   - Scope: Enterprise policies, platform commission tiers, fulfillment/dispatch SLA rules, perishable food returns, restocking fees, and merchant compliance.
2. 'guidance_guru' (Guidance Guru 🧭):
   - Scope: Tracking store progress toward the $50K Q4 target, milestone progression (MS-01 to MS-04), "Are we there yet?", goal checks, current state vs target state gap, and today's execution checklist.
3. 'solution_mate' (Solution Mate 💡):
   - Scope: Root-cause analysis (why did sales plateau at $24.8K?), what-if scenario modeling (ad budget shift from Meta to Google, bundle simulation, shipping shock fix impact), ROAS/CAC analysis, and product margin comparisons.
4. 'utility_minion' (Utility Minion 🛠️):
   - Scope: Writing copy, drafting emails (e.g. abandoned cart sequence), product descriptions, ad copy/headlines, social captions, image aspect ratio specs, and creative generation prompts.
5. 'collaborative' (Multi-Agent Collaboration 🤝):
   - Scope: Questions requiring more than one agent to answer properly (e.g., policy check + financial modeling, or milestone review + creative copy generation).

Output your routing decision in ONLY this exact JSON format:
```json
{
  "primary_agent": "information_escort" | "guidance_guru" | "solution_mate" | "utility_minion" | "collaborative",
  "secondary_agents": ["agent_id"],
  "reasoning": "Short 1-sentence explanation of why this agent was chosen",
  "intent": "Brief intent label (e.g. 'Fulfillment SLA Query' or 'What-If Budget Reallocation')"
}
```
"""

ROUTER_PATTERN = re.compile(
    r"```(?:json)?\s*(\{[\s\S]*?\"primary_agent\"[\s\S]*?\})\s*```", re.DOTALL
)


def classify_question(question: str) -> Dict[str, Any]:
    """Classify the question to select the optimal agent or collaborative workflow."""
    # Fast heuristic check for obvious domain matches to optimize latency
    q_lower = question.lower()

    # Check for multi-agent / collaborative queries first
    has_policy = any(k in q_lower for k in ["policy", "sla", "commission tier", "restocking fee", "freshness guarantee", "return rule", "returns", "operating agreement", "dispatch window"])
    has_goal = any(k in q_lower for k in ["milestone", "roadmap", "goal", "target state", "current state", "$50k", "are we there yet", "on track"])
    has_strategy = any(k in q_lower for k in ["what if", "why did our sales plateau", "why did sales plateau", "diagnose root cause", "root cause", "roas", "channel", "highest margin", "lowest return rate", "scenario", "model the outcome", "financial impact"])
    has_creative = any(k in q_lower for k in ["draft an email", "write an email", "email sequence", "write copy", "product description", "ad headline", "write an ad", "creative brief", "image prompt", "social caption", "draft a response", "template"])

    # 1. Collaborative combinations:
    if has_policy and (has_creative or has_strategy):
        collabs = ["information_escort"]
        if has_strategy:
            collabs.append("solution_mate")
        if has_creative:
            collabs.append("utility_minion")
        return {
            "primary_agent": "collaborative",
            "secondary_agents": collabs,
            "reasoning": f"Cross-agent inquiry combining policy verification ({collabs[0]}) with {collabs[1]}.",
            "intent": "Policy & Cross-Domain Synthesis",
        }

    if has_goal and has_creative:
        return {
            "primary_agent": "collaborative",
            "secondary_agents": ["guidance_guru", "utility_minion"],
            "reasoning": "Combines milestone tracking from Guidance Guru with execution copy from Utility Minion.",
            "intent": "Milestone-Driven Copywriting",
        }

    if has_strategy and has_creative:
        return {
            "primary_agent": "collaborative",
            "secondary_agents": ["solution_mate", "utility_minion"],
            "reasoning": "Combines strategic scenario modeling with promotional copy execution.",
            "intent": "Strategic Campaign Execution",
        }

    # 2. Single agent direct matching:
    # Creative / Copywriting -> Utility Minion
    if has_creative:
        return {
            "primary_agent": "utility_minion",
            "secondary_agents": [],
            "reasoning": "Creative execution request for copy, email, or marketing drafts.",
            "intent": "Marketing & Content Generation",
        }

    # Policy / Legal / SLA -> Information Escort
    if has_policy:
        return {
            "primary_agent": "information_escort",
            "secondary_agents": [],
            "reasoning": "Inquiry regarding operational policies, SLAs, or merchant terms.",
            "intent": "Policy & Compliance Check",
        }

    # What-If / Root Cause / Modeling -> Solution Mate
    if has_strategy:
        return {
            "primary_agent": "solution_mate",
            "secondary_agents": [],
            "reasoning": "Strategic diagnostic query requiring causal reasoning, ROAS evaluation, or what-if modeling.",
            "intent": "Strategic Scenario & Diagnosis",
        }

    # Goal / Milestone / Progress / Gap -> Guidance Guru
    if has_goal:
        return {
            "primary_agent": "guidance_guru",
            "secondary_agents": [],
            "reasoning": "Goal coaching inquiry regarding milestones, target progress, or execution steps.",
            "intent": "Goal & Milestone Guidance",
        }

    # Default to LLM classification for nuanced queries
    try:
        raw_res = generate_completion(
            messages=[{"role": "user", "content": f"Classify this merchant question:\n\n{question}"}],
            system_prompt=ROUTER_SYSTEM_PROMPT,
            max_tokens=250,
        )
        match = ROUTER_PATTERN.search(raw_res)
        if match:
            parsed = json.loads(match.group(1))
            agent = parsed.get("primary_agent", "solution_mate")
            if agent in AGENT_REGISTRY or agent == "collaborative":
                return parsed
    except Exception:
        pass

    # Safe fallback
    return {
        "primary_agent": "solution_mate",
        "secondary_agents": [],
        "reasoning": "Evaluated as general strategic business intelligence.",
        "intent": "General Business Intelligence",
    }


def handle_collaborative_workflow(
    store: VectorStore,
    question: str,
    history: list,
    agents: List[str],
    session_state: dict,
) -> Tuple[str, List[str], Dict[str, Any]]:
    """Coordinate multiple agents to synthesize an authoritative collaborative answer."""
    pieces = []
    sources = []
    meta = {}

    if "information_escort" in agents:
        ans, srcs = answer_question(store, question, [])
        sources.extend(srcs)
        pieces.append(f"### 📚 Information Escort (Policy Grounding)\n{ans}")

    if "guidance_guru" in agents:
        ans, goal, srcs = answer_guidance(store, question, [], session_state.get("goal_state"))
        if goal:
            meta["goal_state"] = goal
        sources.extend(srcs)
        pieces.append(f"### 🧭 Guidance Guru (Milestone Context)\n{ans}")

    if "solution_mate" in agents:
        ans, analysis, srcs = answer_solution(store, question, [], session_state.get("solution_analysis"))
        if analysis:
            meta["solution_analysis"] = analysis
        sources.extend(srcs)
        pieces.append(f"### 💡 Solution Mate (Diagnostic Analysis)\n{ans}")

    if "utility_minion" in agents:
        ans, draft = answer_utility(question, [], session_state.get("utility_draft"))
        if draft:
            meta["utility_draft"] = draft
        pieces.append(f"### 🛠️ Utility Minion (Creative Execution)\n{ans}")

    # Now synthesize the contributions into a unified executive brief
    synthesis_prompt = (
        "You are the Multi-Agent Coordinator. Multiple specialist agents provided their findings "
        "for the merchant query below. Synthesize their outputs into a cohesive, beautifully structured "
        "executive response with clear headings and seamless handoffs.\n\n"
        f"Original User Question: {question}\n\n"
        f"Specialist Agent Inputs:\n" + "\n\n".join(pieces)
    )

    synthesized_answer = generate_completion(
        messages=[{"role": "user", "content": synthesis_prompt}],
        system_prompt="Synthesize the multi-agent outputs cleanly and comprehensively.",
        max_tokens=1400,
    )

    return synthesized_answer, sorted(set(sources)), meta


def orchestrate_multi_agent(
    store: VectorStore,
    question: str,
    history: list,
    session_state: dict,
) -> Dict[str, Any]:
    """Main Multi-Agent orchestrator entry point: finds the agent, delegates, and returns."""
    routing = classify_question(question)
    primary = routing.get("primary_agent", "solution_mate")
    reasoning = routing.get("reasoning", "Dispatched to specialist agent.")
    intent = routing.get("intent", "Merchant Inquiry")

    # 1. Collaborative Flow
    if primary == "collaborative":
        collaborators = routing.get("secondary_agents", ["information_escort", "solution_mate"])
        if len(collaborators) < 2:
            collaborators = ["information_escort", "solution_mate"]

        ans_text, sources, meta = handle_collaborative_workflow(
            store, question, history, collaborators, session_state
        )

        collab_info = [
            {
                "id": cid,
                "name": AGENT_REGISTRY.get(cid, {}).get("name", cid),
                "icon": AGENT_REGISTRY.get(cid, {}).get("icon", "🤖"),
                "role": AGENT_REGISTRY.get(cid, {}).get("role", ""),
            }
            for cid in collaborators
            if cid in AGENT_REGISTRY
        ]

        return {
            "answer": ans_text,
            "agent": "collaborative",
            "agent_name": "Multi-Agent Collaboration",
            "agent_icon": "🤝",
            "agent_role": "Coordinated Multi-Agent Synthesis",
            "reasoning": reasoning,
            "intent": intent,
            "collaborating_agents": collab_info,
            "sources": sources,
            "metadata": meta,
        }

    # 2. Individual Agent Delegation
    agent_info = AGENT_REGISTRY.get(primary, AGENT_REGISTRY["solution_mate"])
    sources = []
    meta = {}

    if primary == "information_escort":
        answer_text, sources = answer_question(store, question, history)
    elif primary == "guidance_guru":
        current_goal = session_state.get("goal_state")
        answer_text, goal, sources = answer_guidance(store, question, history, current_goal)
        if goal:
            meta["goal_state"] = goal
    elif primary == "solution_mate":
        current_scenario = session_state.get("solution_analysis")
        answer_text, analysis, sources = answer_solution(store, question, history, current_scenario)
        if analysis:
            meta["solution_analysis"] = analysis
    elif primary == "utility_minion":
        current_draft = session_state.get("utility_draft")
        answer_text, draft = answer_utility(question, history, current_draft)
        if draft:
            meta["utility_draft"] = draft
    else:
        answer_text, sources = answer_question(store, question, history)

    return {
        "answer": answer_text,
        "agent": agent_info["id"],
        "agent_name": agent_info["name"],
        "agent_icon": agent_info["icon"],
        "agent_role": agent_info["role"],
        "tab_id": agent_info["tab_id"],
        "reasoning": reasoning,
        "intent": intent,
        "collaborating_agents": [],
        "sources": sources,
        "metadata": meta,
    }
