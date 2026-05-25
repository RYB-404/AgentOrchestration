"""Dockerfile policy checks for release images."""

import re
from typing import Dict, List


class DockerfilePolicyError(ValueError):
    """Raised when final image layers expose build arguments."""


def validate_final_stage_no_build_args(dockerfile: str) -> Dict[str, object]:
    stages = _split_stages(dockerfile)
    if not stages:
        raise DockerfilePolicyError("Dockerfile must contain at least one FROM stage")

    build_args = _collect_build_args(stages[:-1])
    final_stage = stages[-1]
    blocked = []
    for line in final_stage:
        instruction = line.strip()
        upper = instruction.upper()
        if upper.startswith("ARG "):
            blocked.append(instruction)
            continue
        if upper.startswith(("ENV ", "LABEL ")) and _references_build_arg(instruction, build_args):
            blocked.append(instruction)

    if blocked:
        raise DockerfilePolicyError(
            "final stage exposes build arguments: " + ", ".join(blocked)
        )
    return {"stages": len(stages), "final_stage": str(len(stages) - 1), "blocked": blocked}


def _split_stages(dockerfile: str) -> List[List[str]]:
    stages: List[List[str]] = []
    current: List[str] = []
    for raw_line in dockerfile.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.upper().startswith("FROM "):
            if current:
                stages.append(current)
            current = [line]
        elif current:
            current.append(line)
    if current:
        stages.append(current)
    return stages


def _collect_build_args(stages: List[List[str]]) -> List[str]:
    args = []
    for stage in stages:
        for line in stage:
            if line.upper().startswith("ARG "):
                name = line[4:].split("=", 1)[0].strip()
                if name:
                    args.append(name)
    return args


def _references_build_arg(instruction: str, build_args: List[str]) -> bool:
    return any(
        re.search(rf"(\${{{re.escape(arg)}}}|\${re.escape(arg)}\b)", instruction)
        for arg in build_args
    )
