"""Container release image target validation."""

import re
from dataclasses import dataclass
from typing import Callable, Dict, Set


TAG_PATTERN = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$")
NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")
REGISTRY_PATTERN = re.compile(r"^[a-z0-9.-]+(?::[0-9]+)?$")


@dataclass(frozen=True)
class ReleaseImageTarget:
    registry: str
    namespace: str
    image: str
    tag: str

    @property
    def full_namespace(self) -> str:
        return f"{self.registry}/{self.namespace}"

    @property
    def reference(self) -> str:
        return f"{self.full_namespace}/{self.image}:{self.tag}"


class ReleaseTargetValidator:
    def __init__(
        self,
        allowed_namespaces: Set[str],
        credential_resolver: Callable[[ReleaseImageTarget], object],
    ):
        self.allowed_namespaces = set(allowed_namespaces)
        self.credential_resolver = credential_resolver

    def validate_before_push(
        self, target: ReleaseImageTarget
    ) -> Dict[str, str]:
        self._validate_tag(target.tag)
        self._validate_registry_namespace(target)
        self._validate_image(target.image)

        self.credential_resolver(target)
        return {
            "registry": target.registry,
            "namespace": target.namespace,
            "image": target.image,
            "tag": target.tag,
            "approved_target": target.reference,
        }

    def _validate_tag(self, tag: str) -> None:
        if not TAG_PATTERN.fullmatch(tag):
            raise ValueError("invalid image tag")

    def _validate_registry_namespace(self, target: ReleaseImageTarget) -> None:
        if not REGISTRY_PATTERN.fullmatch(target.registry):
            raise ValueError("invalid registry host")
        if not NAME_PATTERN.fullmatch(target.namespace):
            raise ValueError("invalid registry namespace")
        if target.full_namespace not in self.allowed_namespaces:
            raise ValueError("unapproved registry namespace")

    def _validate_image(self, image: str) -> None:
        if not NAME_PATTERN.fullmatch(image):
            raise ValueError("invalid image name")
