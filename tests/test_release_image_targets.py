import pytest

from src.release.images import ReleaseImageTarget, ReleaseTargetValidator


def test_rejects_unapproved_registry_namespace_before_credentials():
    credential_calls = []
    validator = ReleaseTargetValidator(
        allowed_namespaces={"ghcr.io/orchestration-agent"},
        credential_resolver=lambda target: credential_calls.append(target),
    )
    target = ReleaseImageTarget(
        registry="ghcr.io",
        namespace="attacker",
        image="worker",
        tag="v2.4.1",
    )

    with pytest.raises(ValueError, match="unapproved registry namespace"):
        validator.validate_before_push(target)

    assert credential_calls == []


def test_rejects_invalid_tag_before_credentials():
    credential_calls = []
    validator = ReleaseTargetValidator(
        allowed_namespaces={"ghcr.io/orchestration-agent"},
        credential_resolver=lambda target: credential_calls.append(target),
    )
    target = ReleaseImageTarget(
        registry="ghcr.io",
        namespace="orchestration-agent",
        image="worker",
        tag="../latest",
    )

    with pytest.raises(ValueError, match="invalid image tag"):
        validator.validate_before_push(target)

    assert credential_calls == []


def test_approved_target_logs_safe_release_summary():
    credential_calls = []
    validator = ReleaseTargetValidator(
        allowed_namespaces={"ghcr.io/orchestration-agent"},
        credential_resolver=lambda target: credential_calls.append(
            target.full_namespace
        ),
    )
    target = ReleaseImageTarget(
        registry="ghcr.io",
        namespace="orchestration-agent",
        image="worker",
        tag="v2.4.1",
    )

    summary = validator.validate_before_push(target)

    assert credential_calls == ["ghcr.io/orchestration-agent"]
    assert summary == {
        "registry": "ghcr.io",
        "namespace": "orchestration-agent",
        "image": "worker",
        "tag": "v2.4.1",
        "approved_target": "ghcr.io/orchestration-agent/worker:v2.4.1",
    }
    assert "token" not in str(summary).lower()
