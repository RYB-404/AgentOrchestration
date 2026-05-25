"""Compose profile validation for local worker deployments."""

from typing import Dict, List


class ComposeProfileError(ValueError):
    """Raised when a compose profile grants unsafe host access."""


HOST_DOCKER_SOCKET = "/var/run/docker.sock"


def validate_compose_profile(compose: Dict, profile: str = "worker") -> Dict[str, List[str]]:
    services = compose.get("services", {})
    checked = []
    blocked = []
    for service_name, service in services.items():
        if profile not in service.get("profiles", [profile]):
            continue
        checked.append(service_name)
        for volume in service.get("volumes", []):
            if _mounts_host_socket(volume):
                blocked.append(f"{service_name}:{HOST_DOCKER_SOCKET}")

    if blocked:
        raise ComposeProfileError(
            f"profile {profile} mounts host docker socket in {', '.join(blocked)}"
        )
    return {"services_checked": checked, "blocked_mounts": blocked}


def _mounts_host_socket(volume) -> bool:
    if isinstance(volume, str):
        source = volume.split(":", 1)[0]
        return _normalise_path(source) == HOST_DOCKER_SOCKET
    if isinstance(volume, dict):
        source = volume.get("source") or volume.get("src")
        return volume.get("type") == "bind" and _normalise_path(source) == HOST_DOCKER_SOCKET
    return False


def _normalise_path(path) -> str:
    return str(path or "").replace("\\", "/").rstrip("/")
