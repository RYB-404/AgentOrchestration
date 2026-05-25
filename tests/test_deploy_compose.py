import pytest

from src.deploy.compose import ComposeProfileError, validate_compose_profile


def test_rejects_host_docker_socket_mount_in_worker_profile():
    compose = {
        "services": {
            "worker": {
                "profiles": ["worker"],
                "volumes": ["/var/run/docker.sock:/var/run/docker.sock"],
            }
        }
    }

    with pytest.raises(ComposeProfileError, match="host docker socket"):
        validate_compose_profile(compose, profile="worker")


def test_allows_named_volumes_without_host_socket_access():
    compose = {
        "services": {
            "worker": {
                "profiles": ["worker"],
                "volumes": ["worker-cache:/cache"],
            }
        },
        "volumes": {"worker-cache": {}},
    }

    assert validate_compose_profile(compose, profile="worker") == {
        "services_checked": ["worker"],
        "blocked_mounts": [],
    }


def test_rejects_long_form_host_socket_mount():
    compose = {
        "services": {
            "worker": {
                "profiles": ["worker"],
                "volumes": [
                    {
                        "type": "bind",
                        "source": "/var/run/docker.sock",
                        "target": "/var/run/docker.sock",
                    }
                ],
            }
        }
    }

    with pytest.raises(ComposeProfileError, match="worker"):
        validate_compose_profile(compose, profile="worker")
