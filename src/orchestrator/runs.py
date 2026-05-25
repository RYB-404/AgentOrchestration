"""Workspace-scoped orchestration run status service."""

from dataclasses import dataclass
from typing import Dict, Optional
from uuid import UUID, uuid4


class RunAccessError(ValueError):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


@dataclass(frozen=True)
class RunPrincipal:
    workspace_id: str
    role: str


class InMemoryRunStore:
    def __init__(self):
        self._runs: Dict[str, Dict] = {}

    def create_run(self, workspace_id: str, role: str, agent_id: str, task_id: str, status: str = "queued") -> Dict:
        run_id = str(uuid4())
        self._runs[run_id] = {
            "id": run_id,
            "workspace_id": workspace_id,
            "role": role,
            "agent_id": agent_id,
            "task_id": task_id,
            "status": status,
        }
        return dict(self._runs[run_id])

    def get_run(self, run_id: str) -> Optional[Dict]:
        run = self._runs.get(run_id)
        return dict(run) if run else None


class OrchestrationRunService:
    def __init__(self, store: Optional[InMemoryRunStore] = None):
        self.store = store or InMemoryRunStore()

    def get_status(self, run_id: str, principal: RunPrincipal) -> Dict:
        self._validate_run_id(run_id)
        self._validate_principal(principal)

        run = self.store.get_run(run_id)
        if not run:
            raise RunAccessError(404, "Run not found")

        if run["workspace_id"] != principal.workspace_id or run["role"] != principal.role:
            raise RunAccessError(403, "Run is not accessible for this workspace and role")

        return {
            "run_id": run["id"],
            "status": run["status"],
            "workspace_id": run["workspace_id"],
            "role": run["role"],
        }

    def _validate_run_id(self, run_id: str) -> None:
        try:
            UUID(run_id)
        except (TypeError, ValueError):
            raise RunAccessError(400, "Malformed run id")

    def _validate_principal(self, principal: RunPrincipal) -> None:
        if not principal.workspace_id:
            raise RunAccessError(400, "Workspace scope is required")
        if not principal.role:
            raise RunAccessError(400, "Active role is required")
