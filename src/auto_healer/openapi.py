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
                        "updated_at",
                    ],
                },
            }
        },
    }
