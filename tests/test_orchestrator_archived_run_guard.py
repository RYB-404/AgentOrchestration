import importlib.util
import sys
import types
from enum import Enum
from pathlib import Path


class AgentStatus(Enum):
    RUNNING = "running"
    PAUSED = "paused"


class AgentRegistry:
    def get(self, agent_id):
        return None

    def update_status(self, agent_id, status):
        return True


agent_module = types.ModuleType("src.agent")
agent_module.AgentRegistry = AgentRegistry
agent_module.AgentStatus = AgentStatus
sys.modules["src.agent"] = agent_module

MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "src" / "orchestrator" / "engine.py"
)
SPEC = importlib.util.spec_from_file_location(
    "orchestrator_engine",
    MODULE_PATH,
)
orchestrator_engine = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(orchestrator_engine)
OrchestrationEngine = orchestrator_engine.OrchestrationEngine


def test_rejects_late_worker_event_for_archived_run():
    engine = OrchestrationEngine()
    run_id = "run-1"
    engine.register_run(run_id, attempt=2, revision=4)
    engine.archive_run(run_id)

    accepted = engine.apply_worker_event(
        run_id,
        {
            "type": "task.completed",
            "attempt": 2,
            "revision": 4,
            "status": "completed",
            "payload": {"secret": "do-not-log"},
        },
    )

    assert not accepted
    assert engine.get_run_state(run_id)["status"] == "archived"
    assert engine.get_run_state(run_id)["revision"] == 4
    assert engine.audit_log[-1] == {
        "run_id": run_id,
        "event_type": "task.completed",
        "decision": "rejected",
        "reason": "archived_run",
        "attempt": 2,
        "revision": 4,
    }


def test_rejects_stale_attempt_and_revision_before_archiving():
    engine = OrchestrationEngine()
    run_id = "run-2"
    engine.register_run(run_id, attempt=3, revision=8)

    stale_attempt = engine.apply_worker_event(
        run_id,
        {
            "type": "task.completed",
            "attempt": 2,
            "revision": 8,
            "status": "completed",
        },
    )
    stale_revision = engine.apply_worker_event(
        run_id,
        {
            "type": "task.completed",
            "attempt": 3,
            "revision": 7,
            "status": "completed",
        },
    )

    assert not stale_attempt
    assert not stale_revision
    assert engine.get_run_state(run_id)["status"] == "active"
    assert [entry["reason"] for entry in engine.audit_log] == [
        "stale_attempt",
        "stale_revision",
    ]


def test_accepts_current_worker_event_and_advances_revision():
    engine = OrchestrationEngine()
    run_id = "run-3"
    engine.register_run(run_id, attempt=1, revision=1)

    accepted = engine.apply_worker_event(
        run_id,
        {
            "type": "task.completed",
            "attempt": 1,
            "revision": 1,
            "status": "completed",
        },
    )

    assert accepted
    assert engine.get_run_state(run_id) == {
        "attempt": 1,
        "revision": 2,
        "status": "completed",
    }
