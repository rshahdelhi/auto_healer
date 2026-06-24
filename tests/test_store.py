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
        }
    )

    assert config.endpoint_url == "https://auto-healer.example.com/api"
    assert config.auth_type == "adfs"
    assert config.password_set is True

    loaded = store.get_endpoint_config()
    assert loaded is not None
    assert loaded.adfs_client_id == "auto-healer-ui"
    assert not hasattr(loaded, "adfs_password")
