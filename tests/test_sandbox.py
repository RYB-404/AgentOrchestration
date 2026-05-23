import pytest

from src.common.config import Config
from src.agent.sandbox import ResourceLimits


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"cpu_time": 0}, "cpu_time must be a positive integer"),
        ({"cpu_time": -1}, "cpu_time must be a positive integer"),
        ({"cpu_time": "60"}, "cpu_time must be a positive integer"),
        ({"memory_mb": 0}, "memory_mb must be a positive integer"),
        ({"memory_mb": -1}, "memory_mb must be a positive integer"),
        ({"memory_mb": "512"}, "memory_mb must be a positive integer"),
        ({"disk_mb": 0}, "disk_mb must be a positive integer"),
        ({"disk_mb": -1}, "disk_mb must be a positive integer"),
        ({"disk_mb": "1024"}, "disk_mb must be a positive integer"),
    ],
)
def test_resource_limits_reject_invalid_values(kwargs, message):
    with pytest.raises(ValueError, match=message):
        ResourceLimits(**kwargs)


def test_config_sandbox_resource_limits_must_be_positive_and_numeric(tmp_path):
    config_file = tmp_path / "config.json"
    config_file.write_text(
        '{"sandbox": {"cpu_time": 30, "memory_mb": -256, "disk_mb": 100}}'
    )
    config = Config(str(config_file))
    limits = config.get("sandbox")

    with pytest.raises(ValueError, match="memory_mb must be a positive integer"):
        ResourceLimits(**limits)
