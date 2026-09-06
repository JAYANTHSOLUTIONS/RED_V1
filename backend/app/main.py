"""Application factory.

Wires configuration, logging, middleware, centralized exception handling,
and the versioned API router together. Business modules register their
routers in `app.api.v1.router`; nothing else here needs to change as the
system grows.
"""
from contextlib import asynccontextmanager
from typing import Callable, Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.errors import ServerErrorMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppException
from app.core.logging import configure_logging, get_logger
from app.db.session import dispose_engine
from app.middleware.logging import RequestLoggingMiddleware
from app.middleware.request_id import RequestIdMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.schemas.common import error_envelope

logger = get_logger(__name__)


class ExceptionHandlingASGI:
    """Custom ASGI middleware that catches exceptions including ExceptionGroups.
    
    This wraps the entire ASGI app to catch exceptions that escape the normal
    exception handler middleware, particularly ExceptionGroups that can occur
    with Starlette's task-group-based middleware.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        response_started = False
        
        async def send_with_tracking(message: dict) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, receive, send_with_tracking)
        except BaseException as exc:
            # Catch BaseException to handle ExceptionGroups which are not Exception subclasses
            # Log the exception
            logger.exception(
                "Caught exception at ASGI level on %s %s",
                scope.get("method"),
                scope.get("path"),
            )
            # Only send error response if response hasn't started yet
            if not response_started:
                await send(
                    {
                        "type": "http.response.start",
                        "status": 500,
                        "headers": [[b"content-type", b"application/json"]],
                    }
                )
                await send(
                    {
                        "type": "http.response.body",
                        "body": error_envelope_bytes("INTERNAL_ERROR", "An unexpected error occurred."),
                    }
                )

    # Proxy attributes to the wrapped app so it behaves like a FastAPI app for testing
    def __getattr__(self, name: str) -> Any:
        return getattr(self.app, name)


def error_envelope_bytes(code: str, message: str) -> bytes:
    """Serialize error envelope to JSON bytes for ASGI response."""
    import json
    return json.dumps({
        "success": False,
        "error": {"code": code, "message": message}
    }).encode("utf-8")


def configure_middleware(app: FastAPI) -> None:
    """Register middleware in a fixed, deliberate order.

    Starlette applies middleware outside-in for requests and inside-out for
    responses, in the reverse order added. Request ID is added last so it
    is the outermost layer and wraps logging — every log line for a
    request therefore carries that request's correlation ID.
    """
    settings = get_settings()

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def configure_exception_handlers(app: FastAPI) -> None:
    """Register centralized exception handlers.

    Every response — success or failure — follows the project's standard
    envelope. No handler here ever leaks a stack trace, SQL statement,
    filesystem path, or secret to the client; unexpected exceptions are
    logged in full server-side and returned as a generic INTERNAL_ERROR.
    """

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_envelope(exc.code, exc.message),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error_envelope(
                "VALIDATION_ERROR", "The provided data failed validation."
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        code = "NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR"
        return JSONResponse(
            status_code=exc.status_code,
            content=error_envelope(code, str(exc.detail)),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "Unhandled exception on %s %s", request.method, request.url.path
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_envelope("INTERNAL_ERROR", "An unexpected error occurred."),
        )



@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger.info("Application startup complete.")
    yield
    await dispose_engine()
    logger.info("Application shutdown complete.")


def create_app() -> FastAPI:
    """Build and fully configure the FastAPI application.

    Exposed as a factory (rather than only a module-level `app`) so tests
    can create isolated instances with dependency overrides.
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        debug=False,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        lifespan=lifespan,
    )

    configure_middleware(app)
    configure_exception_handlers(app)
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    # Wrap with custom exception handling ASGI middleware
    app = ExceptionHandlingASGI(app)  # type: ignore
    
    return app


app = create_app()
