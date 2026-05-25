"""Environment-scoped deployment credentials."""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Iterable, List, Optional, Set
from uuid import uuid4


class DeploymentCredentialError(ValueError):
    """Raised when a deployment credential cannot be issued or consumed."""


class DeploymentEnvironment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass(frozen=True)
class DeploymentIdentity:
    environment: DeploymentEnvironment
    identity_id: str
    secret: str
    allowed_releases: Optional[Set[str]] = None


@dataclass(frozen=True)
class ProductionApproval:
    release_id: str
    approver: str
    approval_id: str


@dataclass
class CredentialLease:
    lease_id: str
    environment: DeploymentEnvironment
    release_id: str
    identity_id: str
    secret: str
    requester: str
    approval_id: Optional[str] = None
    used: bool = False


class DeploymentCredentialBroker:
    """Issues one-use deployment credentials bound to an environment and release."""

    def __init__(self):
        self._identities: Dict[DeploymentEnvironment, DeploymentIdentity] = {}
        self._approvals: Dict[str, ProductionApproval] = {}
        self._leases: Dict[str, CredentialLease] = {}
        self._audit: List[Dict[str, str]] = []

    def register_identity(
        self,
        environment: DeploymentEnvironment,
        identity_id: str,
        secret: str,
        allowed_releases: Optional[Iterable[str]] = None,
    ) -> None:
        self._identities[environment] = DeploymentIdentity(
            environment=environment,
            identity_id=identity_id,
            secret=secret,
            allowed_releases=set(allowed_releases) if allowed_releases is not None else None,
        )
        self._record("identity_registered", environment, identity_id=identity_id)

    def approve_production_release(self, release_id: str, approver: str, approval_id: str) -> None:
        self._approvals[release_id] = ProductionApproval(
            release_id=release_id,
            approver=approver,
            approval_id=approval_id,
        )
        self._record(
            "production_release_approved",
            DeploymentEnvironment.PRODUCTION,
            release_id=release_id,
            approver=approver,
            approval_id=approval_id,
        )

    def issue_lease(
        self,
        environment: DeploymentEnvironment,
        release_id: str,
        requester: str,
    ) -> CredentialLease:
        identity = self._identities.get(environment)
        if identity is None:
            raise DeploymentCredentialError(f"no identity registered for {environment.value} environment")
        if identity.allowed_releases is not None and release_id not in identity.allowed_releases:
            raise DeploymentCredentialError(f"release {release_id} is not allowed for {environment.value}")

        approval_id = None
        if environment is DeploymentEnvironment.PRODUCTION:
            approval = self._approvals.get(release_id)
            if approval is None:
                raise DeploymentCredentialError(f"production release {release_id} requires approval")
            approval_id = approval.approval_id

        lease = CredentialLease(
            lease_id=str(uuid4()),
            environment=environment,
            release_id=release_id,
            identity_id=identity.identity_id,
            secret=identity.secret,
            requester=requester,
            approval_id=approval_id,
        )
        self._leases[lease.lease_id] = lease
        self._record(
            "lease_issued",
            environment,
            release_id=release_id,
            identity_id=identity.identity_id,
            requester=requester,
            approval_id=approval_id,
            lease_id=lease.lease_id,
        )
        return lease

    def consume_lease(
        self,
        lease_id: str,
        environment: DeploymentEnvironment,
        release_id: str,
    ) -> CredentialLease:
        lease = self._leases.get(lease_id)
        if lease is None:
            raise DeploymentCredentialError("credential lease not found")
        if lease.environment is not environment:
            raise DeploymentCredentialError("credential lease environment does not match deployment")
        if lease.release_id != release_id:
            raise DeploymentCredentialError("credential lease release does not match deployment")
        if lease.used:
            raise DeploymentCredentialError("credential lease already used")

        lease.used = True
        self._record(
            "lease_consumed",
            environment,
            release_id=release_id,
            identity_id=lease.identity_id,
            lease_id=lease_id,
        )
        return lease

    def audit_log(self) -> List[Dict[str, str]]:
        return [dict(entry) for entry in self._audit]

    def _record(self, event: str, environment: DeploymentEnvironment, **fields: Optional[str]) -> None:
        entry = {"event": event, "environment": environment.value}
        entry.update({key: value for key, value in fields.items() if value is not None})
        self._audit.append(entry)
