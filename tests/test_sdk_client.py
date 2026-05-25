import pytest

from src.sdk.client import OrchestratorClient


class CapturingClient(OrchestratorClient):
    def __init__(self):
        super().__init__(base_url="http://example.test", api_key="test")
        self.last_request = None

    def _request(self, method, path, data=None):
        self.last_request = {"method": method, "path": path, "data": data}
        return {"ok": True}


def test_register_agent_maps_none_config_to_empty_dict():
    client = CapturingClient()

    client.register_agent("agent", "worker.processor")

    assert client.last_request["data"]["config"] == {}


def test_register_agent_accepts_mapping_config():
    client = CapturingClient()
    config = {"retries": 2, "labels": {"tier": "gold"}}

    client.register_agent("agent", "worker.processor", config=config)

    assert client.last_request["data"]["config"] == config


@pytest.mark.parametrize("invalid_config", ["not-a-dict", ["a", "list"], ("tuple",), 42])
def test_register_agent_rejects_non_mapping_config(invalid_config):
    client = CapturingClient()

    with pytest.raises(TypeError, match="config must be a mapping"):
        client.register_agent("agent", "worker.processor", config=invalid_config)

    assert client.last_request is None
