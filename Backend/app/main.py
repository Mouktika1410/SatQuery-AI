"""
Main FastAPI Application Entrypoint for SatQuery.
"""

import os
import sys
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1.router import api_router
from app.api.v1.endpoints.health import health_check, database_health_check
from app.schemas.health import HealthResponse, DatabaseHealthResponse

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup and shutdown lifecycle manager.
    Creates required data directories and ensures synthetic sample GeoTIFFs exist.
    """
    # Ensure all data subdirectories exist
    data_dirs = [
        settings.DATA_DIR,
        settings.data_input_dir,
        settings.data_output_dir,
        settings.data_boundaries_dir,
        settings.data_population_dir,
        settings.data_buildings_dir,
        settings.data_roads_dir,
        settings.data_pois_dir,
        settings.data_dem_dir,
    ]
    for d in data_dirs:
        os.makedirs(d, exist_ok=True)

    # Ensure synthetic sample GeoTIFF files exist in data/input/ and data/dem/
    pre_sample = os.path.join(settings.data_input_dir, "sample_pre_flood_sentinel.tif")
    post_sample = os.path.join(settings.data_input_dir, "sample_post_flood_sentinel.tif")
    if not (os.path.isfile(pre_sample) and os.path.isfile(post_sample)):
        try:
            # Add scripts dir to sys.path to load create_synthetic_tifs
            root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            scripts_dir = os.path.join(root_dir, "scripts")
            if scripts_dir not in sys.path:
                sys.path.insert(0, scripts_dir)
            import create_synthetic_tifs
            create_synthetic_tifs.generate_all_sample_files(settings.DATA_DIR)
            logger.info("Generated sample synthetic GeoTIFF files in %s", settings.DATA_DIR)
        except Exception as exc:
            logger.debug("Synthetic GeoTIFF generation notice: %s", exc)

    logger.info("SatQuery %s starting up. Data directory: %s", settings.VERSION, settings.DATA_DIR)

    # Log available GIS datasets
    try:
        from app.services.gis_repository import GISRepository
        repo = GISRepository(settings.DATA_DIR)
        available = repo.available_layers()
        loaded = [k for k, v in available.items() if v]
        missing = [k for k, v in available.items() if not v]
        if loaded:
            logger.info("GIS datasets available: %s", ", ".join(loaded))
        if missing:
            logger.info("GIS datasets NOT loaded (add to data/): %s", ", ".join(missing))
    except Exception as exc:
        logger.debug("GIS repository check skipped: %s", exc)

    yield

    logger.info("SatQuery shutting down.")


# Initialize FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "SatQuery: AI-powered, query-driven remote-sensing and GIS assistant. "
        "Phase 1 provides deterministic flood detection from satellite imagery "
        "with file-based GIS overlay analysis."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# Configure CORS for React/Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root-level health endpoints
app.add_api_route(
    "/health",
    health_check,
    methods=["GET"],
    response_model=HealthResponse,
    tags=["Health"],
    summary="Application health check",
)
app.add_api_route(
    "/health/db",
    database_health_check,
    methods=["GET"],
    response_model=DatabaseHealthResponse,
    tags=["Health"],
    summary="Database connectivity check",
    responses={
        200: {"description": "Database connected and PostGIS active."},
        503: {"description": "Database unreachable or PostGIS missing."},
    },
)

# Mount versioned API routes
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Root"], summary="API Root")
async def root():
    """Root endpoint — entry point with links to docs and health checks."""
    return {
        "message": f"Welcome to {settings.PROJECT_NAME} API",
        "version": settings.VERSION,
        "docs": "/docs",
        "health": "/health",
        "database_health": "/health/db",
        "flood_analysis": f"{settings.API_V1_STR}/flood/pipeline",
        "ai_assistant": f"{settings.API_V1_STR}/chat",
    }
