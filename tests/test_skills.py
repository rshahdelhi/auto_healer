from auto_healer.skills import run_skill
from auto_healer.store import EventStore


def test_run_skill_defaults_to_dry_run_and_records_audit(tmp_path):
    store = EventStore(tmp_path / "events.sqlite3")

    execution = run_skill(
        store,
        {
            "skill": "scale_up",
            "project_id": "checkout",
            "component": "payments-api",
            "current_replicas": 2,
            "max_replicas": 6,
            "event_id": 42,
        },
    )

    assert execution.status == "dry_run"
    assert execution.dry_run is True
    assert execution.proposal["target_replicas"] == 3
    assert execution.evidence["event_id"] == 42

    audit_entries = store.list_audit_entries(entity_type="skill_execution")
    assert len(audit_entries) == 1
    assert audit_entries[0].action == "dry_run"
    assert audit_entries[0].details["proposal"]["target_replicas"] == 3


def test_non_dry_run_requires_approval(tmp_path):
    store = EventStore(tmp_path / "events.sqlite3")

    execution = run_skill(
        store,
        {
            "skill": "restart_component",
            "project_id": "checkout",
            "component": "payments-api",
            "dry_run": False,
            "autonomy_level": 2,
        },
    )

    assert execution.status == "requires_approval"
    assert execution.risk_level == "medium"


def test_skill_guardrail_blocks_excessive_autonomy(tmp_path):
    store = EventStore(tmp_path / "events.sqlite3")

    execution = run_skill(
        store,
        {
            "skill": "scale_up",
            "project_id": "checkout",
            "component": "payments-api",
            "dry_run": False,
            "approved": True,
            "autonomy_level": 3,
        },
    )

    assert execution.status == "blocked"
    assert execution.reason == "requested autonomy level exceeds the skill guardrail"
