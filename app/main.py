from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi.middleware import SlowAPIMiddleware

from app.api.router import api_router
from app.config import Settings, get_settings
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import setup_logging
from app.core.rate_limit import limiter
from app.core.security import SecurityHeadersMiddleware
from app.db.database import create_table
from app.middleware.request_id import RequestIdMiddleware


@asynccontextmanager
async def lifespan(_app: FastAPI):
    create_table()
    yield


def create_app(settings: Settings | None = None) -> FastAPI:
    if settings is not None:
        os.environ["DATABASE_URL"] = settings.database_url
        get_settings.cache_clear()
    else:
        settings = get_settings()

    setup_logging(settings)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    app.state.limiter = limiter
    register_exception_handlers(app)

    # Middleware order: last added runs first on request.
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.allowed_hosts,
    )
    allow_credentials = settings.cors_origins != ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
    app.add_middleware(SecurityHeadersMiddleware, settings=settings)
    app.add_middleware(RequestIdMiddleware)

    app.include_router(api_router)
    return app


app = create_app()
