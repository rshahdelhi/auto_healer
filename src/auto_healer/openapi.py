from __future__ import annotations

from typing import Any


def build_openapi_schema() -> dict[str, Any]:
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "Auto Healer API",
            "version": "0.1.0",
            "description": (
                "Accept monitoring events from Dynatrace, Splunk, Phoenix, "
                "or any JSON-capable monitoring system and persist them in SQLite."
            ),
        },
        "servers": [{"url": "/"}],
        "paths": {
            "/health": {
                "get": {
                    "summary": "Check service health",
                    "responses": {
                        "200": {
                            "description": "Service is online",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Health"}
                                }
                            },
                        }
                    },
                }
            },
            "/events": {
                "get": {
                    "summary": "List stored monitoring events",
                    "parameters": [
                        {
                            "name": "project_id",
                            "in": "query",
                            "schema": {"type": "string"},
                            "description": "Filter by project id.",
                        },
                        {
                            "name": "project_name",
                            "in": "query",
                            "schema": {"type": "string"},
                            "description": "Filter by project name.",
                        },
                        {
                            "name": "component",
                            "in": "query",
                            "schema": {"type": "string"},
                            "description": "Filter by component name.",
                        },
                        {
                            "name": "limit",
                            "in": "query",
                            "schema": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 500,
                                "default": 100,
                            },
                            "description": "Maximum events to return.",
                        },
                    ],
                    "responses": {
                        "200": {
                            "description": "Stored events.",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "events": {
                                                "type": "array",
                                                "items": {
                                                    "$ref": "#/components/schemas/Event"
                                                },
                                            }
                                        },
                                        "required": ["events"],
                                    }
                                }
                            },
                        }
                    },
                },
                "post": {
                    "summary": "Ingest a monitoring event",
                    "description": (
                        "The payload must include component and either a project id "
                        "or project name. Provider-specific fields are accepted and "
                        "preserved in raw_payload."
                    ),
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/EventInput"},
                                "examples": {
                                    "dynatrace": {
                                        "summary": "Dynatrace problem event",
                                        "value": {
                                            "projectId": "checkout",
                                            "projectName": "Checkout",
                                            "component": "payments-api",
                                            "source": "dynatrace",
                                            "severity": "critical",
                                            "event_name": "Dynatrace problem notification",
                                            "message": "p95 latency crossed threshold",
                                            "dt_problem_id": "P-12345",
                                        },
                                    },
                                    "splunk": {
                                        "summary": "Splunk alert event",
                                        "value": {
                                            "project_id": "inventory",
                                            "project_name": "Inventory",
                                            "component": "stock-api",
                                            "monitoring_system": "splunk",
                                            "severity": "warning",
                                            "message": "Error rate increased above baseline",
                                            "sid": "splunk-12345",
                                        },
                                    },
                                    "phoenix": {
                                        "summary": "Phoenix event",
                                        "value": {
                                            "pid": "customer-care",
                                            "project": "Customer Care",
                                            "component": "case-worker",
                                            "source": "phoenix",
                                            "level": "info",
                                            "description": "Queue depth returned to normal",
                                            "incident_key": "phoenix-12345",
                                        },
                                    },
                                },
                            }
                        },
                    },
                    "responses": {
                        "201": {
                            "description": "Event stored.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Event"}
                                }
                            },
                        },
                        "400": {
                            "description": "Invalid payload.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Error"}
                                }
                            },
                        },
                    },
                },
            },
            "/splunk/alerts": {
                "post": {
                    "summary": "Ingest a Splunk alert",
                    "description": (
                        "Accepts Splunk webhook-style alerts and normalizes them "
                        "into Auto Healer events. Common fields can be sent at the "
                        "top level or inside the Splunk result object."
                    ),
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/SplunkAlertInput"
                                },
                                "examples": {
                                    "system_error": {
                                        "summary": "System error alert",
                                        "value": {
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
                                                "usage_percent": 96,
                                            },
                                        },
                                    },
                                    "application_error": {
                                        "summary": "Application error alert",
                                        "value": {
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
                                                "error_rate_percent": 18,
                                            },
                                        },
                                    },
                                },
                            }
                        },
                    },
                    "responses": {
                        "201": {
                            "description": "Splunk alert stored as an event.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Event"}
                                }
                            },
                        },
                        "400": {
                            "description": "Invalid Splunk alert payload.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Error"}
                                }
                            },
                        },
                    },
                }
            },
            "/policies": {
                "get": {
                    "summary": "List application control policies",
                    "parameters": [
                        {
                            "name": "project_id",
                            "in": "query",
                            "schema": {"type": "string"},
                        },
                        {
                            "name": "project_name",
                            "in": "query",
                            "schema": {"type": "string"},
                        },
                        {
                            "name": "component",
                            "in": "query",
                            "schema": {"type": "string"},
                        },
                        {
                            "name": "limit",
                            "in": "query",
                            "schema": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 500,
                                "default": 100,
                            },
                        },
                    ],
                    "responses": {
                        "200": {
                            "description": "Saved policies.",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "policies": {
                                                "type": "array",
                                                "items": {
                                                    "$ref": "#/components/schemas/AppPolicy"
                                                },
                                            }
                                        },
                                        "required": ["policies"],
                                    }
                                }
                            },
                        }
                    },
                },
                "post": {
                    "summary": "Create or update an application control policy",
                    "description": (
                        "Stores user-defined scale limits and schedule rules for "
                        "a project/component pair."
                    ),
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/AppPolicyInput"},
                                "example": {
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
                                },
                            }
                        },
                    },
                    "responses": {
                        "201": {
                            "description": "Policy saved.",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/AppPolicy"
                                    }
                                }
                            },
                        },
                        "400": {
                            "description": "Invalid policy.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Error"}
                                }
                            },
                        },
                    },
                },
            },
            "/endpoint-config": {
                "get": {
                    "summary": "Get Auto Healer endpoint configuration",
                    "description": "Returns endpoint and ADFS fields without returning the saved password.",
                    "responses": {
                        "200": {
                            "description": "Current endpoint configuration, or null when unset.",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "config": {
                                                "oneOf": [
                                                    {
                                                        "$ref": "#/components/schemas/EndpointConfig"
                                                    },
                                                    {"type": "null"},
                                                ]
                                            }
                                        },
                                        "required": ["config"],
                                    }
                                }
                            },
                        }
                    },
                },
                "post": {
                    "summary": "Save Auto Healer endpoint configuration",
                    "description": (
                        "Stores endpoint URL and ADFS authentication settings. "
                        "The password is accepted but is never returned by the API."
                    ),
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/EndpointConfigInput"
                                },
                                "example": {
                                    "endpoint_url": "https://auto-healer.example.com/api",
                                    "auth_type": "adfs",
                                    "adfs_client_id": "auto-healer-ui",
                                    "adfs_server_id": "urn:auto-healer",
                                    "adfs_username": "ops.user@example.com",
                                    "adfs_password": "change-me",
                                    "retry_enabled": True,
                                    "max_retry_attempts": 3,
                                    "retry_backoff_seconds": 2,
                                    "circuit_breaker_enabled": True,
                                    "circuit_breaker_failure_threshold": 5,
                                    "circuit_breaker_reset_timeout_seconds": 60,
                                },
                            }
                        },
                    },
                    "responses": {
                        "201": {
                            "description": "Configuration saved.",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/EndpointConfig"
                                    }
                                }
                            },
                        },
                        "400": {
                            "description": "Invalid configuration.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Error"}
                                }
                            },
                        },
                    },
                },
            },
            "/audit-log": {
                "get": {
                    "summary": "List audit trail entries",
                    "description": (
                        "Returns changes recorded for rules/policies and endpoint "
                        "configuration updates."
                    ),
                    "parameters": [
                        {
                            "name": "entity_type",
                            "in": "query",
                            "schema": {
                                "type": "string",
                                "enum": ["policy", "endpoint_config"],
                            },
                        },
                        {
                            "name": "entity_id",
                            "in": "query",
                            "schema": {"type": "string"},
                        },
                        {
                            "name": "limit",
                            "in": "query",
                            "schema": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 500,
                                "default": 100,
                            },
                        },
                    ],
                    "responses": {
                        "200": {
                            "description": "Audit entries.",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "audit_log": {
                                                "type": "array",
                                                "items": {
                                                    "$ref": "#/components/schemas/AuditEntry"
                                                },
                                            }
                                        },
                                        "required": ["audit_log"],
                                    }
                                }
                            },
                        }
                    },
                }
            },
            "/postmortems": {
                "get": {
                    "summary": "List blameless postmortems and RCA records",
                    "parameters": [
                        {"name": "incident_id", "in": "query", "schema": {"type": "string"}},
                        {"name": "project_id", "in": "query", "schema": {"type": "string"}},
                        {"name": "component", "in": "query", "schema": {"type": "string"}},
                        {
                            "name": "status",
                            "in": "query",
                            "schema": {
                                "type": "string",
                                "enum": ["draft", "in_review", "published"],
                            },
                        },
                    ],
                    "responses": {
                        "200": {
                            "description": "Postmortem records.",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "postmortems": {
                                                "type": "array",
                                                "items": {
                                                    "$ref": "#/components/schemas/Postmortem"
                                                },
                                            }
                                        },
                                        "required": ["postmortems"],
                                    }
                                }
                            },
                        }
                    },
                },
                "post": {
                    "summary": "Create or update a blameless postmortem/RCA",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/PostmortemInput"},
                                "example": {
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
                                    "lessons_learned": "Retries need per-provider budgets.",
                                },
                            }
                        },
                    },
                    "responses": {
                        "201": {
                            "description": "Postmortem saved.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Postmortem"}
                                }
                            },
                        },
                        "400": {
                            "description": "Invalid postmortem.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Error"}
                                }
                            },
                        },
                    },
                },
            },
            "/skills": {
                "get": {
                    "summary": "List available auto-healing skills",
                    "description": (
                        "Returns bounded operational skills with their maximum "
                        "supported autonomy level."
                    ),
                    "responses": {
                        "200": {
                            "description": "Registered skills.",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "skills": {
                                                "type": "array",
                                                "items": {"$ref": "#/components/schemas/Skill"},
                                            }
                                        },
                                        "required": ["skills"],
                                    }
                                }
                            },
                        }
                    },
                }
            },
            "/skills/run": {
                "post": {
                    "summary": "Run an auto-healing skill through guardrails",
                    "description": (
                        "Generates a deterministic skill proposal, applies autonomy "
                        "and approval guardrails, records an immutable audit entry, "
                        "and defaults to dry-run execution."
                    ),
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/SkillRunInput"},
                                "example": {
                                    "skill": "scale_up",
                                    "project_id": "checkout",
                                    "component": "payments-api",
                                    "current_replicas": 2,
                                    "max_replicas": 6,
                                    "dry_run": True,
                                    "autonomy_level": 1,
                                    "event_id": 42,
                                    "reason": "p95 latency crossed threshold",
                                },
                            }
                        },
                    },
                    "responses": {
                        "201": {
                            "description": "Skill execution recorded.",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/SkillExecution"
                                    }
                                }
                            },
                        },
                        "400": {
                            "description": "Invalid skill request.",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Error"}
                                }
                            },
                        },
                    },
                }
            },
            "/skill-executions": {
                "get": {
                    "summary": "List skill execution records",
                    "parameters": [
                        {"name": "skill_name", "in": "query", "schema": {"type": "string"}},
                        {"name": "project_id", "in": "query", "schema": {"type": "string"}},
                        {"name": "project_name", "in": "query", "schema": {"type": "string"}},
                        {"name": "component", "in": "query", "schema": {"type": "string"}},
                        {"name": "status", "in": "query", "schema": {"type": "string"}},
                    ],
                    "responses": {
                        "200": {
                            "description": "Skill execution records.",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "skill_executions": {
                                                "type": "array",
                                                "items": {
                                                    "$ref": "#/components/schemas/SkillExecution"
                                                },
                                            }
                                        },
                                        "required": ["skill_executions"],
                                    }
                                }
                            },
                        }
                    },
                }
            },
        },
        "components": {
            "schemas": {
                "Health": {
                    "type": "object",
                    "properties": {"status": {"type": "string", "example": "ok"}},
                    "required": ["status"],
                },
                "EventInput": {
                    "type": "object",
                    "additionalProperties": True,
                    "properties": {
                        "project_id": {"type": "string"},
                        "projectId": {"type": "string"},
                        "pid": {"type": "string"},
                        "project_name": {"type": "string"},
                        "projectName": {"type": "string"},
                        "project": {"type": "string"},
                        "component": {"type": "string"},
                        "source": {"type": "string"},
                        "monitoring_system": {"type": "string"},
                        "severity": {
                            "type": "string",
                            "enum": ["critical", "warning", "info"],
                        },
                        "level": {"type": "string"},
                        "title": {"type": "string"},
                        "event_name": {"type": "string"},
                        "message": {"type": "string"},
                        "description": {"type": "string"},
                    },
                    "required": ["component"],
                },
                "Event": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "project_id": {"type": ["string", "null"]},
                        "project_name": {"type": ["string", "null"]},
                        "component": {"type": "string"},
                        "source": {"type": "string"},
                        "severity": {"type": ["string", "null"]},
                        "title": {"type": ["string", "null"]},
                        "message": {"type": ["string", "null"]},
                        "raw_payload": {"type": "object", "additionalProperties": True},
                        "created_at": {"type": "string", "format": "date-time"},
                    },
                    "required": [
                        "id",
                        "project_id",
                        "project_name",
                        "component",
                        "source",
                        "severity",
                        "title",
                        "message",
                        "raw_payload",
                        "created_at",
                    ],
                },
                "SplunkAlertInput": {
                    "type": "object",
                    "additionalProperties": True,
                    "properties": {
                        "search_name": {"type": "string"},
                        "sid": {"type": "string"},
                        "app": {"type": "string"},
                        "owner": {"type": "string"},
                        "alert_type": {
                            "type": "string",
                            "enum": ["system_error", "application_error"],
                        },
                        "project_id": {"type": "string"},
                        "project_name": {"type": "string"},
                        "component": {"type": "string"},
                        "severity": {"type": "string"},
                        "message": {"type": "string"},
                        "result": {
                            "type": "object",
                            "additionalProperties": True,
                            "properties": {
                                "project_id": {"type": "string"},
                                "project_name": {"type": "string"},
                                "component": {"type": "string"},
                                "host": {"type": "string"},
                                "severity": {"type": "string"},
                                "message": {"type": "string"},
                                "error": {"type": "string"},
                                "exception": {"type": "string"},
                            },
                        },
                    },
                },
                "Error": {
                    "type": "object",
                    "properties": {"error": {"type": "string"}},
                    "required": ["error"],
                },
                "AppPolicyInput": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "project_id": {"type": "string"},
                        "project_name": {"type": "string"},
                        "component": {"type": "string"},
                        "min_replicas": {"type": "integer", "minimum": 0},
                        "max_replicas": {"type": "integer", "minimum": 0},
                        "scale_up_threshold": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 100,
                        },
                        "scale_down_threshold": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 100,
                        },
                        "stop_during_off_hours": {"type": "boolean"},
                        "off_hours_start": {"type": "string", "example": "20:00"},
                        "off_hours_end": {"type": "string", "example": "06:00"},
                        "stop_during_holidays": {"type": "boolean"},
                        "holiday_calendar": {"type": "string"},
                    },
                    "required": ["component"],
                },
                "AppPolicy": {
                    "allOf": [
                        {"$ref": "#/components/schemas/AppPolicyInput"},
                        {
                            "type": "object",
                            "properties": {
                                "id": {"type": "integer"},
                                "updated_at": {
                                    "type": "string",
                                    "format": "date-time",
                                },
                            },
                            "required": ["id", "updated_at"],
                        },
                    ]
                },
                "EndpointConfigInput": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "endpoint_url": {
                            "type": "string",
                            "example": "https://auto-healer.example.com/api",
                        },
                        "auth_type": {"type": "string", "enum": ["adfs"]},
                        "adfs_client_id": {"type": "string"},
                        "adfs_server_id": {"type": "string"},
                        "adfs_username": {"type": "string"},
                        "adfs_password": {"type": "string", "format": "password"},
                        "retry_enabled": {"type": "boolean", "default": True},
                        "max_retry_attempts": {
                            "type": "integer",
                            "minimum": 0,
                            "default": 3,
                        },
                        "retry_backoff_seconds": {
                            "type": "integer",
                            "minimum": 0,
                            "default": 2,
                        },
                        "circuit_breaker_enabled": {
                            "type": "boolean",
                            "default": True,
                        },
                        "circuit_breaker_failure_threshold": {
                            "type": "integer",
                            "minimum": 1,
                            "default": 5,
                        },
                        "circuit_breaker_reset_timeout_seconds": {
                            "type": "integer",
                            "minimum": 1,
                            "default": 60,
                        },
                    },
                    "required": [
                        "endpoint_url",
                        "auth_type",
                        "adfs_client_id",
                        "adfs_server_id",
                        "adfs_username",
                    ],
                },
                "EndpointConfig": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "endpoint_url": {"type": "string"},
                        "auth_type": {"type": "string", "enum": ["adfs"]},
                        "adfs_client_id": {"type": "string"},
                        "adfs_server_id": {"type": "string"},
                        "adfs_username": {"type": "string"},
                        "password_set": {"type": "boolean"},
                        "retry_enabled": {"type": "boolean"},
                        "max_retry_attempts": {"type": "integer"},
                        "retry_backoff_seconds": {"type": "integer"},
                        "circuit_breaker_enabled": {"type": "boolean"},
                        "circuit_breaker_failure_threshold": {"type": "integer"},
                        "circuit_breaker_reset_timeout_seconds": {"type": "integer"},
                        "updated_at": {"type": "string", "format": "date-time"},
                    },
                    "required": [
                        "id",
                        "endpoint_url",
                        "auth_type",
                        "adfs_client_id",
                        "adfs_server_id",
                        "adfs_username",
                        "password_set",
                        "retry_enabled",
                        "max_retry_attempts",
                        "retry_backoff_seconds",
                        "circuit_breaker_enabled",
                        "circuit_breaker_failure_threshold",
                        "circuit_breaker_reset_timeout_seconds",
                        "updated_at",
                    ],
                },
                "AuditEntry": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "entity_type": {"type": "string"},
                        "entity_id": {"type": "string"},
                        "action": {"type": "string"},
                        "summary": {"type": "string"},
                        "details": {"type": "object", "additionalProperties": True},
                        "created_at": {"type": "string", "format": "date-time"},
                    },
                    "required": [
                        "id",
                        "entity_type",
                        "entity_id",
                        "action",
                        "summary",
                        "details",
                        "created_at",
                    ],
                },
                "PostmortemInput": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "incident_id": {"type": "string"},
                        "project_id": {"type": "string"},
                        "project_name": {"type": "string"},
                        "component": {"type": "string"},
                        "title": {"type": "string"},
                        "severity": {"type": "string"},
                        "status": {
                            "type": "string",
                            "enum": ["draft", "in_review", "published"],
                        },
                        "owner": {"type": "string"},
                        "summary": {"type": "string"},
                        "impact": {"type": "string"},
                        "root_cause": {"type": "string"},
                        "corrective_actions": {"type": "string"},
                        "lessons_learned": {"type": "string"},
                    },
                    "required": ["incident_id", "component", "title"],
                },
                "Postmortem": {
                    "allOf": [
                        {"$ref": "#/components/schemas/PostmortemInput"},
                        {
                            "type": "object",
                            "properties": {
                                "id": {"type": "integer"},
                                "created_at": {
                                    "type": "string",
                                    "format": "date-time",
                                },
                                "updated_at": {
                                    "type": "string",
                                    "format": "date-time",
                                },
                            },
                            "required": ["id", "created_at", "updated_at"],
                        },
                    ]
                },
                "Skill": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "max_autonomy_level": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 4,
                        },
                    },
                    "required": ["name", "description", "max_autonomy_level"],
                },
                "SkillRunInput": {
                    "type": "object",
                    "additionalProperties": True,
                    "properties": {
                        "skill": {"type": "string"},
                        "project_id": {"type": "string"},
                        "project_name": {"type": "string"},
                        "component": {"type": "string"},
                        "dry_run": {"type": "boolean", "default": True},
                        "approved": {"type": "boolean", "default": False},
                        "autonomy_level": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 4,
                            "default": 1,
                        },
                    },
                    "required": ["skill", "component"],
                },
                "SkillExecution": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "skill_name": {"type": "string"},
                        "project_id": {"type": ["string", "null"]},
                        "project_name": {"type": ["string", "null"]},
                        "component": {"type": "string"},
                        "autonomy_level": {"type": "integer"},
                        "dry_run": {"type": "boolean"},
                        "approved": {"type": "boolean"},
                        "risk_level": {"type": "string"},
                        "status": {"type": "string"},
                        "reason": {"type": "string"},
                        "proposal": {"type": "object", "additionalProperties": True},
                        "evidence": {"type": "object", "additionalProperties": True},
                        "created_at": {"type": "string", "format": "date-time"},
                    },
                    "required": [
                        "id",
                        "skill_name",
                        "project_id",
                        "project_name",
                        "component",
                        "autonomy_level",
                        "dry_run",
                        "approved",
                        "risk_level",
                        "status",
                        "reason",
                        "proposal",
                        "evidence",
                        "created_at",
                    ],
                },
            }
        },
    }
