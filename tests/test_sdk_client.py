import json
from io import BytesIO
from urllib.error import HTTPError

from src.sdk import client as sdk_client
from src.sdk.client import OrchestratorClient


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return json.dumps(self.payload).encode()


def transient_error(status):
    return HTTPError(
        url="https://orchestrator.example/api/v2/agents",
        code=status,
        msg="temporary gateway failure",
        hdrs={},
        fp=BytesIO(b""),
    )


def test_get_request_retries_transient_failures_when_opted_in(monkeypatch):
    calls = []
    responses = [
        transient_error(503),
        transient_error(502),
        FakeResponse({"agents": [{"id": "agent-1"}]}),
    ]

    def fake_urlopen(request):
        calls.append(request)
        response = responses.pop(0)
        if isinstance(response, HTTPError):
            raise response
        return response

    monkeypatch.setattr(sdk_client, "urlopen", fake_urlopen)

    client = OrchestratorClient(
        base_url="https://orchestrator.example",
        api_key="secret",
        get_retry_count=2,
        get_retry_backoff=0,
    )

    assert client.list_agents() == {"agents": [{"id": "agent-1"}]}
    assert len(calls) == 3
    assert all(call.get_method() == "GET" for call in calls)


def test_get_request_does_not_retry_by_default(monkeypatch):
    calls = []

    def fake_urlopen(request):
        calls.append(request)
        raise transient_error(503)

    monkeypatch.setattr(sdk_client, "urlopen", fake_urlopen)

    client = OrchestratorClient(
        base_url="https://orchestrator.example",
        api_key="secret",
    )

    assert client.list_agents() == {"error": 503, "message": "temporary gateway failure"}
    assert len(calls) == 1


def test_post_request_does_not_retry_transient_failure(monkeypatch):
    calls = []

    def fake_urlopen(request):
        calls.append(request)
        raise transient_error(503)

    monkeypatch.setattr(sdk_client, "urlopen", fake_urlopen)

    client = OrchestratorClient(
        base_url="https://orchestrator.example",
        api_key="secret",
        get_retry_count=2,
        get_retry_backoff=0,
    )

    assert client.register_agent("worker", "python") == {
        "error": 503,
        "message": "temporary gateway failure",
    }
    assert len(calls) == 1
