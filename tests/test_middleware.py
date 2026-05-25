from datetime import datetime, timedelta, timezone
import importlib.util
import asyncio
from pathlib import Path

import pytest
from starlette.requests import Request
from starlette.responses import Response

MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "src" / "api" / "middleware.py"
)
SPEC = importlib.util.spec_from_file_location("api_middleware", MODULE_PATH)
api_middleware = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(api_middleware)
AuthMiddleware = api_middleware.AuthMiddleware


def _scope(path="/api/v2/agents", method="GET", authorization=None):
    headers = []
    if authorization is not None:
        headers.append((b"authorization", authorization.encode()))
    return {
        "type": "http",
        "method": method,
        "path": path,
        "headers": headers,
        "query_string": b"",
        "server": ("testserver", 80),
        "scheme": "http",
        "client": ("127.0.0.1", 1234),
    }


async def _call_next(request: Request):
    return Response("ok", status_code=200)


def _dispatch(middleware, request):
    return asyncio.run(middleware.dispatch(request, _call_next))


def test_rejects_malformed_bearer_token_before_handler():
    middleware = AuthMiddleware(app=None)
    request = Request(_scope(authorization="Bearer invalid-token"))

    response = _dispatch(middleware, request)

    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/json")
    assert response.body == (
        b'{"error":{"code":"invalid_token",'
        b'"message":"Token type is not recognized"}}'
    )


def test_user_token_can_read_agents_and_sets_principal_state():
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
    middleware = AuthMiddleware(
        app=None,
        token_store={
            "usr_alice.readsig": {
                "type": "user",
                "principal": "alice",
                "scopes": {"agents:read"},
                "expires_at": expires_at,
            }
        },
    )
    request = Request(_scope(authorization="Bearer usr_alice.readsig"))

    response = _dispatch(middleware, request)

    assert response.status_code == 200
    assert request.state.principal == "alice"
    assert request.state.token_type == "user"
    assert request.state.scopes == {"agents:read"}


def test_user_token_cannot_mutate_agents():
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
    middleware = AuthMiddleware(
        app=None,
        token_store={
            "usr_alice.readsig": {
                "type": "user",
                "principal": "alice",
                "scopes": {"agents:read"},
                "expires_at": expires_at,
            }
        },
    )
    request = Request(
        _scope(method="POST", authorization="Bearer usr_alice.readsig")
    )

    response = _dispatch(middleware, request)

    assert response.status_code == 403
    assert response.body == (
        b'{"error":{"code":"insufficient_scope",'
        b'"message":"Token does not grant the required scope",'
        b'"required_scope":"agents:write"}}'
    )


def test_user_token_with_write_scope_still_cannot_use_machine_write_path():
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
    middleware = AuthMiddleware(
        app=None,
        token_store={
            "usr_alice.adminsig": {
                "type": "user",
                "principal": "alice",
                "scopes": {"agents:read", "agents:write"},
                "expires_at": expires_at,
            }
        },
    )
    request = Request(
        _scope(method="POST", authorization="Bearer usr_alice.adminsig")
    )

    response = _dispatch(middleware, request)

    assert response.status_code == 403
    assert response.body == (
        b'{"error":{"code":"machine_token_required",'
        b'"message":"Agent write operations require a machine token",'
        b'"required_scope":"agents:write","token_type":"user"}}'
    )


def test_machine_token_can_mutate_agents():
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
    middleware = AuthMiddleware(
        app=None,
        token_store={
            "mch_worker.adminsig": {
                "type": "machine",
                "principal": "worker",
                "scopes": {"agents:read", "agents:write"},
                "expires_at": expires_at,
            }
        },
    )
    request = Request(
        _scope(
            method="DELETE",
            path="/api/v2/agents/a1",
            authorization="Bearer mch_worker.adminsig",
        )
    )

    response = _dispatch(middleware, request)

    assert response.status_code == 200
    assert request.state.principal == "worker"
    assert request.state.token_type == "machine"


@pytest.mark.parametrize(
    ("token_record", "expected_body"),
    [
        (
            {
                "type": "machine",
                "principal": "worker",
                "scopes": {"agents:read"},
                "revoked": True,
            },
            b'{"error":{"code":"revoked_token","message":"Token has been revoked"}}',
        ),
        (
            {
                "type": "machine",
                "principal": "worker",
                "scopes": {"agents:read"},
                "expires_at": (
                    datetime.now(timezone.utc) - timedelta(seconds=1)
                ),
            },
            b'{"error":{"code":"expired_token","message":"Token has expired"}}',
        ),
    ],
)
def test_denies_revoked_and_expired_tokens(
    token_record,
    expected_body,
):
    middleware = AuthMiddleware(
        app=None,
        token_store={"mch_worker.adminsig": token_record},
    )
    request = Request(_scope(authorization="Bearer mch_worker.adminsig"))

    response = _dispatch(middleware, request)

    assert response.status_code == 401
    assert response.body == expected_body
