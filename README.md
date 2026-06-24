# auto_healer

Auto Healer is a Python service that accepts monitoring events over HTTP and
stores them in SQLite. Events can come from Dynatrace, Splunk, Phoenix, or any
system that can send a JSON `POST`.

Each event is identified by a project id or project name plus a component.

## Run

```bash
uv run auto-healer --host 127.0.0.1 --port 8080 --db auto_healer.sqlite3
```

## Run with Docker

Build the image:

```bash
docker build -t auto-healer .
```

Run the container with a persistent SQLite volume:

```bash
docker run --rm \
  -p 8080:8080 \
  -v auto-healer-data:/data \
  auto-healer
```

Open the dashboard at:

```text
http://127.0.0.1:8080/
```

Open the operator console at:

```text
http://127.0.0.1:8080/console
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
- endpoint configuration for ADFS credentials, retries, and circuit breaker settings
- immutable audit trail for policy/rule and endpoint configuration changes
- SRE blameless postmortem and RCA management

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

## Send Splunk alerts

System error:

```bash
curl -X POST http://127.0.0.1:8080/splunk/alerts \
  -H 'Content-Type: application/json' \
  -d '{
    "search_name": "System Error Surge",
    "sid": "scheduler__admin__search__RMD5",
    "app": "platform",
    "owner": "auto-healer",
    "alert_type": "system_error",
    "result": {
      "project_id": "platform",
      "project_name": "Platform",
      "component": "node-17",
      "host": "node-17",
      "severity": "critical",
      "message": "Root filesystem usage reached 96%",
      "error": "disk_usage_high",
      "filesystem": "/",
      "usage_percent": 96
    }
  }'
```

Application error:

```bash
curl -X POST http://127.0.0.1:8080/splunk/alerts \
  -H 'Content-Type: application/json' \
  -d '{
    "search_name": "Application Error Surge",
    "sid": "scheduler__admin__search__RMD6",
    "app": "checkout",
    "owner": "auto-healer",
    "alert_type": "application_error",
    "result": {
      "project_id": "checkout",
      "project_name": "Checkout",
      "component": "payments-api",
      "severity": "critical",
      "message": "Payment authorization exceptions crossed threshold",
      "exception": "PaymentAuthorizationException",
      "error_count": 148,
      "error_rate_percent": 18
    }
  }'
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
    "adfs_password": "change-me",
    "retry_enabled": true,
    "max_retry_attempts": 3,
    "retry_backoff_seconds": 2,
    "circuit_breaker_enabled": true,
    "circuit_breaker_failure_threshold": 5,
    "circuit_breaker_reset_timeout_seconds": 60
  }'
```

The API returns `password_set` instead of returning the saved password.

## Query audit trail

```bash
curl 'http://127.0.0.1:8080/audit-log?entity_type=policy&limit=25'
```

Audit entries are append-only records in SQLite. Database triggers reject updates
and deletes on `audit_log`.

## Save blameless postmortem and RCA

```bash
curl -X POST http://127.0.0.1:8080/postmortems \
  -H 'Content-Type: application/json' \
  -d '{
    "incident_id": "INC-2026-0001",
    "project_id": "checkout",
    "project_name": "Checkout",
    "component": "payments-api",
    "title": "Payment authorization error surge",
    "severity": "critical",
    "status": "draft",
    "owner": "sre-team",
    "summary": "Payment authorization failures increased for a subset of users.",
    "impact": "Checkout conversion dropped during the incident window.",
    "root_cause": "Downstream payment provider timeout caused retry amplification.",
    "corrective_actions": "Tune retries, add circuit breaker, update runbook.",
    "lessons_learned": "Retries need per-provider budgets."
  }'
```

## Test

```bash
uv run pytest
```
