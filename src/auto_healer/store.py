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
                    updated_at TEXT NOT NULL
                )
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

        return self.list_policies(
            project_id=project_id,
            project_name=project_name,
            component=component,
            limit=1,
        )[0]

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
        updated_at = datetime.now(timezone.utc).isoformat()

        if auth_type != "adfs":
            raise ValueError("auth_type must be adfs")
        if not endpoint_url.startswith(("http://", "https://")):
            raise ValueError("endpoint_url must start with http:// or https://")

        current_password = self._get_endpoint_password()
        if adfs_password is None:
            if current_password is None:
                raise ValueError("adfs_password is required")
            adfs_password = current_password

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
                    updated_at
                )
                VALUES (1, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    endpoint_url = excluded.endpoint_url,
                    auth_type = excluded.auth_type,
                    adfs_client_id = excluded.adfs_client_id,
                    adfs_server_id = excluded.adfs_server_id,
                    adfs_username = excluded.adfs_username,
                    adfs_password = excluded.adfs_password,
                    updated_at = excluded.updated_at
                """,
                (
                    endpoint_url,
                    auth_type,
                    adfs_client_id,
                    adfs_server_id,
                    adfs_username,
                    adfs_password,
                    updated_at,
                ),
            )

        config = self.get_endpoint_config()
        if config is None:
            raise ValueError("endpoint configuration could not be saved")
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
        updated_at=row["updated_at"],
    )
