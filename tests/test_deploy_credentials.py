import pytest

from src.deploy.credentials import (
    DeploymentCredentialBroker,
    DeploymentCredentialError,
    DeploymentEnvironment,
)


def test_production_release_requires_matching_approval_before_credential_lease():
    broker = DeploymentCredentialBroker()
    broker.register_identity(
        environment=DeploymentEnvironment.PRODUCTION,
        identity_id="prod-ci",
        secret="prod-secret",
        allowed_releases={"release-123"},
    )

    with pytest.raises(DeploymentCredentialError, match="approval"):
        broker.issue_lease(
            environment=DeploymentEnvironment.PRODUCTION,
            release_id="release-123",
            requester="deploy-bot",
        )

    broker.approve_production_release(
        release_id="release-123",
        approver="ops-lead",
        approval_id="approval-1",
    )

    lease = broker.issue_lease(
        environment=DeploymentEnvironment.PRODUCTION,
        release_id="release-123",
        requester="deploy-bot",
    )

    assert lease.environment is DeploymentEnvironment.PRODUCTION
    assert lease.release_id == "release-123"
    assert lease.identity_id == "prod-ci"
    assert lease.secret == "prod-secret"


def test_credential_lease_cannot_cross_environment_or_release_boundary():
    broker = DeploymentCredentialBroker()
    broker.register_identity(
        environment=DeploymentEnvironment.STAGING,
        identity_id="staging-ci",
        secret="staging-secret",
        allowed_releases={"release-123"},
    )
    lease = broker.issue_lease(
        environment=DeploymentEnvironment.STAGING,
        release_id="release-123",
        requester="deploy-bot",
    )

    with pytest.raises(DeploymentCredentialError, match="environment"):
        broker.consume_lease(
            lease.lease_id,
            environment=DeploymentEnvironment.PRODUCTION,
            release_id="release-123",
        )

    with pytest.raises(DeploymentCredentialError, match="release"):
        broker.consume_lease(
            lease.lease_id,
            environment=DeploymentEnvironment.STAGING,
            release_id="release-999",
        )

    consumed = broker.consume_lease(
        lease.lease_id,
        environment=DeploymentEnvironment.STAGING,
        release_id="release-123",
    )
    assert consumed.secret == "staging-secret"


def test_credential_lease_is_single_use_and_audit_log_redacts_secret():
    broker = DeploymentCredentialBroker()
    broker.register_identity(
        environment=DeploymentEnvironment.STAGING,
        identity_id="staging-ci",
        secret="staging-secret",
    )
    lease = broker.issue_lease(
        environment=DeploymentEnvironment.STAGING,
        release_id="release-abc",
        requester="deploy-bot",
    )

    assert broker.consume_lease(
        lease.lease_id,
        environment=DeploymentEnvironment.STAGING,
        release_id="release-abc",
    )

    with pytest.raises(DeploymentCredentialError, match="used"):
        broker.consume_lease(
            lease.lease_id,
            environment=DeploymentEnvironment.STAGING,
            release_id="release-abc",
        )

    audit = broker.audit_log()
    assert any(entry["event"] == "lease_consumed" for entry in audit)
    assert all("secret" not in entry for entry in audit)
    assert "staging-secret" not in repr(audit)
