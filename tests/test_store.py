import sqlite3

from auto_healer import EventStore


def test_create_event_saves_monitoring_payload(tmp_path):
    store = EventStore(tmp_path / "events.sqlite3")

    event = store.create_event(
        {
            "project_id": "checkout",
            "project_name": "Checkout",
            "component": "payments-api",
            "source": "dynatrace",
            "severity": "critical",
            "title": "High latency",
            "message": "p95 latency crossed threshold",
            "dt_event_id": "abc-123",
        }
    )

    assert event.id == 1
    assert event.project_id == "checkout"
    assert event.project_name == "Checkout"
    assert event.component == "payments-api"
    assert event.source == "dynatrace"

    stored_events = store.list_events(project_id="checkout", component="payments-api")
    assert len(stored_events) == 1
    assert stored_events[0].raw_payload["dt_event_id"] == "abc-123"


def test_create_event_requires_project_identifier(tmp_path):
    store = EventStore(tmp_path / "events.sqlite3")

    try:
        store.create_event({"component": "payments-api"})
    except ValueError as exc:
        assert str(exc) == "project_id or project_name is required"
    else:
        raise AssertionError("expected missing project identifier to fail")


def test_create_event_accepts_common_project_aliases(tmp_path):
    store = EventStore(tmp_path / "events.sqlite3")

    event = store.create_event(
        {
            "project": "Phoenix",
            "component": "search-worker",
            "monitoring_system": "splunk",
        }
    )

    assert event.project_name == "Phoenix"
    assert event.source == "splunk"


def test_upsert_policy_saves_scale_and_schedule_settings(tmp_path):
    store = EventStore(tmp_path / "events.sqlite3")

    policy = store.upsert_policy(
        {
            "project_id": "checkout",
            "project_name": "Checkout",
            "component": "payments-api",
            "min_replicas": 1,
            "max_replicas": 6,
            "scale_up_threshold": 80,
            "scale_down_threshold": 25,
            "stop_during_off_hours": True,
            "off_hours_start": "20:00",
            "off_hours_end": "06:00",
            "stop_during_holidays": True,
            "holiday_calendar": "2026-12-25 Christmas",
        }
    )

    assert policy.project_id == "checkout"
    assert policy.component == "payments-api"
    assert policy.max_replicas == 6
    assert policy.stop_during_off_hours is True
    assert policy.stop_during_holidays is True

    policies = store.list_policies(project_id="checkout")
    assert len(policies) == 1
    assert policies[0].holiday_calendar == "2026-12-25 Christmas"

    audit_entries = store.list_audit_entries(entity_type="policy")
    assert len(audit_entries) == 1
    assert audit_entries[0].action == "created"
    assert audit_entries[0].details["max_replicas"] == 6


def test_upsert_policy_audits_updates(tmp_path):
    store = EventStore(tmp_path / "events.sqlite3")
    payload = {
        "project_id": "checkout",
        "project_name": "Checkout",
        "component": "payments-api",
        "min_replicas": 1,
        "max_replicas": 6,
    }

    store.upsert_policy(payload)
    store.upsert_policy({**payload, "max_replicas": 8})

    audit_entries = store.list_audit_entries(entity_type="policy")
    assert [entry.action for entry in audit_entries] == ["updated", "created"]
    assert audit_entries[0].details["max_replicas"] == 8


def test_audit_entries_are_database_immutable(tmp_path):
    db_path = tmp_path / "events.sqlite3"
    store = EventStore(db_path)
    audit_entry = store.record_audit(
        entity_type="policy",
        entity_id="checkout:payments-api",
        action="created",
        summary="Policy created",
        details={"max_replicas": 6},
    )

    with sqlite3.connect(db_path) as conn:
        try:
            conn.execute(
                "UPDATE audit_log SET summary = ? WHERE id = ?",
                ("changed", audit_entry.id),
            )
        except sqlite3.IntegrityError as exc:
            assert str(exc) == "audit_log records are immutable"
        else:
            raise AssertionError("expected audit_log update to be rejected")

        try:
            conn.execute("DELETE FROM audit_log WHERE id = ?", (audit_entry.id,))
        except sqlite3.IntegrityError as exc:
            assert str(exc) == "audit_log records are immutable"
        else:
            raise AssertionError("expected audit_log delete to be rejected")

    audit_entries = store.list_audit_entries()
    assert len(audit_entries) == 1
    assert audit_entries[0].summary == "Policy created"


def test_save_endpoint_config_masks_password(tmp_path):
    store = EventStore(tmp_path / "events.sqlite3")

    config = store.save_endpoint_config(
        {
            "endpoint_url": "https://auto-healer.example.com/api",
            "auth_type": "adfs",
            "adfs_client_id": "auto-healer-ui",
            "adfs_server_id": "urn:auto-healer",
            "adfs_username": "ops.user@example.com",
            "adfs_password": "secret",
            "retry_enabled": True,
            "max_retry_attempts": 4,
            "retry_backoff_seconds": 1,
            "circuit_breaker_enabled": True,
            "circuit_breaker_failure_threshold": 2,
            "circuit_breaker_reset_timeout_seconds": 30,
        }
    )

    assert config.endpoint_url == "https://auto-healer.example.com/api"
    assert config.auth_type == "adfs"
    assert config.password_set is True
    assert config.retry_enabled is True
    assert config.max_retry_attempts == 4
    assert config.retry_backoff_seconds == 1
    assert config.circuit_breaker_enabled is True
    assert config.circuit_breaker_failure_threshold == 2
    assert config.circuit_breaker_reset_timeout_seconds == 30

    loaded = store.get_endpoint_config()
    assert loaded is not None
    assert loaded.adfs_client_id == "auto-healer-ui"
    assert loaded.max_retry_attempts == 4
    assert not hasattr(loaded, "adfs_password")

    audit_entries = store.list_audit_entries(entity_type="endpoint_config")
    assert len(audit_entries) == 1
    assert audit_entries[0].action == "created"
    assert audit_entries[0].details["password_set"] is True
    assert audit_entries[0].details["max_retry_attempts"] == 4
    assert "adfs_password" not in audit_entries[0].details


def test_upsert_postmortem_saves_rca_and_audits(tmp_path):
    store = EventStore(tmp_path / "events.sqlite3")

    postmortem = store.upsert_postmortem(
        {
            "incident_id": "INC-2026-0001",
            "project_id": "checkout",
            "project_name": "Checkout",
            "component": "payments-api",
            "title": "Payment authorization error surge",
            "severity": "critical",
            "status": "draft",
            "owner": "sre-team",
            "summary": "Payment authorization failures increased.",
            "impact": "Checkout conversion dropped.",
            "root_cause": "Payment provider timeout caused retry amplification.",
            "corrective_actions": "Tune retries and add circuit breaker.",
            "lessons_learned": "Retries need per-provider budgets.",
        }
    )

    assert postmortem.incident_id == "INC-2026-0001"
    assert postmortem.status == "draft"
    assert postmortem.root_cause == "Payment provider timeout caused retry amplification."

    stored = store.list_postmortems(project_id="checkout")
    assert len(stored) == 1
    assert stored[0].owner == "sre-team"

    audit_entries = store.list_audit_entries(entity_type="postmortem")
    assert len(audit_entries) == 1
    assert audit_entries[0].action == "created"
    assert audit_entries[0].details["incident_id"] == "INC-2026-0001"
