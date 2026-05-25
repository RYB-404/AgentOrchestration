from fastapi.testclient import TestClient

from src.api.routes import run_service
from src.api.server import create_app
from src.orchestrator.runs import InMemoryRunStore, OrchestrationRunService


def make_client(store=None):
    run_service.store = store or InMemoryRunStore()
    return TestClient(create_app())


def auth_headers(workspace_id="workspace-a", role="operator"):
    return {
        "Authorization": "Bearer test-token",
        "X-Workspace-ID": workspace_id,
        "X-Active-Role": role,
    }


def test_run_status_polling_allows_owner_workspace_and_role():
    store = InMemoryRunStore()
    run = store.create_run("workspace-a", "operator", "agent-1", "task-1")
    client = make_client(store)

    response = client.get(f"/api/v2/runs/{run['id']}/status", headers=auth_headers())

    assert response.status_code == 200
    assert response.json() == {
        "run_id": run["id"],
        "status": "queued",
        "workspace_id": "workspace-a",
        "role": "operator",
    }


def test_run_status_polling_rejects_wrong_workspace():
    store = InMemoryRunStore()
    run = store.create_run("workspace-a", "operator", "agent-1", "task-1")
    client = make_client(store)

    response = client.get(
        f"/api/v2/runs/{run['id']}/status",
        headers=auth_headers(workspace_id="workspace-b"),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Run is not accessible for this workspace and role"


def test_run_status_polling_rejects_wrong_role():
    store = InMemoryRunStore()
    run = store.create_run("workspace-a", "operator", "agent-1", "task-1")
    client = make_client(store)

    response = client.get(
        f"/api/v2/runs/{run['id']}/status",
        headers=auth_headers(role="viewer"),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Run is not accessible for this workspace and role"


def test_run_status_polling_rejects_malformed_run_id_before_lookup():
    class ExplodingStore(InMemoryRunStore):
        def get_run(self, run_id):
            raise AssertionError("store lookup must not run for malformed run ids")

    client = make_client(ExplodingStore())

    response = client.get("/api/v2/runs/not-a-run/status", headers=auth_headers())

    assert response.status_code == 400
    assert response.json()["detail"] == "Malformed run id"


def test_run_status_polling_rejects_missing_workspace_before_lookup():
    class ExplodingStore(InMemoryRunStore):
        def get_run(self, run_id):
            raise AssertionError("store lookup must not run without workspace scope")

    client = make_client(ExplodingStore())

    response = client.get(
        "/api/v2/runs/7f3f02b2-c79d-4a85-91f8-44e3ce784c50/status",
        headers={"Authorization": "Bearer test-token", "X-Active-Role": "operator"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Workspace scope is required"
