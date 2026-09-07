"""Assigns a correlation/request ID to every incoming request.

Reuses an incoming `X-Request-ID` header if present (useful behind a
reverse proxy or for client-side tracing), otherwise generates one. The ID
is exposed on `request.state.request_id`, echoed back as a response
header, and injected into every log line for the request's lifetime via
`app.core.logging.request_id_ctx_var`.
"""
import re
import uuid
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.logging import request_id_ctx_var

REQUEST_ID_HEADER = "X-Request-ID"
REQUEST_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\.:]{1,64}$")


def is_valid_request_id(request_id: Optional[str]) -> bool:
    """Validate request ID format to prevent log injection and oversized tokens."""
    if not request_id:
        return False
    return bool(REQUEST_ID_PATTERN.match(request_id.strip()))


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        incoming_id = request.headers.get(REQUEST_ID_HEADER)
        if incoming_id and is_valid_request_id(incoming_id):
            request_id = incoming_id.strip()
        else:
            request_id = str(uuid.uuid4())

        request.state.request_id = request_id

        token = request_id_ctx_var.set(request_id)
        try:
            response = await call_next(request)
        finally:
            request_id_ctx_var.reset(token)

        response.headers[REQUEST_ID_HEADER] = request_id
        return response
