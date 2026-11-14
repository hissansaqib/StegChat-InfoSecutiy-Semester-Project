import traceback
from uuid import uuid4
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError

from .core.config import Settings
from .core.logging import logger
from .core.errors import StegChatError
from .api import health, carriers, auth, users, conversations, lab, bench, analysis, recommend, reports, crypto, integrity, attachments
from .db.base import Base
from .db.session import engine
from .db.schema_check import check_schema_sync
from .crypto import get_at_rest_cipher

def create_app() -> FastAPI:
    # Ensure database schema and tables exist on application startup
    Base.metadata.create_all(bind=engine)
    
    # Startup schema integrity verification
    check_schema_sync(engine)
    
    # Eagerly initialize at-rest cipher service at startup
    get_at_rest_cipher()

    settings = Settings()
    app = FastAPI(title="StegChat Backend", version="0.1.0")

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-CSRF-Token", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )

    # Request ID and Global Error Middleware
    @app.middleware("http")
    async def request_id_and_error_middleware(request: Request, call_next):
        req_id = request.headers.get("X-Request-ID", "req-" + uuid4().hex)
        request.state.request_id = req_id
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = req_id
            return response
        except Exception as exc:
            logger.error("Unhandled middleware exception [%s]: %s\n%s", req_id, exc, traceback.format_exc())
            origin = request.headers.get("origin")
            headers = {"X-Request-ID": req_id}
            if origin and (origin in settings.cors_allow_origins or "*" in settings.cors_allow_origins):
                headers["Access-Control-Allow-Origin"] = origin
                headers["Access-Control-Allow-Credentials"] = "true"
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": "An unexpected server error occurred. Please contact support.",
                        "request_id": req_id,
                    }
                },
                headers=headers,
            )

    # Exception Handlers
    @app.exception_handler(StegChatError)
    async def stegchat_error_handler(request: Request, exc: StegChatError):
        req_id = getattr(request.state, "request_id", "req-" + uuid4().hex)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "request_id": req_id,
                }
            },
            headers={"X-Request-ID": req_id},
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        req_id = getattr(request.state, "request_id", "req-" + uuid4().hex)
        code_map = {
            400: "BAD_REQUEST",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            415: "UNSUPPORTED_MEDIA_TYPE",
            422: "UNPROCESSABLE_ENTITY",
            429: "RATE_LIMITED",
            500: "INTERNAL_SERVER_ERROR",
        }
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": code_map.get(exc.status_code, "HTTP_ERROR"),
                    "message": str(exc.detail) if isinstance(exc.detail, str) else "Request error",
                    "request_id": req_id,
                },
                "detail": exc.detail,  # Maintain backwards compatibility
            },
            headers={"X-Request-ID": req_id},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        req_id = getattr(request.state, "request_id", "req-" + uuid4().hex)
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_FAILED",
                    "message": "Invalid request parameters or payload.",
                    "request_id": req_id,
                },
                "detail": exc.errors(),
            },
            headers={"X-Request-ID": req_id},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        req_id = getattr(request.state, "request_id", "req-" + uuid4().hex)
        logger.error("Unhandled route exception [%s]: %s\n%s", req_id, exc, traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An internal server error occurred.",
                    "request_id": req_id,
                }
            },
            headers={"X-Request-ID": req_id},
        )

    # Include routers
    app.include_router(health.router, prefix="/api/v1")
    app.include_router(carriers.router, prefix="/api/v1")
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(users.router, prefix="/api/v1")
    app.include_router(conversations.router, prefix="/api/v1")
    app.include_router(lab.router, prefix="/api/v1")
    app.include_router(bench.router, prefix="/api/v1")
    app.include_router(analysis.router, prefix="/api/v1")
    app.include_router(recommend.router, prefix="/api/v1")
    app.include_router(reports.router, prefix="/api/v1")
    app.include_router(crypto.router, prefix="/api/v1")
    # Include key management router
    from .api import keys
    app.include_router(keys.router, prefix="/api/v1")
    app.include_router(integrity.router, prefix="/api/v1")
    app.include_router(attachments.router, prefix="/api/v1")

    logger.info("FastAPI app created with CORS origins: %s", settings.cors_allow_origins)
    return app

