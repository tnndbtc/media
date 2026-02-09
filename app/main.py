"""FastAPI application entry point."""

import logging as std_logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api.admin import router as admin_router
from app.api.error_handlers import register_error_handlers
from app.api.middleware import setup_middleware
from app.api.routes import router
from app.config.settings import get_settings
from app.db.base import close_db, init_db
from app.utils.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    settings = get_settings()

    # Setup logging
    setup_logging(
        log_level=settings.log_level,
        log_format=settings.log_format,
    )

    std_logging.info(f"application_starting - version={__version__} debug={settings.debug}")

    # Initialize database
    await init_db()
    std_logging.info("database_initialized")

    # Seed prompts from hardcoded defaults
    from app.db.seed import seed_system_prompts

    await seed_system_prompts()
    std_logging.info("prompts_seeded")

    yield

    # Cleanup
    await close_db()
    std_logging.info("application_shutdown")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Multilingual Media Search API",
        description=(
            "AI-powered semantic media search system that accepts natural language "
            "queries in any language and returns relevant images and videos from "
            "Pexels and Pixabay."
        ),
        version=__version__,
        debug=settings.debug,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Setup middleware
    setup_middleware(app)

    # Register error handlers
    register_error_handlers(app)

    # Include routes
    app.include_router(router)
    app.include_router(admin_router)

    # Mount static files
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    return app


# Create application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )
