from src.sdk import client as client_module
from src.sdk.client import OrchestratorClient


class FakeResponse:
    def __init__(self, status, body=b""):
        self.status = status
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.body


def test_request_returns_empty_dict_for_204(monkeypatch):
    monkeypatch.setattr(client_module, "urlopen", lambda _req: FakeResponse(204))
    client = OrchestratorClient(base_url="http://example.test", api_key="token")

    assert client.delete_agent("agent-1") == {}


def test_request_returns_empty_dict_for_empty_200_body(monkeypatch):
    monkeypatch.setattr(client_module, "urlopen", lambda _req: FakeResponse(200, b""))
    client = OrchestratorClient(base_url="http://example.test", api_key="token")

    assert client.get_agent("agent-1") == {}


def test_request_decodes_json_body(monkeypatch):
    monkeypatch.setattr(client_module, "urlopen", lambda _req: FakeResponse(200, b'{"ok": true}'))
    client = OrchestratorClient(base_url="http://example.test", api_key="token")

    assert client.get_agent("agent-1") == {"ok": True}
