from src.agent.sandbox import AgentSandbox


def test_get_path_returns_none_when_tracked_sandbox_is_missing(tmp_path):
    sandbox = AgentSandbox(base_path=str(tmp_path))
    sandbox_path = sandbox.create("agent-1")
    sandbox_path.rmdir()

    assert sandbox.get_path("agent-1") is None
    assert "agent-1" not in sandbox._sandboxes


def test_get_path_returns_none_when_tracked_path_leaves_base(tmp_path):
    sandbox = AgentSandbox(base_path=str(tmp_path / "base"))
    outside_path = tmp_path / "outside"
    outside_path.mkdir()
    sandbox._sandboxes["agent-1"] = outside_path

    assert sandbox.get_path("agent-1") is None
    assert "agent-1" not in sandbox._sandboxes


def test_get_path_returns_existing_path_inside_base(tmp_path):
    sandbox = AgentSandbox(base_path=str(tmp_path))
    sandbox_path = sandbox.create("agent-1")

    assert sandbox.get_path("agent-1") == sandbox_path
