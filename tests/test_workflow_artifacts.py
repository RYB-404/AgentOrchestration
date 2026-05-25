import pytest
import importlib.util
from pathlib import Path


_WORKFLOW_PATH = Path(__file__).resolve().parents[1] / "src" / "orchestrator" / "workflow.py"
_SPEC = importlib.util.spec_from_file_location("workflow", _WORKFLOW_PATH)
_WORKFLOW = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_WORKFLOW)
WorkflowArtifactCleanupPlanner = _WORKFLOW.WorkflowArtifactCleanupPlanner


def test_cleanup_is_deferred_while_retry_dependency_is_pending():
    planner = WorkflowArtifactCleanupPlanner()
    planner.register_artifact("artifact-1", produced_by="step-build")
    planner.mark_retry_pending("step-test", depends_on_artifacts={"artifact-1"})

    decision = planner.request_cleanup("artifact-1", reason="step-failed")

    assert decision.allowed is False
    assert decision.reason == "retry_dependency_pending"
    assert planner.pending_artifacts() == {"artifact-1"}
    assert planner.audit_log()[-1] == {
        "event": "cleanup_deferred",
        "artifact_id": "artifact-1",
        "reason": "retry_dependency_pending",
        "dependent_step": "step-test",
    }


def test_cleanup_is_allowed_after_retry_dependency_finishes():
    planner = WorkflowArtifactCleanupPlanner()
    planner.register_artifact("artifact-1", produced_by="step-build")
    planner.mark_retry_pending("step-test", depends_on_artifacts={"artifact-1"})
    planner.mark_retry_resolved("step-test")

    decision = planner.request_cleanup("artifact-1", reason="retry-complete")

    assert decision.allowed is True
    assert decision.reason == "cleanup_allowed"
    assert planner.pending_artifacts() == set()


def test_unknown_artifact_cleanup_is_rejected_before_state_change():
    planner = WorkflowArtifactCleanupPlanner()

    decision = planner.request_cleanup("missing", reason="manual")

    assert decision.allowed is False
    assert decision.reason == "unknown_artifact"
    assert planner.pending_artifacts() == set()
