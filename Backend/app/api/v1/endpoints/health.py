"""
Health and Database Connectivity Check Endpoints.
"""

from fastapi import APIRouter, Response, status
from app.core.config import settings
from app.database.session import check_db_connection
from app.schemas.health import HealthResponse, DatabaseHealthResponse

router = APIRouter()


@router.get(
    "",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Application Health Check",
    description="Check the operational health of the SatQuery backend service.",
)
@router.get(
    "/",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def health_check() -> HealthResponse:
    """Return operational health status of the API service."""
    return HealthResponse(
        status="healthy",
        app_name=settings.PROJECT_NAME,
        version=settings.VERSION,
    )


@router.get(
    "/db",
    response_model=DatabaseHealthResponse,
    summary="Database & PostGIS Health Check",
    description="Verify connectivity to PostgreSQL and validate PostGIS extension.",
    responses={
        200: {"description": "Database and PostGIS operational."},
        503: {"description": "Database unreachable or PostGIS missing."},
    },
)
async def database_health_check(response: Response) -> DatabaseHealthResponse:
    """Verify PostgreSQL connectivity and PostGIS extension status."""
    db_result = check_db_connection()

    if db_result["connected"]:
        response.status_code = status.HTTP_200_OK
        return DatabaseHealthResponse(
            status="healthy",
            app_name=settings.PROJECT_NAME,
            database="connected",
            postgis_installed=db_result.get("postgis_installed", False),
            postgis_version=db_result.get("postgis_version"),
            error=None,
        )

    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return DatabaseHealthResponse(
        status="unhealthy",
        app_name=settings.PROJECT_NAME,
        database="disconnected",
        postgis_installed=False,
        postgis_version=None,
        error=db_result.get("error", "Failed to connect to database."),
    )
