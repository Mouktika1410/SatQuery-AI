"""
Database Session and Connection Management.

Configures connection pooling for PostgreSQL with PostGIS extensions
using SQLAlchemy and GeoAlchemy2.
"""

from typing import Any, Dict, Generator
from app.core.config import settings

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker, Session

    SQLALCHEMY_AVAILABLE = True

    engine = create_engine(
        settings.SQLALCHEMY_DATABASE_URI,
        pool_pre_ping=True,
        echo=settings.DEBUG,
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

except ImportError:
    SQLALCHEMY_AVAILABLE = False
    engine = None  # type: ignore
    SessionLocal = None  # type: ignore
    Session = Any  # type: ignore


def get_db() -> Generator[Any, None, None]:
    """
    FastAPI dependency yielding a database session per request.
    Closes the session when request lifecycle finishes.
    """
    if not SQLALCHEMY_AVAILABLE or SessionLocal is None:
        raise RuntimeError(
            "SQLAlchemy / database driver is not installed. "
            "Please install dependencies from requirements.txt."
        )
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> Dict[str, Any]:
    """
    Performs a connectivity and PostGIS extension check against PostgreSQL.
    
    Returns:
        dict with status, database connectivity flag, and PostGIS version information.
    """
    if not SQLALCHEMY_AVAILABLE or engine is None:
        return {
            "connected": False,
            "error": "SQLAlchemy / psycopg2 driver is not installed in the Python environment.",
            "postgis_installed": False,
            "postgis_version": None,
        }

    try:
        with engine.connect() as connection:
            # 1. Verify basic connectivity
            connection.execute(text("SELECT 1;"))

            # 2. Verify PostGIS extension availability
            postgis_version = None
            try:
                result = connection.execute(text("SELECT PostGIS_Full_Version();"))
                row = result.fetchone()
                if row:
                    postgis_version = str(row[0])
            except Exception:
                # Try simpler version check if PostGIS_Full_Version fails
                try:
                    res = connection.execute(text("SELECT PostGIS_Version();"))
                    r = res.fetchone()
                    if r:
                        postgis_version = str(r[0])
                except Exception:
                    postgis_version = None

            return {
                "connected": True,
                "error": None,
                "postgis_installed": postgis_version is not None,
                "postgis_version": postgis_version,
            }
    except Exception as exc:
        return {
            "connected": False,
            "error": str(exc),
            "postgis_installed": False,
            "postgis_version": None,
        }
