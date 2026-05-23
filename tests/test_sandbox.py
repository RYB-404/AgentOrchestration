import pytest

from src.agent.sandbox import (
    AgentSandbox,
    ResourceLimits,
    UnsupportedResourceLimitError,
)


def test_default_resource_limits_do_not_claim_disk_quota():
    limits = ResourceLimits()

    assert limits.disk_mb is None


def test_apply_limits_fails_fast_when_disk_limit_requested(tmp_path):
    sandbox = AgentSandbox(base_path=str(tmp_path))

    with pytest.raises(UnsupportedResourceLimitError, match="disk_mb is not enforced"):
        sandbox.apply_limits("agent-1", ResourceLimits(disk_mb=100))


def test_apply_limits_allows_cpu_and_memory_without_disk_limit(monkeypatch, tmp_path):
    calls = []

    class FakeResource:
        RLIMIT_CPU = "cpu"
        RLIMIT_AS = "as"
        error = OSError

        @staticmethod
        def setrlimit(kind, limits):
            calls.append((kind, limits))

    monkeypatch.setattr("src.agent.sandbox.resource", FakeResource)
    sandbox = AgentSandbox(base_path=str(tmp_path))

    sandbox.apply_limits("agent-1", ResourceLimits(cpu_time=10, memory_mb=64))

    assert calls == [
        ("cpu", (10, 10)),
        ("as", (64 * 1024 * 1024, 64 * 1024 * 1024)),
    ]
