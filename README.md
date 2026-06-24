# auto_healer

Auto Healer is a Python service that accepts monitoring events over HTTP and
stores them in SQLite. Events can come from Dynatrace, Splunk, Phoenix, or any
system that can send a JSON `POST`.

Each event is identified by a project id or project name plus a component.

## Run

```bash
uv run auto-healer --host 127.0.0.1 --port 8080 --db auto_healer.sqlite3
```

Open the UI at:

```text
http://127.0.0.1:8080/
```

API documentation:

```text
http://127.0.0.1:8080/docs
http://127.0.0.1:8080/documentation
http://127.0.0.1:8080/openapi.json
```

Configure the Auto Healer endpoint and ADFS authentication at:

```text
http://127.0.0.1:8080/configuration
```

The UI includes:

- mock event generation for Dynatrace, Splunk, Phoenix, and generic systems
- mock scenarios for ADFS error surge, scale up, scale down, and off-hours stop
- payload preview before sending
- presentation metrics for event count, critical events, projects, and sources
- stored event table with project/component filters
- application policy editor for replica limits, holiday stops, and off-hours stops
- endpoint configuration for ADFS client ID, server ID, username, and password

## Send an event

```bash
curl -X POST http://127.0.0.1:8080/events \
  -H 'Content-Type: application/json' \
  -d '{
    "project_id": "checkout",
    "project_name": "Checkout",
    "component": "payments-api",
    "source": "dynatrace",
    "severity": "critical",
    "title": "High latency",
    "message": "p95 latency crossed threshold"
  }'
```

Required fields:

- `component`
- either `project_id`, `projectId`, `pid`, `project_name`, `projectName`, or `project`

Optional fields:

- `source` or `monitoring_system`
- `severity` or `level`
- `title` or `event_name`
- `message` or `description`

The original JSON payload is stored in `raw_payload` so provider-specific fields
are preserved.

## Query events

```bash
curl 'http://127.0.0.1:8080/events?project_id=checkout&component=payments-api'
```

## Save application policy

```bash
curl -X POST http://127.0.0.1:8080/policies \
  -H 'Content-Type: application/json' \
  -d '{
    "project_id": "checkout",
    "project_name": "Checkout",
    "component": "payments-api",
    "min_replicas": 1,
    "max_replicas": 6,
    "scale_up_threshold": 80,
    "scale_down_threshold": 25,
    "stop_during_off_hours": true,
    "off_hours_start": "20:00",
    "off_hours_end": "06:00",
    "stop_during_holidays": true,
    "holiday_calendar": "2026-12-25 Christmas"
  }'
```

## Save endpoint configuration

```bash
curl -X POST http://127.0.0.1:8080/endpoint-config \
  -H 'Content-Type: application/json' \
  -d '{
    "endpoint_url": "https://auto-healer.example.com/api",
    "auth_type": "adfs",
    "adfs_client_id": "auto-healer-ui",
    "adfs_server_id": "urn:auto-healer",
    "adfs_username": "ops.user@example.com",
    "adfs_password": "change-me"
  }'
```

The API returns `password_set` instead of returning the saved password.

## Test

```bash
uv run pytest
```
