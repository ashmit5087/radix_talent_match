"""Optional LLM layer over the deterministic plan (any OpenAI-compatible provider).

Guardrails:
  * Off unless the caller asks AND LLM_BASE_URL/LLM_API_KEY/LLM_MODEL are set.
  * Sends only skill names, categories, statuses and levels - no name, email or evidence text.
  * The model may only rewrite `steps` for actions that already exist and add a short
    narrative. Scores, gains, ordering and the action list stay deterministic.
  * Reply is validated; on ANY failure the deterministic plan is returned with a warning.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from pydantic import BaseModel, Field, ValidationError

from . import config
from .schemas import ImprovementPlan

SYSTEM_PROMPT = (
    "You are a career-readiness coach inside a skill-matching tool. You receive a JSON list of "
    "skill gaps that were computed by code. Rules: (1) Only use the skills listed; never add, "
    "rename or claim the candidate already has a skill. (2) Never state or change any score. "
    "(3) For each action write 2-3 short, concrete, practical steps tailored to the skill and "
    "action_type. (4) Add a 2-3 sentence narrative prioritizing the first actions. "
    'Reply with ONLY JSON: {"narrative": str, "actions": [{"skill_name": str, "steps": [str]}]}.'
)


class _LLMAction(BaseModel):
    skill_name: str
    steps: list[str] = Field(min_length=1, max_length=4)


class _LLMReply(BaseModel):
    narrative: str = Field(max_length=1200)
    actions: list[_LLMAction]


def llm_configured() -> bool:
    return bool(config.LLM_BASE_URL and config.LLM_API_KEY and config.LLM_MODEL)


def _make_client() -> Any:
    from openai import OpenAI  # lazy: only needed when the LLM layer is used

    return OpenAI(base_url=config.LLM_BASE_URL, api_key=config.LLM_API_KEY, timeout=config.LLM_TIMEOUT_S)


def _payload(plan: ImprovementPlan, role: Optional[str]) -> str:
    return json.dumps({
        "target_role": role,
        "actions": [
            {"skill_name": a.skill_name, "category": a.category_code, "action_type": a.action_type,
             "current_status": a.current_status, "critical_gap": a.critical_gap,
             "level_needed": a.level_needed, "score_gain": a.score_gain}
            for a in plan.actions
        ],
    })


def enhance_plan(plan: ImprovementPlan, role: Optional[str] = None, client: Any = None) -> ImprovementPlan:
    """Return the plan with LLM-written steps/narrative, or the original plus a warning."""
    if not plan.actions:
        return plan
    if client is None:
        if not llm_configured():
            plan.warnings.append("LLM not configured (set LLM_BASE_URL, LLM_API_KEY, LLM_MODEL); showing the offline plan.")
            return plan
        try:
            client = _make_client()
        except Exception as exc:  # noqa: BLE001
            plan.warnings.append(f"LLM client unavailable ({type(exc).__name__}); showing the offline plan.")
            return plan
    try:
        completion = client.chat.completions.create(
            model=config.LLM_MODEL or "default",
            messages=[{"role": "system", "content": SYSTEM_PROMPT},
                      {"role": "user", "content": _payload(plan, role)}],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        reply = _LLMReply.model_validate_json(completion.choices[0].message.content)
    except (ValidationError, ValueError, KeyError, IndexError, AttributeError, TypeError) as exc:
        plan.warnings.append(f"LLM reply was not usable ({type(exc).__name__}); showing the offline plan.")
        return plan
    except Exception as exc:  # network, auth, timeout, provider errors
        plan.warnings.append(f"LLM call failed ({type(exc).__name__}); showing the offline plan.")
        return plan

    by_name = {a.skill_name: a for a in reply.actions}
    updated = 0
    for action in plan.actions:  # only existing actions can change, and only their steps
        hit = by_name.get(action.skill_name)
        if hit:
            action.steps = [s.strip() for s in hit.steps if s.strip()] or action.steps
            updated += 1
    plan.narrative = reply.narrative.strip()
    plan.source = "deterministic+llm"
    ignored = len(reply.actions) - updated
    if ignored:
        plan.warnings.append(f"Ignored {ignored} LLM action(s) that did not match a computed gap.")
    return plan
