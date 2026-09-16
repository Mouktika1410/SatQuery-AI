"""
Declarative base foundation for SQLAlchemy and GeoAlchemy2 models.
"""

try:
    from sqlalchemy.orm import DeclarativeBase

    class Base(DeclarativeBase):
        """Base class for all database models."""
        pass

except ImportError:
    # Fallback placeholder if SQLAlchemy is not yet installed
    class Base:  # type: ignore
        """Placeholder DeclarativeBase until SQLAlchemy is installed."""
        pass
