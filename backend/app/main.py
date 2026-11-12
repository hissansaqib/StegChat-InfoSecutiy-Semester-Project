from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.config import Settings
from .core.logging import logger
from .api import health, carriers, auth, users, conversations, lab, bench, analysis, recommend, reports, crypto, integrity, attachments
from .db.base import Base
from .db.session import engine
import backend.app.db.models
from uuid import uuid4

def create_app() -> FastAPI:
    # Ensure database schema and tables exist on application startup
    Base.metadata.create_all(bind=engine)
    settings = Settings()
    app = FastAPI(title="StegChat Backend", version="0.1.0")

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request ID Middleware
    @app.middleware("http")
    async def add_request_id(request, call_next):
        request.state.request_id = request.headers.get("X-Request-ID", "req-" + uuid4().hex)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    # Include routers
    app.include_router(health.router, prefix="/api/v1")
    app.include_router(carriers.router, prefix="/api/v1")
    # stub routers
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
