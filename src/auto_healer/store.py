from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Event:
    id: int
    project_id: str | None
    project_name: str | None
    component: str
    source: str
    severity: str | None
    title: str | None
    message: str | None
    raw_payload: dict[str, Any]
    created_at: str


@dataclass(frozen=True)
class AppPolicy:
    id: int
    project_id: str | None
    project_name: str | None
    component: str
    min_replicas: int
    max_replicas: int
    scale_up_threshold: int
    scale_down_threshold: int
    stop_during_off_hours: bool
    off_hours_start: str | None
    off_hours_end: str | None
    stop_during_holidays: bool
    holiday_calendar: str | None
    updated_at: str


@dataclass(frozen=True)
class EndpointConfig:
    id: int
    endpoint_url: str
    auth_type: str
    adfs_client_id: str
    adfs_server_id: str
    adfs_username: str
    password_set: bool
    retry_enabled: bool
    max_retry_attempts: int
    retry_backoff_seconds: int
    circuit_breaker_enabled: bool
    circuit_breaker_failure_threshold: int
    circuit_breaker_reset_timeout_seconds: int
    updated_at: str


@dataclass(frozen=True)
class AuditEntry:
    id: int
    entity_type: str
    entity_id: str
    action: str
    summary: str
    details: dict[str, Any]
    created_at: str


@dataclass(frozen=True)
class Postmortem:
    id: int
    incident_id: str
    project_id: str | None
    project_name: str | None
    component: str
    title: str
    severity: str | None
    status: str
    owner: str | None
    summary: str | None
    impact: str | None
    root_cause: str | None
    corrective_actions: str | None
    lessons_learned: str | None
    created_at: str
    updated_at: str


class EventStore:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        self.initialize()

    def initialize(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT,
                    project_name TEXT,
                    component TEXT NOT NULL,
                    source TEXT NOT NULL,
                    severity TEXT,
                    title TEXT,
                    message TEXT,
                    raw_payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_events_project_component
                ON events(project_id, project_name, component)
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS policies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT,
                    project_name TEXT,
                    component TEXT NOT NULL,
                    min_replicas INTEGER NOT NULL,
                    max_replicas INTEGER NOT NULL,
                    scale_up_threshold INTEGER NOT NULL,
                    scale_down_threshold INTEGER NOT NULL,
                    stop_during_off_hours INTEGER NOT NULL,
                    off_hours_start TEXT,
                    off_hours_end TEXT,
                    stop_during_holidays INTEGER NOT NULL,
                    holiday_calendar TEXT,
                    updated_at TEXT NOT NULL,
                    UNIQUE(project_id, project_name, component)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS endpoint_config (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    endpoint_url TEXT NOT NULL,
                    auth_type TEXT NOT NULL,
                    adfs_client_id TEXT NOT NULL,
                    adfs_server_id TEXT NOT NULL,
                    adfs_username TEXT NOT NULL,
                    adfs_password TEXT NOT NULL,
                    retry_enabled INTEGER NOT NULL DEFAULT 1,
                    max_retry_attempts INTEGER NOT NULL DEFAULT 3,
                    retry_backoff_seconds INTEGER NOT NULL DEFAULT 2,
                    circuit_breaker_enabled INTEGER NOT NULL DEFAULT 1,
                    circuit_breaker_failure_threshold INTEGER NOT NULL DEFAULT 5,
                    circuit_breaker_reset_timeout_seconds INTEGER NOT NULL DEFAULT 60,
                    updated_at TEXT NOT NULL
                )
                """
            )
            _ensure_column(conn, "endpoint_config", "retry_enabled", "INTEGER NOT NULL DEFAULT 1")
            _ensure_column(conn, "endpoint_config", "max_retry_attempts", "INTEGER NOT NULL DEFAULT 3")
            _ensure_column(conn, "endpoint_config", "retry_backoff_seconds", "INTEGER NOT NULL DEFAULT 2")
            _ensure_column(conn, "endpoint_config", "circuit_breaker_enabled", "INTEGER NOT NULL DEFAULT 1")
            _ensure_column(
                conn,
                "endpoint_config",
                "circuit_breaker_failure_threshold",
                "INTEGER NOT NULL DEFAULT 5",
            )
            _ensure_column(
                conn,
                "endpoint_config",
                "circuit_breaker_reset_timeout_seconds",
                "INTEGER NOT NULL DEFAULT 60",
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    details TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS postmortems (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    incident_id TEXT NOT NULL UNIQUE,
                    project_id TEXT,
                    project_name TEXT,
                    component TEXT NOT NULL,
                    title TEXT NOT NULL,
                    severity TEXT,
                    status TEXT NOT NULL,
                    owner TEXT,
                    summary TEXT,
                    impact TEXT,
                    root_cause TEXT,
                    corrective_actions TEXT,
                    lessons_learned TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_postmortems_project_component
                ON postmortems(project_id, project_name, component, status)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_audit_log_entity
                ON audit_log(entity_type, entity_id, created_at)
                """
            )
            conn.execute(
                """
                CREATE TRIGGER IF NOT EXISTS audit_log_prevent_update
                BEFORE UPDATE ON audit_log
                BEGIN
                    SELECT RAISE(ABORT, 'audit_log records are immutable');
                END
                """
            )
            conn.execute(
                """
                CREATE TRIGGER IF NOT EXISTS audit_log_prevent_delete
                BEFORE DELETE ON audit_log
                BEGIN
                    SELECT RAISE(ABORT, 'audit_log records are immutable');
                END
                """
            )

    def create_event(self, payload: dict[str, Any]) -> Event:
        project_id = _optional_text(
            payload.get("project_id")
            or payload.get("projectId")
            or payload.get("pid")
        )
        project_name = _optional_text(
            payload.get("project_name")
            or payload.get("projectName")
            or payload.get("project")
        )
        component = _required_text(payload, "component")
        source = _optional_text(payload.get("source") or payload.get("monitoring_system"))
        severity = _optional_text(payload.get("severity") or payload.get("level"))
        title = _optional_text(payload.get("title") or payload.get("event_name"))
        message = _optional_text(payload.get("message") or payload.get("description"))
        created_at = datetime.now(timezone.utc).isoformat()

        if not project_id and not project_name:
            raise ValueError("project_id or project_name is required")

        source = source or "unknown"
        raw_payload = json.dumps(payload, sort_keys=True, separators=(",", ":"))

        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO events (
                    project_id,
                    project_name,
                    component,
                    source,
                    severity,
                    title,
                    message,
                    raw_payload,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    project_name,
                    component,
                    source,
                    severity,
                    title,
                    message,
                    raw_payload,
                    created_at,
                ),
            )
            event_id = int(cursor.lastrowid)

        return Event(
            id=event_id,
            project_id=project_id,
            project_name=project_name,
            component=component,
            source=source,
            severity=severity,
            title=title,
            message=message,
            raw_payload=payload,
            created_at=created_at,
        )

    def list_events(
        self,
        *,
        project_id: str | None = None,
        project_name: str | None = None,
        component: str | None = None,
        limit: int = 100,
    ) -> list[Event]:
        query = "SELECT * FROM events"
        filters: list[str] = []
        params: list[Any] = []

        if project_id:
            filters.append("project_id = ?")
            params.append(project_id)
        if project_name:
            filters.append("project_name = ?")
            params.append(project_name)
        if component:
            filters.append("component = ?")
            params.append(component)
        if filters:
            query += " WHERE " + " AND ".join(filters)

        query += " ORDER BY created_at DESC, id DESC LIMIT ?"
        params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()

        return [_row_to_event(row) for row in rows]

    def upsert_policy(self, payload: dict[str, Any]) -> AppPolicy:
        project_id = _optional_text(
            payload.get("project_id")
            or payload.get("projectId")
            or payload.get("pid")
        )
        project_name = _optional_text(
            payload.get("project_name")
            or payload.get("projectName")
            or payload.get("project")
        )
        component = _required_text(payload, "component")
        min_replicas = _int_value(payload.get("min_replicas"), "min_replicas", default=1)
        max_replicas = _int_value(payload.get("max_replicas"), "max_replicas", default=4)
        scale_up_threshold = _int_value(
            payload.get("scale_up_threshold"),
            "scale_up_threshold",
            default=80,
        )
        scale_down_threshold = _int_value(
            payload.get("scale_down_threshold"),
            "scale_down_threshold",
            default=25,
        )
        stop_during_off_hours = _bool_value(payload.get("stop_during_off_hours"))
        off_hours_start = _optional_text(payload.get("off_hours_start"))
        off_hours_end = _optional_text(payload.get("off_hours_end"))
        stop_during_holidays = _bool_value(payload.get("stop_during_holidays"))
        holiday_calendar = _optional_text(payload.get("holiday_calendar"))
        updated_at = datetime.now(timezone.utc).isoformat()

        if not project_id and not project_name:
            raise ValueError("project_id or project_name is required")
        if min_replicas < 0:
            raise ValueError("min_replicas must be greater than or equal to 0")
        if max_replicas < min_replicas:
            raise ValueError("max_replicas must be greater than or equal to min_replicas")
        if not 0 <= scale_down_threshold <= 100:
            raise ValueError("scale_down_threshold must be between 0 and 100")
        if not 0 <= scale_up_threshold <= 100:
            raise ValueError("scale_up_threshold must be between 0 and 100")

        existing_policy = self.list_policies(
            project_id=project_id,
            project_name=project_name,
            component=component,
            limit=1,
        )
        action = "updated" if existing_policy else "created"

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO policies (
                    project_id,
                    project_name,
                    component,
                    min_replicas,
                    max_replicas,
                    scale_up_threshold,
                    scale_down_threshold,
                    stop_during_off_hours,
                    off_hours_start,
                    off_hours_end,
                    stop_during_holidays,
                    holiday_calendar,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(project_id, project_name, component) DO UPDATE SET
                    min_replicas = excluded.min_replicas,
                    max_replicas = excluded.max_replicas,
                    scale_up_threshold = excluded.scale_up_threshold,
                    scale_down_threshold = excluded.scale_down_threshold,
                    stop_during_off_hours = excluded.stop_during_off_hours,
                    off_hours_start = excluded.off_hours_start,
                    off_hours_end = excluded.off_hours_end,
                    stop_during_holidays = excluded.stop_during_holidays,
                    holiday_calendar = excluded.holiday_calendar,
                    updated_at = excluded.updated_at
                """,
                (
                    project_id,
                    project_name,
                    component,
                    min_replicas,
                    max_replicas,
                    scale_up_threshold,
                    scale_down_threshold,
                    int(stop_during_off_hours),
                    off_hours_start,
                    off_hours_end,
                    int(stop_during_holidays),
                    holiday_calendar,
                    updated_at,
                ),
            )

        policy = self.list_policies(
            project_id=project_id,
            project_name=project_name,
            component=component,
            limit=1,
        )[0]
        self.record_audit(
            entity_type="policy",
            entity_id=_policy_entity_id(policy),
            action=action,
            summary=f"Policy {action} for {policy.project_id or policy.project_name}/{policy.component}",
            details=_policy_audit_details(policy),
        )
        return policy

    def list_policies(
        self,
        *,
        project_id: str | None = None,
        project_name: str | None = None,
        component: str | None = None,
        limit: int = 100,
    ) -> list[AppPolicy]:
        query = "SELECT * FROM policies"
        filters: list[str] = []
        params: list[Any] = []

        if project_id:
            filters.append("project_id = ?")
            params.append(project_id)
        if project_name:
            filters.append("project_name = ?")
            params.append(project_name)
        if component:
            filters.append("component = ?")
            params.append(component)
        if filters:
            query += " WHERE " + " AND ".join(filters)

        query += " ORDER BY updated_at DESC, id DESC LIMIT ?"
        params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()

        return [_row_to_policy(row) for row in rows]

    def save_endpoint_config(self, payload: dict[str, Any]) -> EndpointConfig:
        endpoint_url = _required_text(payload, "endpoint_url")
        auth_type = _optional_text(payload.get("auth_type")) or "adfs"
        adfs_client_id = _required_text(payload, "adfs_client_id")
        adfs_server_id = _required_text(payload, "adfs_server_id")
        adfs_username = _required_text(payload, "adfs_username")
        adfs_password = _optional_text(payload.get("adfs_password"))
        retry_enabled = _bool_value(payload.get("retry_enabled", True))
        max_retry_attempts = _int_value(
            payload.get("max_retry_attempts"),
            "max_retry_attempts",
            default=3,
        )
        retry_backoff_seconds = _int_value(
            payload.get("retry_backoff_seconds"),
            "retry_backoff_seconds",
            default=2,
        )
        circuit_breaker_enabled = _bool_value(
            payload.get("circuit_breaker_enabled", True)
        )
        circuit_breaker_failure_threshold = _int_value(
            payload.get("circuit_breaker_failure_threshold"),
            "circuit_breaker_failure_threshold",
            default=5,
        )
        circuit_breaker_reset_timeout_seconds = _int_value(
            payload.get("circuit_breaker_reset_timeout_seconds"),
            "circuit_breaker_reset_timeout_seconds",
            default=60,
        )
        updated_at = datetime.now(timezone.utc).isoformat()

        if auth_type != "adfs":
            raise ValueError("auth_type must be adfs")
        if not endpoint_url.startswith(("http://", "https://")):
            raise ValueError("endpoint_url must start with http:// or https://")
        if max_retry_attempts < 0:
            raise ValueError("max_retry_attempts must be greater than or equal to 0")
        if retry_backoff_seconds < 0:
            raise ValueError("retry_backoff_seconds must be greater than or equal to 0")
        if circuit_breaker_failure_threshold < 1:
            raise ValueError("circuit_breaker_failure_threshold must be greater than or equal to 1")
        if circuit_breaker_reset_timeout_seconds < 1:
            raise ValueError("circuit_breaker_reset_timeout_seconds must be greater than or equal to 1")

        current_password = self._get_endpoint_password()
        if adfs_password is None:
            if current_password is None:
                raise ValueError("adfs_password is required")
            adfs_password = current_password

        existing_config = self.get_endpoint_config()
        action = "updated" if existing_config else "created"

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO endpoint_config (
                    id,
                    endpoint_url,
                    auth_type,
                    adfs_client_id,
                    adfs_server_id,
                    adfs_username,
                    adfs_password,
                    retry_enabled,
                    max_retry_attempts,
                    retry_backoff_seconds,
                    circuit_breaker_enabled,
                    circuit_breaker_failure_threshold,
                    circuit_breaker_reset_timeout_seconds,
                    updated_at
                )
                VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    endpoint_url = excluded.endpoint_url,
                    auth_type = excluded.auth_type,
                    adfs_client_id = excluded.adfs_client_id,
                    adfs_server_id = excluded.adfs_server_id,
                    adfs_username = excluded.adfs_username,
                    adfs_password = excluded.adfs_password,
                    retry_enabled = excluded.retry_enabled,
                    max_retry_attempts = excluded.max_retry_attempts,
                    retry_backoff_seconds = excluded.retry_backoff_seconds,
                    circuit_breaker_enabled = excluded.circuit_breaker_enabled,
                    circuit_breaker_failure_threshold = excluded.circuit_breaker_failure_threshold,
                    circuit_breaker_reset_timeout_seconds = excluded.circuit_breaker_reset_timeout_seconds,
                    updated_at = excluded.updated_at
                """,
                (
                    endpoint_url,
                    auth_type,
                    adfs_client_id,
                    adfs_server_id,
                    adfs_username,
                    adfs_password,
                    int(retry_enabled),
                    max_retry_attempts,
                    retry_backoff_seconds,
                    int(circuit_breaker_enabled),
                    circuit_breaker_failure_threshold,
                    circuit_breaker_reset_timeout_seconds,
                    updated_at,
                ),
            )

        config = self.get_endpoint_config()
        if config is None:
            raise ValueError("endpoint configuration could not be saved")
        self.record_audit(
            entity_type="endpoint_config",
            entity_id="auto-healer",
            action=action,
            summary=f"Endpoint configuration {action}",
            details=_config_audit_details(config),
        )
        return config

    def get_endpoint_config(self) -> EndpointConfig | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM endpoint_config WHERE id = 1").fetchone()

        if row is None:
            return None
        return _row_to_endpoint_config(row)

    def _get_endpoint_password(self) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT adfs_password FROM endpoint_config WHERE id = 1"
            ).fetchone()

        if row is None:
            return None
        return row["adfs_password"]

    def record_audit(
        self,
        *,
        entity_type: str,
        entity_id: str,
        action: str,
        summary: str,
        details: dict[str, Any],
    ) -> AuditEntry:
        created_at = datetime.now(timezone.utc).isoformat()
        details_json = json.dumps(details, sort_keys=True, separators=(",", ":"))

        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO audit_log (
                    entity_type,
                    entity_id,
                    action,
                    summary,
                    details,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    entity_type,
                    entity_id,
                    action,
                    summary,
                    details_json,
                    created_at,
                ),
            )
            audit_id = int(cursor.lastrowid)

        return AuditEntry(
            id=audit_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            summary=summary,
            details=details,
            created_at=created_at,
        )

    def list_audit_entries(
        self,
        *,
        entity_type: str | None = None,
        entity_id: str | None = None,
        limit: int = 100,
    ) -> list[AuditEntry]:
        query = "SELECT * FROM audit_log"
        filters: list[str] = []
        params: list[Any] = []

        if entity_type:
            filters.append("entity_type = ?")
            params.append(entity_type)
        if entity_id:
            filters.append("entity_id = ?")
            params.append(entity_id)
        if filters:
            query += " WHERE " + " AND ".join(filters)

        query += " ORDER BY created_at DESC, id DESC LIMIT ?"
        params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()

        return [_row_to_audit_entry(row) for row in rows]

    def upsert_postmortem(self, payload: dict[str, Any]) -> Postmortem:
        incident_id = _required_text(payload, "incident_id")
        project_id = _optional_text(
            payload.get("project_id")
            or payload.get("projectId")
            or payload.get("pid")
        )
        project_name = _optional_text(
            payload.get("project_name")
            or payload.get("projectName")
            or payload.get("project")
        )
        component = _required_text(payload, "component")
        title = _required_text(payload, "title")
        severity = _optional_text(payload.get("severity"))
        status = _optional_text(payload.get("status")) or "draft"
        owner = _optional_text(payload.get("owner"))
        summary = _optional_text(payload.get("summary"))
        impact = _optional_text(payload.get("impact"))
        root_cause = _optional_text(payload.get("root_cause"))
        corrective_actions = _optional_text(payload.get("corrective_actions"))
        lessons_learned = _optional_text(payload.get("lessons_learned"))
        updated_at = datetime.now(timezone.utc).isoformat()

        if not project_id and not project_name:
            raise ValueError("project_id or project_name is required")
        if status not in {"draft", "in_review", "published"}:
            raise ValueError("status must be draft, in_review, or published")

        existing = self.list_postmortems(incident_id=incident_id, limit=1)
        action = "updated" if existing else "created"
        created_at = existing[0].created_at if existing else updated_at

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO postmortems (
                    incident_id,
                    project_id,
                    project_name,
                    component,
                    title,
                    severity,
                    status,
                    owner,
                    summary,
                    impact,
                    root_cause,
                    corrective_actions,
                    lessons_learned,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(incident_id) DO UPDATE SET
                    project_id = excluded.project_id,
                    project_name = excluded.project_name,
                    component = excluded.component,
                    title = excluded.title,
                    severity = excluded.severity,
                    status = excluded.status,
                    owner = excluded.owner,
                    summary = excluded.summary,
                    impact = excluded.impact,
                    root_cause = excluded.root_cause,
                    corrective_actions = excluded.corrective_actions,
                    lessons_learned = excluded.lessons_learned,
                    updated_at = excluded.updated_at
                """,
                (
                    incident_id,
                    project_id,
                    project_name,
                    component,
                    title,
                    severity,
                    status,
                    owner,
                    summary,
                    impact,
                    root_cause,
                    corrective_actions,
                    lessons_learned,
                    created_at,
                    updated_at,
                ),
            )

        postmortem = self.list_postmortems(incident_id=incident_id, limit=1)[0]
        self.record_audit(
            entity_type="postmortem",
            entity_id=postmortem.incident_id,
            action=action,
            summary=f"Postmortem {action} for {postmortem.incident_id}",
            details=_postmortem_audit_details(postmortem),
        )
        return postmortem

    def list_postmortems(
        self,
        *,
        incident_id: str | None = None,
        project_id: str | None = None,
        project_name: str | None = None,
        component: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[Postmortem]:
        query = "SELECT * FROM postmortems"
        filters: list[str] = []
        params: list[Any] = []

        if incident_id:
            filters.append("incident_id = ?")
            params.append(incident_id)
        if project_id:
            filters.append("project_id = ?")
            params.append(project_id)
        if project_name:
            filters.append("project_name = ?")
            params.append(project_name)
        if component:
            filters.append("component = ?")
            params.append(component)
        if status:
            filters.append("status = ?")
            params.append(status)
        if filters:
            query += " WHERE " + " AND ".join(filters)

        query += " ORDER BY updated_at DESC, id DESC LIMIT ?"
        params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()

        return [_row_to_postmortem(row) for row in rows]

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn


def _required_text(payload: dict[str, Any], key: str) -> str:
    value = _optional_text(payload.get(key))
    if not value:
        raise ValueError(f"{key} is required")
    return value


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _int_value(value: Any, key: str, *, default: int) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{key} must be an integer") from None


def _bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _ensure_column(
    conn: sqlite3.Connection,
    table_name: str,
    column_name: str,
    column_definition: str,
) -> None:
    columns = {
        row["name"]
        for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    if column_name not in columns:
        conn.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
        )


def _row_to_event(row: sqlite3.Row) -> Event:
    return Event(
        id=row["id"],
        project_id=row["project_id"],
        project_name=row["project_name"],
        component=row["component"],
        source=row["source"],
        severity=row["severity"],
        title=row["title"],
        message=row["message"],
        raw_payload=json.loads(row["raw_payload"]),
        created_at=row["created_at"],
    )


def _row_to_policy(row: sqlite3.Row) -> AppPolicy:
    return AppPolicy(
        id=row["id"],
        project_id=row["project_id"],
        project_name=row["project_name"],
        component=row["component"],
        min_replicas=row["min_replicas"],
        max_replicas=row["max_replicas"],
        scale_up_threshold=row["scale_up_threshold"],
        scale_down_threshold=row["scale_down_threshold"],
        stop_during_off_hours=bool(row["stop_during_off_hours"]),
        off_hours_start=row["off_hours_start"],
        off_hours_end=row["off_hours_end"],
        stop_during_holidays=bool(row["stop_during_holidays"]),
        holiday_calendar=row["holiday_calendar"],
        updated_at=row["updated_at"],
    )


def _row_to_endpoint_config(row: sqlite3.Row) -> EndpointConfig:
    return EndpointConfig(
        id=row["id"],
        endpoint_url=row["endpoint_url"],
        auth_type=row["auth_type"],
        adfs_client_id=row["adfs_client_id"],
        adfs_server_id=row["adfs_server_id"],
        adfs_username=row["adfs_username"],
        password_set=bool(row["adfs_password"]),
        retry_enabled=bool(row["retry_enabled"]),
        max_retry_attempts=row["max_retry_attempts"],
        retry_backoff_seconds=row["retry_backoff_seconds"],
        circuit_breaker_enabled=bool(row["circuit_breaker_enabled"]),
        circuit_breaker_failure_threshold=row["circuit_breaker_failure_threshold"],
        circuit_breaker_reset_timeout_seconds=row[
            "circuit_breaker_reset_timeout_seconds"
        ],
        updated_at=row["updated_at"],
    )


def _row_to_audit_entry(row: sqlite3.Row) -> AuditEntry:
    return AuditEntry(
        id=row["id"],
        entity_type=row["entity_type"],
        entity_id=row["entity_id"],
        action=row["action"],
        summary=row["summary"],
        details=json.loads(row["details"]),
        created_at=row["created_at"],
    )


def _row_to_postmortem(row: sqlite3.Row) -> Postmortem:
    return Postmortem(
        id=row["id"],
        incident_id=row["incident_id"],
        project_id=row["project_id"],
        project_name=row["project_name"],
        component=row["component"],
        title=row["title"],
        severity=row["severity"],
        status=row["status"],
        owner=row["owner"],
        summary=row["summary"],
        impact=row["impact"],
        root_cause=row["root_cause"],
        corrective_actions=row["corrective_actions"],
        lessons_learned=row["lessons_learned"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _policy_entity_id(policy: AppPolicy) -> str:
    project = policy.project_id or policy.project_name or "unknown"
    return f"{project}:{policy.component}"


def _policy_audit_details(policy: AppPolicy) -> dict[str, Any]:
    return {
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
    }


def _config_audit_details(config: EndpointConfig) -> dict[str, Any]:
    return {
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
    }


def _postmortem_audit_details(postmortem: Postmortem) -> dict[str, Any]:
    return {
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
    }
