"""Shared validation helpers for public API routes."""

from typing import Dict, Optional
from uuid import UUID

from fastapi import HTTPException

from src.agent import AgentStatus


def validation_error(message: str, field: Optional[str] = None) -> HTTPException:
    detail: Dict[str, object] = {
        "error": {
            "code": "invalid_request",
            "message": message,
        }
    }
    if field:
        detail["error"]["field"] = field
    return HTTPException(status_code=400, detail=detail)


def not_found_error(message: str = "Agent not found") -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={
            "error": {
                "code": "not_found",
                "message": message,
            }
        },
    )


def require_non_empty(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise validation_error(f"{field} must be a non-empty string", field)
    return value.strip()


def parse_agent_status(status: Optional[str]) -> Optional[AgentStatus]:
    if status is None:
        return None
    try:
        return AgentStatus(status)
    except ValueError as exc:
        allowed = ", ".join(member.value for member in AgentStatus)
        raise validation_error(f"status must be one of: {allowed}", "status") from exc


def parse_agent_id(agent_id: str) -> str:
    try:
        return str(UUID(agent_id))
    except (TypeError, ValueError) as exc:
        raise validation_error("agent_id must be a valid UUID", "agent_id") from exc
