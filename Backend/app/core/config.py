"""
Application Configuration Module.

Centralizes environment variables and application settings for SatQuery.
Uses Pydantic for validation and type enforcement.
"""

import os
from typing import List, Optional
from pydantic import BaseModel, Field


def _load_env_file() -> None:
    """Load key-value pairs from all potential .env file locations into os.environ."""
    module_dir = os.path.dirname(os.path.abspath(__file__))
    app_dir = os.path.dirname(module_dir)
    backend_dir = os.path.dirname(app_dir)
    project_root = os.path.dirname(backend_dir)

    candidates = [
        os.path.join(os.getcwd(), ".env"),
        os.path.join(backend_dir, ".env"),
        os.path.join(project_root, ".env"),
        os.path.join(app_dir, ".env"),
    ]

    seen = set()
    for path in candidates:
        abs_p = os.path.abspath(path)
        if abs_p in seen:
            continue
        seen.add(abs_p)

        if os.path.isfile(abs_p):
            try:
                with open(abs_p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, val = line.split("=", 1)
                            key = key.strip()
                            val = val.strip()
                            if "#" in val and not (val.startswith('"') or val.startswith("'")):
                                val = val.split("#", 1)[0].strip()
                            val = val.strip("'\"")
                            if key:
                                existing = os.environ.get(key, "").strip()
                                if not existing and val:
                                    os.environ[key] = val
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

    @property
    def GEMINI_API_KEY(self) -> Optional[str]:
        """Dynamically resolve Gemini API key from environment variables or .env files."""
        _load_env_file()
        for env_var in ("GEMINI_API_KEY", "GEMINI_KEY", "GOOGLE_API_KEY"):
            val = os.getenv(env_var)
            if val and val.strip():
                return val.strip()
        return None

    # Copernicus Data Space Ecosystem (CDSE) configuration
    @property
    def COPERNICUS_USERNAME(self) -> Optional[str]:
        """Resolve Copernicus Data Space username from environment."""
        _load_env_file()
        for env_var in ("COPERNICUS_USERNAME", "CDSE_USERNAME", "COPERNICUS_USER"):
            val = os.getenv(env_var)
            if val and val.strip():
                return val.strip()
        return None

    @property
    def COPERNICUS_PASSWORD(self) -> Optional[str]:
        """Resolve Copernicus Data Space password from environment."""
        _load_env_file()
        for env_var in ("COPERNICUS_PASSWORD", "CDSE_PASSWORD", "COPERNICUS_PASS"):
            val = os.getenv(env_var)
            if val and val.strip():
                return val.strip()
        return None

    @property
    def COPERNICUS_CLIENT_ID(self) -> Optional[str]:
        """Resolve Copernicus Data Space OAuth2 Client ID from environment."""
        _load_env_file()
        for env_var in ("COPERNICUS_CLIENT_ID", "CDSE_CLIENT_ID"):
            val = os.getenv(env_var)
            if val and val.strip():
                return val.strip()
        return None

    @property
    def COPERNICUS_CLIENT_SECRET(self) -> Optional[str]:
        """Resolve Copernicus Data Space OAuth2 Client Secret from environment."""
        _load_env_file()
        for env_var in ("COPERNICUS_CLIENT_SECRET", "CDSE_CLIENT_SECRET"):
            val = os.getenv(env_var)
            if val and val.strip():
                return val.strip()
        return None

    COPERNICUS_TOKEN_URL: str = (
        "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    )
    COPERNICUS_CATALOGUE_URL: str = (
        "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
    )
    COPERNICUS_ZIPPER_URL: str = (
        "https://zipper.dataspace.copernicus.eu/odata/v1/Products"
    )
    COPERNICUS_STAC_URL: str = (
        "https://stac.dataspace.copernicus.eu/v1/search"
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

    @property
    def copernicus_cache_dir(self) -> str:
        d = os.path.join(self.DATA_DIR, "copernicus_cache")
        os.makedirs(d, exist_ok=True)
        return d


settings = Settings()
