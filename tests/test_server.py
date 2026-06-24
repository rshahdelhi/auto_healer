import json
from http import HTTPStatus
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from threading import Thread

from auto_healer.server import create_handler
from auto_healer.store import EventStore


def test_post_events_persists_payload(tmp_path):
    store = EventStore(tmp_path / "events.sqlite3")
    server = ThreadingHTTPServer(("127.0.0.1", 0), create_handler(store))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        conn = HTTPConnection("127.0.0.1", server.server_port)
        conn.request(
            "POST",
            "/events",
            body=json.dumps(
                {
                    "project_id": "inventory",
                    "component": "stock-api",
                    "source": "phoenix",
                    "message": "error rate increased",
                }
            ),
            headers={"Content-Type": "application/json"},
        )
        response = conn.getresponse()
        body = json.loads(response.read())
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert response.status == HTTPStatus.CREATED
    assert body["project_id"] == "inventory"
    assert body["component"] == "stock-api"
    assert store.list_events(project_id="inventory")[0].message == "error rate increased"


def test_get_root_serves_ui(tmp_path):
    store = EventStore(tmp_path / "events.sqlite3")
    server = ThreadingHTTPServer(("127.0.0.1", 0), create_handler(store))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        conn = HTTPConnection("127.0.0.1", server.server_port)
        conn.request("GET", "/")
        response = conn.getresponse()
        body = response.read().decode("utf-8")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert response.status == HTTPStatus.OK
    assert "Monitoring Event Console" in body


def test_get_configuration_page(tmp_path):
    store = EventStore(tmp_path / "events.sqlite3")
    server = ThreadingHTTPServer(("127.0.0.1", 0), create_handler(store))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        conn = HTTPConnection("127.0.0.1", server.server_port)
        conn.request("GET", "/configuration")
        response = conn.getresponse()
        body = response.read().decode("utf-8")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert response.status == HTTPStatus.OK
    assert "Endpoint Configuration" in body


def test_get_openapi_schema(tmp_path):
    store = EventStore(tmp_path / "events.sqlite3")
    server = ThreadingHTTPServer(("127.0.0.1", 0), create_handler(store))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        conn = HTTPConnection("127.0.0.1", server.server_port)
        conn.request("GET", "/openapi.json")
        response = conn.getresponse()
        body = json.loads(response.read())
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert response.status == HTTPStatus.OK
    assert body["openapi"] == "3.1.0"
    assert "/events" in body["paths"]
    assert "/policies" in body["paths"]
    assert "/endpoint-config" in body["paths"]


def test_get_docs_pages(tmp_path):
    store = EventStore(tmp_path / "events.sqlite3")
    server = ThreadingHTTPServer(("127.0.0.1", 0), create_handler(store))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        conn = HTTPConnection("127.0.0.1", server.server_port)
        conn.request("GET", "/docs")
        swagger_response = conn.getresponse()
        swagger_body = swagger_response.read().decode("utf-8")

        conn.request("GET", "/documentation")
        docs_response = conn.getresponse()
        docs_body = docs_response.read().decode("utf-8")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert swagger_response.status == HTTPStatus.OK
    assert "SwaggerUIBundle" in swagger_body
    assert docs_response.status == HTTPStatus.OK
    assert "API Documentation" in docs_body


def test_post_policy_persists_scale_schedule(tmp_path):
    store = EventStore(tmp_path / "events.sqlite3")
    server = ThreadingHTTPServer(("127.0.0.1", 0), create_handler(store))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        conn = HTTPConnection("127.0.0.1", server.server_port)
        conn.request(
            "POST",
            "/policies",
            body=json.dumps(
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
            ),
            headers={"Content-Type": "application/json"},
        )
        response = conn.getresponse()
        body = json.loads(response.read())
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert response.status == HTTPStatus.CREATED
    assert body["project_id"] == "checkout"
    assert body["max_replicas"] == 6
    assert body["stop_during_off_hours"] is True
    assert store.list_policies(project_id="checkout")[0].off_hours_start == "20:00"


def test_post_endpoint_config_masks_password(tmp_path):
    store = EventStore(tmp_path / "events.sqlite3")
    server = ThreadingHTTPServer(("127.0.0.1", 0), create_handler(store))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        conn = HTTPConnection("127.0.0.1", server.server_port)
        conn.request(
            "POST",
            "/endpoint-config",
            body=json.dumps(
                {
                    "endpoint_url": "https://auto-healer.example.com/api",
                    "auth_type": "adfs",
                    "adfs_client_id": "auto-healer-ui",
                    "adfs_server_id": "urn:auto-healer",
                    "adfs_username": "ops.user@example.com",
                    "adfs_password": "secret",
                }
            ),
            headers={"Content-Type": "application/json"},
        )
        response = conn.getresponse()
        body = json.loads(response.read())

        conn.request("GET", "/endpoint-config")
        get_response = conn.getresponse()
        get_body = json.loads(get_response.read())
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert response.status == HTTPStatus.CREATED
    assert body["endpoint_url"] == "https://auto-healer.example.com/api"
    assert body["password_set"] is True
    assert "adfs_password" not in body
    assert get_response.status == HTTPStatus.OK
    assert get_body["config"]["adfs_username"] == "ops.user@example.com"
    assert "adfs_password" not in get_body["config"]
