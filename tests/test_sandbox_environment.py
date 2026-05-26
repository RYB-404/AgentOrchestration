import os

from src.agent.sandbox import AgentSandbox


def test_build_environment_does_not_inherit_unlisted_process_secrets(monkeypatch):
    monkeypatch.setenv("PATH", "/usr/bin")
    monkeypatch.setenv("AO_API_KEY", "secret")

    sandbox = AgentSandbox(env_allowlist={"PATH"})

    env = sandbox.build_environment()
    assert env == {"PATH": "/usr/bin"}


def test_build_environment_applies_explicit_overrides(monkeypatch):
    monkeypatch.setenv("PATH", "/usr/bin")

    sandbox = AgentSandbox(env_allowlist={"PATH"})

    env = sandbox.build_environment({"AO_WORKSPACE_ID": "workspace-a"})
    assert env == {"PATH": "/usr/bin", "AO_WORKSPACE_ID": "workspace-a"}


def test_isolated_environment_restores_parent_environment(monkeypatch):
    monkeypatch.setenv("PATH", "/usr/bin")
    monkeypatch.setenv("AO_API_KEY", "secret")
    sandbox = AgentSandbox(env_allowlist={"PATH"})

    with sandbox.isolated_environment({"AO_WORKSPACE_ID": "workspace-a"}) as env:
        assert dict(env) == {"PATH": "/usr/bin", "AO_WORKSPACE_ID": "workspace-a"}

    assert os.environ["AO_API_KEY"] == "secret"
    assert os.environ["PATH"] == "/usr/bin"
