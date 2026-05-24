"""Signed deployment bundle promotion."""

import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Callable, Dict, List


@dataclass(frozen=True)
class PromotionResult:
    accepted: bool
    reason: str


class DeploymentBundlePromoter:
    def __init__(
        self,
        trusted_secret: str,
        credential_resolver: Callable[[str], object],
        history_limit: int = 100,
    ):
        self.trusted_secret = trusted_secret.encode()
        self.credential_resolver = credential_resolver
        self.history_limit = history_limit
        self.history: List[Dict[str, str]] = []

    def digest(self, bundle: Dict) -> str:
        canonical = self._canonical_bundle(bundle)
        payload = json.dumps(
            canonical,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        return "sha256:" + hashlib.sha256(payload).hexdigest()

    def sign(self, bundle: Dict) -> str:
        digest = self.digest(bundle)
        signature = hmac.new(
            self.trusted_secret,
            digest.encode(),
            hashlib.sha256,
        ).hexdigest()
        return "sha256:" + signature

    def promote(self, bundle: Dict) -> PromotionResult:
        environment = str(bundle.get("environment", "unknown"))
        signature = bundle.get("signature")
        bundle_digest = self.digest(bundle)

        if not signature:
            self._record(environment, bundle_digest, "", "missing_signature")
            return PromotionResult(False, "missing_signature")

        expected_signature = self.sign(bundle)
        if not hmac.compare_digest(signature, expected_signature):
            self._record(
                environment,
                bundle_digest,
                str(signature),
                "invalid_signature",
            )
            return PromotionResult(False, "invalid_signature")

        self._record(environment, bundle_digest, str(signature), "verified")
        self.credential_resolver(environment)
        return PromotionResult(True, "verified")

    def _record(
        self,
        environment: str,
        bundle_digest: str,
        signature: str,
        verification: str,
    ) -> None:
        self.history.append(
            {
                "environment": environment,
                "bundle_digest": bundle_digest,
                "signature": signature,
                "verification": verification,
            }
        )
        if len(self.history) > self.history_limit:
            self.history = self.history[-self.history_limit:]

    def _canonical_bundle(self, bundle: Dict) -> Dict:
        canonical = dict(bundle)
        canonical.pop("signature", None)
        return canonical
