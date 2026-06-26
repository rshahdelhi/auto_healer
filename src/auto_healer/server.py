from __future__ import annotations

import argparse
import json
import logging
from importlib import resources
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from auto_healer.openapi import build_openapi_schema
from auto_healer.skills import list_skills, run_skill
from auto_healer.store import (
    AppPolicy,
    AuditEntry,
    EndpointConfig,
    Event,
    EventStore,
    Postmortem,
    SkillExecution,
)
from auto_healer.telemetry import configure_telemetry, start_span

DEFAULT_DB_PATH = "auto_healer.sqlite3"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8080

logger = logging.getLogger("auto_healer")


def create_handler(store: EventStore) -> type[BaseHTTPRequestHandler]:
    class AutoHealerRequestHandler(BaseHTTPRequestHandler):
        server_version = "AutoHealer/0.1"

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path in ("/", "/index.html"):
                self._send_static("index.html", "text/html; charset=utf-8")
                return

            if parsed.path == "/console":
                self._send_static("console.html", "text/html; charset=utf-8")
                return

            if parsed.path == "/app.css":
                self._send_static("app.css", "text/css; charset=utf-8")
                return

            if parsed.path == "/app.js":
                self._send_static("app.js", "text/javascript; charset=utf-8")
                return

            if parsed.path == "/configuration":
                self._send_static("configuration.html", "text/html; charset=utf-8")
                return

            if parsed.path == "/configuration.js":
                self._send_static("configuration.js", "text/javascript; charset=utf-8")
                return

            if parsed.path == "/docs":
                self._send_static("swagger.html", "text/html; charset=utf-8")
                return

            if parsed.path == "/documentation":
                self._send_static("docs.html", "text/html; charset=utf-8")
                return

            if parsed.path == "/docs.css":
                self._send_static("docs.css", "text/css; charset=utf-8")
                return

            if parsed.path == "/openapi.json":
                self._send_json(build_openapi_schema(), cache=False)
                return

            if parsed.path == "/health":
                self._send_json({"status": "ok"})
                return

            if parsed.path == "/events":
                params = parse_qs(parsed.query)
                events = store.list_events(
                    project_id=_first(params, "project_id"),
                    project_name=_first(params, "project_name"),
                    component=_first(params, "component"),
                    limit=_int_param(params, "limit", default=100),
                )
                self._send_json({"events": [_event_to_dict(event) for event in events]})
                return

            if parsed.path == "/policies":
                params = parse_qs(parsed.query)
                policies = store.list_policies(
                    project_id=_first(params, "project_id"),
                    project_name=_first(params, "project_name"),
                    component=_first(params, "component"),
                    limit=_int_param(params, "limit", default=100),
                )
                self._send_json(
                    {"policies": [_policy_to_dict(policy) for policy in policies]}
                )
                return

            if parsed.path == "/endpoint-config":
                config = store.get_endpoint_config()
                self._send_json({"config": _config_to_dict(config)})
                return

            if parsed.path == "/audit-log":
                params = parse_qs(parsed.query)
                audit_entries = store.list_audit_entries(
                    entity_type=_first(params, "entity_type"),
                    entity_id=_first(params, "entity_id"),
                    limit=_int_param(params, "limit", default=100),
                )
                self._send_json(
                    {"audit_log": [_audit_entry_to_dict(entry) for entry in audit_entries]}
                )
                return

            if parsed.path == "/postmortems":
                params = parse_qs(parsed.query)
                postmortems = store.list_postmortems(
                    incident_id=_first(params, "incident_id"),
                    project_id=_first(params, "project_id"),
                    project_name=_first(params, "project_name"),
                    component=_first(params, "component"),
                    status=_first(params, "status"),
                    limit=_int_param(params, "limit", default=100),
                )
                self._send_json(
                    {
                        "postmortems": [
                            _postmortem_to_dict(postmortem)
                            for postmortem in postmortems
                        ]
                    }
                )
                return

            if parsed.path == "/skills":
                self._send_json({"skills": [_skill_to_dict(skill) for skill in list_skills()]})
                return

            if parsed.path == "/skill-executions":
                params = parse_qs(parsed.query)
                executions = store.list_skill_executions(
                    skill_name=_first(params, "skill_name"),
                    project_id=_first(params, "project_id"),
                    project_name=_first(params, "project_name"),
                    component=_first(params, "component"),
                    status=_first(params, "status"),
                    limit=_int_param(params, "limit", default=100),
                )
                self._send_json(
                    {
                        "skill_executions": [
                            _skill_execution_to_dict(execution)
                            for execution in executions
                        ]
                    }
                )
                return

            self._send_error(HTTPStatus.NOT_FOUND, "not found")

        def do_POST(self) -> None:
            path = urlparse(self.path).path
            if path not in {
                "/events",
                "/splunk/alerts",
                "/policies",
                "/endpoint-config",
                "/postmortems",
                "/skills/run",
            }:
                self._send_error(HTTPStatus.NOT_FOUND, "not found")
                return

            try:
                payload = self._read_json_body()
                if path == "/skills/run":
                    execution = run_skill(store, payload)
                    logger.info(
                        "skill_execution id=%s skill=%s project=%s component=%s status=%s dry_run=%s",
                        execution.id,
                        execution.skill_name,
                        execution.project_id or execution.project_name,
                        execution.component,
                        execution.status,
                        execution.dry_run,
                    )
                    self._send_json(
                        _skill_execution_to_dict(execution),
                        status=HTTPStatus.CREATED,
                    )
                    return

                if path == "/events":
                    with start_span("auto_healer.event.create", source=payload.get("source")):
                        event = store.create_event(payload)
                    logger.info(
                        "event_ingested id=%s project=%s component=%s source=%s",
                        event.id,
                        event.project_id or event.project_name,
                        event.component,
                        event.source,
                    )
                    self._send_json(_event_to_dict(event), status=HTTPStatus.CREATED)
                    return

                if path == "/splunk/alerts":
                    event = store.create_event(_normalize_splunk_alert(payload))
                    logger.info(
                        "splunk_alert_ingested id=%s project=%s component=%s severity=%s",
                        event.id,
                        event.project_id or event.project_name,
                        event.component,
                        event.severity,
                    )
                    self._send_json(_event_to_dict(event), status=HTTPStatus.CREATED)
                    return

                if path == "/policies":
                    policy = store.upsert_policy(payload)
                    logger.info(
                        "policy_saved id=%s project=%s component=%s",
                        policy.id,
                        policy.project_id or policy.project_name,
                        policy.component,
                    )
                    self._send_json(_policy_to_dict(policy), status=HTTPStatus.CREATED)
                    return

                if path == "/postmortems":
                    postmortem = store.upsert_postmortem(payload)
                    logger.info(
                        "postmortem_saved incident_id=%s project=%s component=%s status=%s",
                        postmortem.incident_id,
                        postmortem.project_id or postmortem.project_name,
                        postmortem.component,
                        postmortem.status,
                    )
                    self._send_json(
                        _postmortem_to_dict(postmortem),
                        status=HTTPStatus.CREATED,
                    )
                    return

                config = store.save_endpoint_config(payload)
                logger.info(
                    "endpoint_config_saved endpoint_url=%s auth_type=%s username=%s",
                    config.endpoint_url,
                    config.auth_type,
                    config.adfs_username,
                )
                self._send_json(_config_to_dict(config), status=HTTPStatus.CREATED)
                return
            except ValueError as exc:
                logger.warning("bad_request path=%s error=%s", path, exc)
                self._send_error(HTTPStatus.BAD_REQUEST, str(exc))
                return
            except json.JSONDecodeError:
                logger.warning("bad_request path=%s error=invalid_json", path)
                self._send_error(HTTPStatus.BAD_REQUEST, "request body must be valid JSON")
                return

        def log_message(self, format: str, *args: Any) -> None:
            logger.info(
                "http_request client=%s message=%s",
                self.client_address[0],
                format % args,
            )

        def _read_json_body(self) -> dict[str, Any]:
            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length == 0:
                raise ValueError("request body is required")

            body = self.rfile.read(content_length)
            payload = json.loads(body.decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("request body must be a JSON object")
            return payload

        def _send_json(
            self,
            payload: dict[str, Any],
            *,
            status: HTTPStatus = HTTPStatus.OK,
            cache: bool = True,
        ) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            if not cache:
                self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_error(self, status: HTTPStatus, message: str) -> None:
            self._send_json({"error": message}, status=status)

        def _send_static(self, filename: str, content_type: str) -> None:
            static_root = resources.files("auto_healer.static")
            body = static_root.joinpath(filename).read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return AutoHealerRequestHandler


def run_server(
    *,
    db_path: str = DEFAULT_DB_PATH,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    configure_telemetry()
    store = EventStore(db_path)
    server = ThreadingHTTPServer((host, port), create_handler(store))
    logger.info("auto_healer_listening url=http://%s:%s db_path=%s", host, port, db_path)
    server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Accept monitoring events and store them in SQLite."
    )
    parser.add_argument("--db", default=DEFAULT_DB_PATH, help="SQLite database path")
    parser.add_argument("--host", default=DEFAULT_HOST, help="HTTP bind host")
    parser.add_argument("--port", default=DEFAULT_PORT, type=int, help="HTTP bind port")
    args = parser.parse_args()

    run_server(db_path=args.db, host=args.host, port=args.port)


def _event_to_dict(event: Event) -> dict[str, Any]:
    return {
        "id": event.id,
        "project_id": event.project_id,
        "project_name": event.project_name,
        "component": event.component,
        "source": event.source,
        "severity": event.severity,
        "title": event.title,
        "message": event.message,
        "raw_payload": event.raw_payload,
        "created_at": event.created_at,
    }


def _normalize_splunk_alert(payload: dict[str, Any]) -> dict[str, Any]:
    result = payload.get("result")
    result_fields = result if isinstance(result, dict) else {}

    project_id = (
        payload.get("project_id")
        or payload.get("projectId")
        or result_fields.get("project_id")
        or result_fields.get("projectId")
        or result_fields.get("service")
        or payload.get("app")
    )
    project_name = (
        payload.get("project_name")
        or payload.get("projectName")
        or result_fields.get("project_name")
        or result_fields.get("projectName")
        or result_fields.get("application")
    )
    component = (
        payload.get("component")
        or result_fields.get("component")
        or result_fields.get("host")
        or result_fields.get("source")
        or payload.get("search_name")
    )
    severity = (
        payload.get("severity")
        or payload.get("level")
        or result_fields.get("severity")
        or result_fields.get("level")
        or result_fields.get("priority")
        or "warning"
    )
    title = payload.get("title") or payload.get("search_name") or "Splunk alert"
    message = (
        payload.get("message")
        or payload.get("description")
        or result_fields.get("message")
        or result_fields.get("error")
        or result_fields.get("exception")
        or title
    )

    normalized = {
        **payload,
        "project_id": project_id,
        "project_name": project_name,
        "component": component,
        "source": "splunk",
        "severity": severity,
        "title": title,
        "message": message,
        "monitoring_system": "splunk",
        "splunk_alert_type": payload.get("alert_type")
        or result_fields.get("alert_type")
        or "unknown",
    }
    return {key: value for key, value in normalized.items() if value is not None}


def _policy_to_dict(policy: AppPolicy) -> dict[str, Any]:
    return {
        "id": policy.id,
        "project_id": policy.project_id,
        "project_name": policy.project_name,
        "component": policy.component,
        "min_replicas": policy.min_replicas,
        "max_replicas": policy.max_replicas,
        "scale_up_threshold": policy.scale_up_threshold,
        "scale_down_threshold": policy.scale_down_threshold,
        "stop_during_off_hours": policy.stop_during_off_hours,
        "off_hours_start": policy.off_hours_start,
        "off_hours_end": policy.off_hours_end,
        "stop_during_holidays": policy.stop_during_holidays,
        "holiday_calendar": policy.holiday_calendar,
        "updated_at": policy.updated_at,
    }


def _postmortem_to_dict(postmortem: Postmortem) -> dict[str, Any]:
    return {
        "id": postmortem.id,
        "incident_id": postmortem.incident_id,
        "project_id": postmortem.project_id,
        "project_name": postmortem.project_name,
        "component": postmortem.component,
        "title": postmortem.title,
        "severity": postmortem.severity,
        "status": postmortem.status,
        "owner": postmortem.owner,
        "summary": postmortem.summary,
        "impact": postmortem.impact,
        "root_cause": postmortem.root_cause,
        "corrective_actions": postmortem.corrective_actions,
        "lessons_learned": postmortem.lessons_learned,
        "created_at": postmortem.created_at,
        "updated_at": postmortem.updated_at,
    }


def _skill_to_dict(skill: Any) -> dict[str, Any]:
    return {
        "name": skill.name,
        "description": skill.description,
        "max_autonomy_level": int(skill.max_autonomy_level),
    }


def _skill_execution_to_dict(execution: SkillExecution) -> dict[str, Any]:
    return {
        "id": execution.id,
        "skill_name": execution.skill_name,
        "project_id": execution.project_id,
        "project_name": execution.project_name,
        "component": execution.component,
        "autonomy_level": execution.autonomy_level,
        "dry_run": execution.dry_run,
        "approved": execution.approved,
        "risk_level": execution.risk_level,
        "status": execution.status,
        "reason": execution.reason,
        "proposal": execution.proposal,
        "evidence": execution.evidence,
        "created_at": execution.created_at,
    }


def _config_to_dict(config: EndpointConfig | None) -> dict[str, Any] | None:
    if config is None:
        return None
    return {
        "id": config.id,
        "endpoint_url": config.endpoint_url,
        "auth_type": config.auth_type,
        "adfs_client_id": config.adfs_client_id,
        "adfs_server_id": config.adfs_server_id,
        "adfs_username": config.adfs_username,
        "password_set": config.password_set,
        "retry_enabled": config.retry_enabled,
        "max_retry_attempts": config.max_retry_attempts,
        "retry_backoff_seconds": config.retry_backoff_seconds,
        "circuit_breaker_enabled": config.circuit_breaker_enabled,
        "circuit_breaker_failure_threshold": config.circuit_breaker_failure_threshold,
        "circuit_breaker_reset_timeout_seconds": (
            config.circuit_breaker_reset_timeout_seconds
        ),
        "updated_at": config.updated_at,
    }


def _audit_entry_to_dict(entry: AuditEntry) -> dict[str, Any]:
    return {
        "id": entry.id,
        "entity_type": entry.entity_type,
        "entity_id": entry.entity_id,
        "action": entry.action,
        "summary": entry.summary,
        "details": entry.details,
        "created_at": entry.created_at,
    }


def _first(params: dict[str, list[str]], key: str) -> str | None:
    values = params.get(key, [])
    return values[0] if values else None


def _int_param(params: dict[str, list[str]], key: str, *, default: int) -> int:
    value = _first(params, key)
    if value is None:
        return default

    try:
        return max(1, min(int(value), 500))
    except ValueError:
        return default
