"""Assigns a correlation/request ID to every incoming request.

Reuses an incoming `X-Request-ID` header if present (useful behind a
reverse proxy or for client-side tracing), otherwise generates one. The ID
is exposed on `request.state.request_id`, echoed back as a response
header, and injected into every log line for the request's lifetime via
`app.core.logging.request_id_ctx_var`.
"""
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.logging import request_id_ctx_var

REQUEST_ID_HEADER = "X-Request-ID"


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        incoming_id = request.headers.get(REQUEST_ID_HEADER)
        request_id = incoming_id or str(uuid.uuid4())
        request.state.request_id = request_id

        token = request_id_ctx_var.set(request_id)
        try:
            response = await call_next(request)
        finally:
            request_id_ctx_var.reset(token)

        response.headers[REQUEST_ID_HEADER] = request_id
        return response
