import pytest

from src.deploy.dockerfile_policy import DockerfilePolicyError, validate_final_stage_no_build_args


def test_rejects_arg_declared_in_final_stage():
    dockerfile = """
    FROM python:3.12 AS builder
    ARG PRIVATE_TOKEN
    RUN echo building
    FROM python:3.12-slim
    ARG PRIVATE_TOKEN
    CMD ["ao"]
    """

    with pytest.raises(DockerfilePolicyError, match="PRIVATE_TOKEN"):
        validate_final_stage_no_build_args(dockerfile)


def test_rejects_env_that_copies_build_arg_into_final_layer():
    dockerfile = """
    FROM python:3.12 AS builder
    ARG BUILD_ID
    FROM python:3.12-slim
    ENV BUILD_ID=$BUILD_ID
    """

    with pytest.raises(DockerfilePolicyError, match="ENV BUILD_ID"):
        validate_final_stage_no_build_args(dockerfile)


def test_allows_builder_args_when_final_stage_uses_static_metadata():
    dockerfile = """
    FROM python:3.12 AS builder
    ARG BUILD_ID
    RUN echo "$BUILD_ID" > /tmp/build-id
    FROM python:3.12-slim
    LABEL org.opencontainers.image.title="agent-orchestration"
    COPY --from=builder /tmp/build-id /app/build-id
    """

    assert validate_final_stage_no_build_args(dockerfile) == {
        "stages": 2,
        "final_stage": "1",
        "blocked": [],
    }
