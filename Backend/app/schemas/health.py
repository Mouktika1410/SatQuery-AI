"""
Health check schema models.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response payload schema."""

    status: str = Field(default="healthy", description="Current system operational status")
    app_name: str = Field(..., description="Application name")
    version: str = Field(..., description="Application version")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="UTC timestamp of the health check"
    )


class DatabaseHealthResponse(BaseModel):
    """Database connectivity and PostGIS health check response schema."""

    status: str = Field(..., description="Overall health status ('healthy' or 'unhealthy')")
    app_name: str = Field(..., description="Application name")
    database: str = Field(..., description="Database connection state ('connected' or 'disconnected')")
    postgis_installed: bool = Field(
        default=False, description="Whether PostGIS extension is active in PostgreSQL"
    )
    postgis_version: Optional[str] = Field(
        default=None, description="Reported PostGIS version string"
    )
    error: Optional[str] = Field(
        default=None, description="Error message if connectivity failed"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="UTC timestamp of the check"
    )
