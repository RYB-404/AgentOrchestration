from fastapi.testclient import TestClient

from src.api import routes
from src.api.server import create_app
from src.agent import AgentRegistry


def make_client():
    routes.registry = AgentRegistry()
    return TestClient(create_app())


def auth_headers():
    return {"Authorization": "Bearer test-token"}


def test_public_api_rejects_unauthorized_request_consistently():
    client = make_client()

    response = client.get("/api/v2/agents")

    assert response.status_code == 401
    assert response.json() == {
        "error": {
            "code": "unauthorized",
            "message": "Bearer token is required",
        }
    }


def test_list_agents_rejects_malformed_status_before_lookup():
    client = make_client()

    response = client.get("/api/v2/agents?status=ready", headers=auth_headers())

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_request"
    assert response.json()["error"]["field"] == "status"


def test_get_agent_rejects_malformed_id_before_registry_lookup(monkeypatch):
    client = make_client()

    def fail_lookup(_agent_id):
        raise AssertionError("registry lookup must not run for malformed agent_id")

    monkeypatch.setattr(routes.registry, "get", fail_lookup)

    response = client.get("/api/v2/agents/not-a-uuid", headers=auth_headers())

    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "code": "invalid_request",
            "message": "agent_id must be a valid UUID",
            "field": "agent_id",
        }
    }


def test_register_agent_validates_inputs_before_mutation(monkeypatch):
    client = make_client()

    def fail_register(*_args, **_kwargs):
        raise AssertionError("registry mutation must not run for malformed name")

    monkeypatch.setattr(routes.registry, "register", fail_register)

    response = client.post(
        "/api/v2/agents",
        params={"name": "  ", "agent_type": "worker.processor"},
        headers=auth_headers(),
    )

    assert response.status_code == 400
    assert response.json()["error"] == {
        "code": "invalid_request",
        "message": "name must be a non-empty string",
        "field": "name",
    }


def test_missing_agent_uses_same_error_envelope():
    client = make_client()

    response = client.get(
        "/api/v2/agents/00000000-0000-0000-0000-000000000000",
        headers=auth_headers(),
    )

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "not_found",
            "message": "Agent not found",
        }
    }


def test_authorized_request_still_registers_and_reads_agent():
    client = make_client()

    create_response = client.post(
        "/api/v2/agents",
        params={"name": "worker-one", "agent_type": "worker.processor"},
        headers=auth_headers(),
    )

    assert create_response.status_code == 200
    agent_id = create_response.json()["agent_id"]

    read_response = client.get(f"/api/v2/agents/{agent_id}", headers=auth_headers())

    assert read_response.status_code == 200
    assert read_response.json()["id"] == agent_id
    assert read_response.json()["name"] == "worker-one"
