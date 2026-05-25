"""Release rollback ledger with paired configuration snapshots."""

from typing import Callable, Dict, List, Optional


Snapshot = Dict[str, str]


class ReleaseRollbackLedger:
    def __init__(
        self,
        restore_callback: Optional[Callable[[Snapshot], object]] = None,
        verification_callback: Optional[Callable[[Snapshot], object]] = None,
    ):
        self._history: List[Snapshot] = []
        self._current: Optional[Snapshot] = None
        self.restore_callback = restore_callback or (lambda snapshot: None)
        self.verification_callback = verification_callback or (
            lambda snapshot: True
        )

    def record_release(
        self,
        version: str,
        image_digest: str,
        config_digest: str,
    ) -> Snapshot:
        snapshot = {
            "version": version,
            "image_digest": image_digest,
            "config_digest": config_digest,
        }
        self._history.append(snapshot)
        self._current = snapshot
        return dict(snapshot)

    def current_snapshot(self) -> Optional[Snapshot]:
        if self._current is None:
            return None
        return dict(self._current)

    def rollback_to(self, version: str) -> Snapshot:
        target = self._find_snapshot(version)
        previous_current = self._current

        self.restore_callback(dict(target))
        verification_result = self.verification_callback(dict(target))
        if verification_result is False:
            self._current = previous_current
            raise RuntimeError("rollback verification failed")

        self._current = target
        return dict(target)

    def _find_snapshot(self, version: str) -> Snapshot:
        for snapshot in reversed(self._history):
            if snapshot["version"] == version:
                return snapshot
        raise ValueError("unknown release version")
