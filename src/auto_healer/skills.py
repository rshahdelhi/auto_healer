from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Callable

from auto_healer.store import EventStore, SkillExecution
from auto_healer.telemetry import start_span


class AutonomyLevel(IntEnum):
    L0_MANUAL = 0
    L1_ASSISTED = 1
    L2_HUMAN_APPROVED = 2
    L3_BOUNDED_AUTONOMY = 3
    L4_FULL_AUTONOMY = 4


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    max_autonomy_level: AutonomyLevel
    handler: Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class RiskDecision:
    level: str
    status: str
    reason: str


def list_skills() -> list[Skill]:
    return list(_SKILLS.values())


def get_skill(name: str) -> Skill:
    try:
        return _SKILLS[name]
    except KeyError:
        raise ValueError(f"unknown skill: {name}") from None


def run_skill(store: EventStore, payload: dict[str, Any]) -> SkillExecution:
    skill_name = _required_text(payload, "skill")
    skill = get_skill(skill_name)
    project_id = _optional_text(payload.get("project_id") or payload.get("projectId"))
    project_name = _optional_text(
        payload.get("project_name") or payload.get("projectName") or payload.get("project")
    )
    component = _required_text(payload, "component")
    dry_run = _bool_value(payload.get("dry_run", True))
    approved = _bool_value(payload.get("approved", False))
    autonomy_level = _autonomy_level(payload.get("autonomy_level", 1))

    if not project_id and not project_name:
        raise ValueError("project_id or project_name is required")

    with start_span(
        "auto_healer.skill.run",
        skill_name=skill.name,
        component=component,
        dry_run=dry_run,
        autonomy_level=int(autonomy_level),
    ):
        proposal_input = {
            **payload,
            "project_id": project_id,
            "project_name": project_name,
            "component": component,
        }
        proposal = skill.handler(proposal_input)
        decision = _risk_decision(
            skill=skill,
            proposal=proposal,
            dry_run=dry_run,
            approved=approved,
            autonomy_level=autonomy_level,
        )
        evidence = _evidence(payload)
        return store.record_skill_execution(
            skill_name=skill.name,
            project_id=project_id,
            project_name=project_name,
            component=component,
            autonomy_level=int(autonomy_level),
            dry_run=dry_run,
            approved=approved,
            risk_level=decision.level,
            status=decision.status,
            reason=decision.reason,
            proposal=proposal,
            evidence=evidence,
        )


def _scale_up(payload: dict[str, Any]) -> dict[str, Any]:
    current = _int_value(payload.get("current_replicas"), default=1)
    increment = max(1, _int_value(payload.get("increment"), default=1))
    max_replicas = _int_value(payload.get("max_replicas"), default=max(current + increment, 2))
    target = min(current + increment, max_replicas)
    return {
        "action": "scale",
        "direction": "up",
        "current_replicas": current,
        "target_replicas": target,
        "blast_radius": "single_component",
        "rollback": {"action": "scale", "target_replicas": current},
    }


def _scale_down(payload: dict[str, Any]) -> dict[str, Any]:
    current = _int_value(payload.get("current_replicas"), default=2)
    decrement = max(1, _int_value(payload.get("decrement"), default=1))
    min_replicas = _int_value(payload.get("min_replicas"), default=1)
    target = max(current - decrement, min_replicas)
    return {
        "action": "scale",
        "direction": "down",
        "current_replicas": current,
        "target_replicas": target,
        "blast_radius": "single_component",
        "rollback": {"action": "scale", "target_replicas": current},
    }


def _restart_component(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "action": "restart",
        "strategy": payload.get("strategy") or "rolling",
        "blast_radius": "single_component",
        "rollback": {"action": "halt_restart"},
    }


def _risk_decision(
    *,
    skill: Skill,
    proposal: dict[str, Any],
    dry_run: bool,
    approved: bool,
    autonomy_level: AutonomyLevel,
) -> RiskDecision:
    if autonomy_level > skill.max_autonomy_level:
        return RiskDecision(
            level="high",
            status="blocked",
            reason="requested autonomy level exceeds the skill guardrail",
        )
    if dry_run:
        return RiskDecision(
            level=_risk_level(proposal),
            status="dry_run",
            reason="dry-run proposal generated without production mutation",
        )
    if autonomy_level <= AutonomyLevel.L2_HUMAN_APPROVED and not approved:
        return RiskDecision(
            level="medium",
            status="requires_approval",
            reason="non-dry-run execution requires explicit approval",
        )
    return RiskDecision(
        level=_risk_level(proposal),
        status="approved",
        reason="proposal passed guardrails and was explicitly approved",
    )


def _risk_level(proposal: dict[str, Any]) -> str:
    if proposal.get("action") == "restart":
        return "medium"
    if proposal.get("direction") == "down":
        return "medium"
    return "low"


def _evidence(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: payload[key]
        for key in ("event_id", "incident_id", "source", "severity", "reason")
        if key in payload
    }


def _autonomy_level(value: object) -> AutonomyLevel:
    try:
        return AutonomyLevel(int(value))
    except (TypeError, ValueError):
        raise ValueError("autonomy_level must be an integer from 0 to 4") from None


def _required_text(payload: dict[str, Any], key: str) -> str:
    value = _optional_text(payload.get(key))
    if not value:
        raise ValueError(f"{key} is required")
    return value


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _int_value(value: object, *, default: int) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _bool_value(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


_SKILLS = {
    skill.name: skill
    for skill in (
        Skill(
            name="scale_up",
            description="Propose increasing replicas for one component.",
            max_autonomy_level=AutonomyLevel.L2_HUMAN_APPROVED,
            handler=_scale_up,
        ),
        Skill(
            name="scale_down",
            description="Propose decreasing replicas for one component within limits.",
            max_autonomy_level=AutonomyLevel.L2_HUMAN_APPROVED,
            handler=_scale_down,
        ),
        Skill(
            name="restart_component",
            description="Propose a rolling restart for one component.",
            max_autonomy_level=AutonomyLevel.L2_HUMAN_APPROVED,
            handler=_restart_component,
        ),
    )
}
