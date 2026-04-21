"""Main FastAPI application – AI-Cam entry point."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.api.alerts import router as alerts_router
from src.api.cameras import router as cameras_router
from src.api.geeni import router as geeni_router
from src.api.events import router as events_router
from src.api.stream import router as stream_router
from src.camera.manager import camera_manager
from src.camera.auto_discovery import auto_discovery_service
from src.config import get_settings
from src.database import SessionLocal, create_tables
from src.detection import detector as det_module

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

_HERE = Path(__file__).parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.ensure_dirs()
    create_tables()
    det_module.load_model(settings.yolo_model)
    db = SessionLocal()
    try:
        camera_manager.startup(db)

        # Run auto-discovery on startup if enabled
        if settings.auto_discovery_enabled and settings.auto_discovery_on_startup:
            logger.info("Running auto-discovery on startup...")
            # Use full sweep settings if enabled
            max_hosts = (
                settings.auto_discovery_full_sweep_max_hosts
                if settings.auto_discovery_full_sweep
                else settings.auto_discovery_max_hosts
            )
            asyncio.create_task(
                auto_discovery_service.run_discovery(
                    db=db,
                    subnets=settings.auto_discovery_subnets_list or None,
                    enable_brute_force=settings.auto_discovery_brute_force,
                    auto_add_cameras=settings.auto_discovery_auto_add,
                    max_hosts=max_hosts,
                    timeout=settings.auto_discovery_timeout,
                    allow_full_sweep=settings.auto_discovery_full_sweep,
                )
            )

        # Start background auto-discovery if enabled with interval
        if settings.auto_discovery_enabled and settings.auto_discovery_interval_hours > 0:
            # Use full sweep settings if enabled
            max_hosts = (
                settings.auto_discovery_full_sweep_max_hosts
                if settings.auto_discovery_full_sweep
                else settings.auto_discovery_max_hosts
            )
            auto_discovery_service.start_background(
                db=db,
                subnets=settings.auto_discovery_subnets_list or None,
                enable_brute_force=settings.auto_discovery_brute_force,
                auto_add_cameras=settings.auto_discovery_auto_add,
                max_hosts=max_hosts,
                timeout=settings.auto_discovery_timeout,
                interval_hours=settings.auto_discovery_interval_hours,
                allow_full_sweep=settings.auto_discovery_full_sweep,
            )
    finally:
        pass  # db kept open for event callbacks
    logger.info("AI-Cam started. Dashboard: http://%s:%d/", settings.host, settings.port)
    yield
    auto_discovery_service.stop_background()
    camera_manager.shutdown()
    db.close()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="AI-Cam",
        description=(
            "Open-source AI-powered camera monitoring system. "
            "Coram-style object detection, motion alerts, and live streaming."
        ),
        version="1.0.0",
        lifespan=lifespan,
        debug=settings.debug,
    )

    # Static files & templates
    static_dir = _HERE / "static"
    templates_dir = _HERE / "templates"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    templates = Jinja2Templates(directory=str(templates_dir))

    # API routers
    app.include_router(cameras_router)
    app.include_router(geeni_router)
    app.include_router(events_router)
    app.include_router(alerts_router)
    app.include_router(stream_router)

    # ── Web UI routes ─────────────────────────────────────────────────────────

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        return templates.TemplateResponse(request, "dashboard.html")

    @app.get("/cameras", response_class=HTMLResponse)
    async def cameras_page(request: Request):
        return templates.TemplateResponse(request, "cameras.html")

    @app.get("/events", response_class=HTMLResponse)
    async def events_page(request: Request):
        return templates.TemplateResponse(request, "events.html")

    @app.get("/settings", response_class=HTMLResponse)
    async def settings_page(request: Request):
        return templates.TemplateResponse(request, "settings.html")

    return app


app = create_app()
