"""API middleware components."""

import time
import logging
from datetime import datetime, timezone
from typing import Callable, Dict, Optional, Set, Tuple
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.responses import Response

logger = logging.getLogger(__name__)


READ_METHODS = {"GET", "HEAD", "OPTIONS"}


def _normalize_scopes(scopes) -> Set[str]:
    if scopes is None:
        return set()
    if isinstance(scopes, str):
        return {scopes}
    return set(scopes)


def _required_scope(request: Request) -> Optional[str]:
    if not request.url.path.startswith("/api/v2/agents"):
        return None
    return "agents:read" if request.method in READ_METHODS else "agents:write"


def _token_type(token: str) -> Optional[str]:
    if token.startswith("mch_"):
        return "machine"
    if token.startswith("usr_"):
        return "user"
    return None


def _auth_error(status_code: int, code: str, message: str, **fields) -> Response:
    error = {
        "code": code,
        "message": message,
    }
    error.update({key: value for key, value in fields.items() if value is not None})
    return JSONResponse(status_code=status_code, content={"error": error})


class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, token_store: Optional[Dict[str, Dict]] = None):
        super().__init__(app)
        self.token_store = token_store or {}

    def _validate_token(
        self,
        auth_header: str,
    ) -> Tuple[Optional[Dict], Optional[Response]]:
        if not auth_header.startswith("Bearer "):
            return None, _auth_error(401, "unauthorized", "Bearer token is required")

        token = auth_header.removeprefix("Bearer ").strip()
        token_type = _token_type(token)
        if not token_type:
            return None, _auth_error(401, "invalid_token", "Token type is not recognized")

        record = self.token_store.get(token)
        if not record or record.get("type") != token_type:
            return None, _auth_error(401, "invalid_token", "Token is not registered")

        if record.get("revoked"):
            return None, _auth_error(401, "revoked_token", "Token has been revoked")

        expires_at = record.get("expires_at")
        if expires_at is not None:
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at <= datetime.now(timezone.utc):
                return None, _auth_error(401, "expired_token", "Token has expired")

        return {
            "type": token_type,
            "principal": record.get("principal"),
            "scopes": _normalize_scopes(record.get("scopes")),
        }, None

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        if (
            request.url.path.startswith("/api/v2")
            and request.url.path != "/api/v2/auth/token"
        ):
            principal, error_response = self._validate_token(
                request.headers.get("Authorization", "")
            )
            if error_response:
                return error_response

            required_scope = _required_scope(request)
            if required_scope and required_scope not in principal["scopes"]:
                return _auth_error(
                    403,
                    "insufficient_scope",
                    "Token does not grant the required scope",
                    required_scope=required_scope,
                )
            if required_scope == "agents:write" and principal["type"] != "machine":
                return _auth_error(
                    403,
                    "machine_token_required",
                    "Agent write operations require a machine token",
                    required_scope=required_scope,
                    token_type=principal["type"],
                )

            request.state.token_type = principal["type"]
            request.state.principal = principal["principal"]
            request.state.scopes = principal["scopes"]

        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        max_requests: int = 100,
        window: int = 60,
    ):
        super().__init__(app)
        self.max_requests = max_requests
        self.window = window
        self._requests = {}

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        if client_ip not in self._requests:
            self._requests[client_ip] = []

        self._requests[client_ip] = [
            t for t in self._requests[client_ip] if now - t < self.window
        ]

        if len(self._requests[client_ip]) >= self.max_requests:
            return Response(status_code=429, content="Too many requests")

        self._requests[client_ip].append(now)
        return await call_next(request)


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        start = time.time()
        response = await call_next(request)
        duration = time.time() - start
        logger.info(
            f"{request.method} {request.url.path} "
            f"{response.status_code} {duration:.3f}s"
        )
        return response

# 2019-03-01T18:35:19 update

# 2019-04-03T13:22:05 update

# 2019-04-30T17:18:49 update

# 2019-08-20T09:29:03 update

# 2019-08-30T15:52:06 update

# 2019-11-23T16:58:42 update

# 2020-02-18T10:04:07 update

# 2020-04-21T17:35:30 update

# 2020-05-22T11:10:34 update

# 2020-07-02T12:31:26 update

# 2020-07-05T13:52:59 update

# 2020-08-21T20:36:45 update

# 2021-01-19T09:17:15 update

# 2021-01-29T11:34:24 update

# 2021-02-04T15:21:21 update

# 2021-04-19T19:23:15 update

# 2021-05-20T16:50:15 update

# 2021-06-22T19:23:44 update

# 2021-09-09T13:44:55 update

# 2021-09-16T09:30:20 update

# 2021-10-14T20:42:33 update

# 2021-12-28T16:39:14 update

# 2022-01-26T19:07:27 update

# 2022-01-28T08:03:41 update

# 2022-03-23T12:17:02 update

# 2022-04-06T12:12:27 update

# 2022-04-21T14:53:01 update

# 2022-06-30T08:37:32 update

# 2022-07-06T10:44:45 update

# 2022-11-02T11:12:47 update

# 2022-11-15T20:54:21 update

# 2022-11-23T14:13:34 update

# 2023-01-26T10:03:44 update

# 2023-02-09T17:08:10 update

# 2023-02-16T10:04:00 update

# 2023-03-14T11:52:03 update

# 2023-04-10T12:42:07 update

# 2023-04-26T10:43:39 update

# 2023-06-27T08:18:07 update

# 2023-08-30T15:30:40 update

# 2023-08-30T14:10:05 update

# 2023-10-09T18:32:46 update

# 2023-11-21T20:35:55 update

# 2024-03-07T19:17:39 update

# 2024-04-01T18:06:19 update

# 2024-07-18T15:37:34 update

# 2024-07-25T09:21:53 update

# 2024-08-12T14:24:22 update

# 2024-11-18T08:50:54 update

# 2025-04-08T12:43:05 update

# 2025-06-03T08:10:47 update

# 2025-06-12T08:37:52 update

# 2025-06-17T08:36:56 update

# 2025-07-02T18:09:42 update

# 2025-07-22T12:39:21 update

# 2025-10-13T12:13:46 update

# 2025-12-05T09:44:22 update

# 2025-12-22T18:34:47 update

# 2026-01-26T15:36:23 update

# 2026-02-13T12:36:40 update

# 2026-02-26T11:07:15 update

# 2026-03-19T11:00:17 update

# 2026-03-27T12:58:53 update

# 2026-05-12T17:19:36 update
