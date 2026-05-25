from src.release.rollback import ReleaseRollbackLedger


def test_records_image_and_configuration_digests_together():
    ledger = ReleaseRollbackLedger()

    ledger.record_release(
        version="v2.4.0",
        image_digest="sha256:image-a",
        config_digest="sha256:config-a",
    )

    assert ledger.current_snapshot() == {
        "version": "v2.4.0",
        "image_digest": "sha256:image-a",
        "config_digest": "sha256:config-a",
    }


def test_rollback_restores_matching_configuration_snapshot():
    restored = []
    verified = []
    ledger = ReleaseRollbackLedger(
        restore_callback=lambda snapshot: restored.append(snapshot),
        verification_callback=lambda snapshot: verified.append(snapshot),
    )
    ledger.record_release("v2.4.0", "sha256:image-a", "sha256:config-a")
    ledger.record_release("v2.5.0", "sha256:image-b", "sha256:config-b")

    snapshot = ledger.rollback_to("v2.4.0")

    assert snapshot == {
        "version": "v2.4.0",
        "image_digest": "sha256:image-a",
        "config_digest": "sha256:config-a",
    }
    assert ledger.current_snapshot() == snapshot
    assert restored == [snapshot]
    assert verified == [snapshot]


def test_rollback_refuses_unverified_startup_and_keeps_current_release():
    restored = []
    ledger = ReleaseRollbackLedger(
        restore_callback=lambda snapshot: restored.append(snapshot),
        verification_callback=lambda snapshot: False,
    )
    ledger.record_release("v2.4.0", "sha256:image-a", "sha256:config-a")
    ledger.record_release("v2.5.0", "sha256:image-b", "sha256:config-b")

    try:
        ledger.rollback_to("v2.4.0")
    except RuntimeError as exc:
        assert str(exc) == "rollback verification failed"
    else:
        raise AssertionError("rollback should fail")

    assert ledger.current_snapshot()["version"] == "v2.5.0"
    assert restored == [
        {
            "version": "v2.4.0",
            "image_digest": "sha256:image-a",
            "config_digest": "sha256:config-a",
        }
    ]
