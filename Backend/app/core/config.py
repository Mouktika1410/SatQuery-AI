"""
Application Configuration Module.

Centralizes environment variables and application settings for SatQuery.
Uses Pydantic for validation and type enforcement.
"""

import os
from typing import List, Optional
from pydantic import BaseModel, Field


def _load_env_file() -> None:
    """Load key-value pairs from .env file into os.environ if present."""
    candidates = [
        os.path.join(os.getcwd(), ".env"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), ".env"
        ),
    ]
    for path in candidates:
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, _, val = line.partition("=")
                            key = key.strip()
                            val = val.strip().strip("'\"")
                            if key and key not in os.environ:
                                os.environ[key] = val
                break
            except Exception:
                pass


_load_env_file()


def _resolve_data_dir() -> str:
    """Resolve the project-level data/ directory relative to this module."""
    # Backend/app/core/config.py -> go up 3 levels to reach project root, then 'data'
    module_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(os.path.dirname(module_dir))
    project_root = os.path.dirname(backend_dir)
    return os.path.join(project_root, "data")


class Settings(BaseModel):
    """SatQuery backend application settings."""

    PROJECT_NAME: str = "SatQuery"
    API_V1_STR: str = "/api/v1"
    VERSION: str = "0.1.0"
    DEBUG: bool = Field(
        default_factory=lambda: os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")
    )

    # CORS configuration for frontend clients (React/Vite)
    CORS_ORIGINS: List[str] = Field(
        default_factory=lambda: [
            origin.strip()
            for origin in os.getenv(
                "CORS_ORIGINS",
                "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000",
            ).split(",")
            if origin.strip()
        ]
    )

    # Database connection parameters (PostgreSQL / PostGIS — Phase 2)
    POSTGRES_SERVER: str = Field(
        default_factory=lambda: os.getenv("POSTGRES_SERVER", "localhost")
    )
    POSTGRES_PORT: int = Field(
        default_factory=lambda: int(os.getenv("POSTGRES_PORT", "5432"))
    )
    POSTGRES_DB: str = Field(
        default_factory=lambda: os.getenv("POSTGRES_DB", "satquery")
    )
    POSTGRES_USER: str = Field(
        default_factory=lambda: os.getenv("POSTGRES_USER", "satquery")
    )
    POSTGRES_PASSWORD: str = Field(
        default_factory=lambda: os.getenv("POSTGRES_PASSWORD", "satquery")
    )

    # AI / LLM configuration
    GEMINI_API_KEY: Optional[str] = Field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY") or None
    )

    # Data directory configuration
    DATA_DIR: str = Field(
        default_factory=_resolve_data_dir
    )

    # Upload configuration
    MAX_UPLOAD_SIZE_MB: int = Field(
        default_factory=lambda: int(os.getenv("MAX_UPLOAD_SIZE_MB", "500"))
    )
    UPLOAD_ALLOWED_EXTENSIONS: List[str] = Field(
        default_factory=lambda: [".tif", ".tiff"]
    )

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        """Construct PostgreSQL/PostGIS connection URI string."""
        override = os.getenv("DATABASE_URL")
        if override:
            return override
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def data_input_dir(self) -> str:
        return os.path.join(self.DATA_DIR, "input")

    @property
    def data_output_dir(self) -> str:
        return os.path.join(self.DATA_DIR, "output")

    @property
    def data_boundaries_dir(self) -> str:
        return os.path.join(self.DATA_DIR, "boundaries")

    @property
    def data_population_dir(self) -> str:
        return os.path.join(self.DATA_DIR, "population")

    @property
    def data_buildings_dir(self) -> str:
        return os.path.join(self.DATA_DIR, "buildings")

    @property
    def data_roads_dir(self) -> str:
        return os.path.join(self.DATA_DIR, "roads")

    @property
    def data_pois_dir(self) -> str:
        return os.path.join(self.DATA_DIR, "pois")

    @property
    def data_dem_dir(self) -> str:
        return os.path.join(self.DATA_DIR, "dem")


settings = Settings()
