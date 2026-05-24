from src.deployment.bundles import DeploymentBundlePromoter


def _bundle(signature=None):
    bundle = {
        "name": "agent-worker",
        "version": "2026.05.24",
        "environment": "staging",
        "artifact": {
            "image": "registry.example.com/agent-worker:2026.05.24",
            "digest": "sha256:abc123",
        },
    }
    if signature is not None:
        bundle["signature"] = signature
    return bundle


def test_unsigned_bundle_is_rejected_before_credentials_are_requested():
    credential_calls = []
    promoter = DeploymentBundlePromoter(
        trusted_secret="release-secret",
        credential_resolver=lambda environment: credential_calls.append(
            environment
        ),
    )

    result = promoter.promote(_bundle())

    assert not result.accepted
    assert result.reason == "missing_signature"
    assert credential_calls == []
    assert promoter.history[-1]["verification"] == "missing_signature"


def test_invalid_signature_is_rejected_before_credentials_are_requested():
    credential_calls = []
    promoter = DeploymentBundlePromoter(
        trusted_secret="release-secret",
        credential_resolver=lambda environment: credential_calls.append(
            environment
        ),
    )

    result = promoter.promote(_bundle(signature="sha256:not-valid"))

    assert not result.accepted
    assert result.reason == "invalid_signature"
    assert credential_calls == []
    assert promoter.history[-1]["verification"] == "invalid_signature"


def test_signed_bundle_is_promoted_and_records_digest_history():
    credential_calls = []
    promoter = DeploymentBundlePromoter(
        trusted_secret="release-secret",
        credential_resolver=lambda environment: credential_calls.append(
            environment
        ),
    )
    bundle = _bundle()
    bundle["signature"] = promoter.sign(bundle)

    result = promoter.promote(bundle)

    assert result.accepted
    assert result.reason == "verified"
    assert credential_calls == ["staging"]
    assert promoter.history[-1] == {
        "environment": "staging",
        "bundle_digest": promoter.digest(bundle),
        "signature": bundle["signature"],
        "verification": "verified",
    }
