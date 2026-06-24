from __future__ import annotations

import argparse
import json
from importlib import resources
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from auto_healer.openapi import build_openapi_schema
from auto_healer.store import AppPolicy, EndpointConfig, Event, EventStore

DEFAULT_DB_PATH = "auto_healer.sqlite3"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8080


def create_handler(store: EventStore) -> type[BaseHTTPRequestHandler]:
    class AutoHealerRequestHandler(BaseHTTPRequestHandler):
        server_version = "AutoHealer/0.1"

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path in ("/", "/index.html"):
                self._send_static("index.html", "text/html; charset=utf-8")
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

            self._send_error(HTTPStatus.NOT_FOUND, "not found")

        def do_POST(self) -> None:
            path = urlparse(self.path).path
            if path not in {"/events", "/policies", "/endpoint-config"}:
                self._send_error(HTTPStatus.NOT_FOUND, "not found")
                return

            try:
                payload = self._read_json_body()
                if path == "/events":
                    event = store.create_event(payload)
                    self._send_json(_event_to_dict(event), status=HTTPStatus.CREATED)
                    return

                if path == "/policies":
                    policy = store.upsert_policy(payload)
                    self._send_json(_policy_to_dict(policy), status=HTTPStatus.CREATED)
                    return

                config = store.save_endpoint_config(payload)
                self._send_json(_config_to_dict(config), status=HTTPStatus.CREATED)
                return
            except ValueError as exc:
                self._send_error(HTTPStatus.BAD_REQUEST, str(exc))
                return
            except json.JSONDecodeError:
                self._send_error(HTTPStatus.BAD_REQUEST, "request body must be valid JSON")
                return

        def log_message(self, format: str, *args: Any) -> None:
            return

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
    store = EventStore(db_path)
    server = ThreadingHTTPServer((host, port), create_handler(store))
    print(f"Auto Healer listening on http://{host}:{port}")
    print(f"Saving events to {db_path}")
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
        "updated_at": config.updated_at,
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
