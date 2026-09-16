"""
Deterministic evacuation and connectivity analysis tools for LLM orchestration.
"""

from typing import Any, Dict, List
from app.services.evacuation import EvacuationService


def analyze_evacuation_routes_tool(
    flood_boundary_geojson: Dict[str, Any],
    data_dir: str = "",
    buffer_m: float = 100.0,
) -> Dict[str, Any]:
    """
    Deterministic tool callable by the LLM to identify candidate accessible sites for on-ground verification.
    """
    from app.core.config import settings
    from app.services.gis_repository import GISRepository

    repo = GISRepository(data_dir or settings.DATA_DIR)
    svc = EvacuationService()
    return svc.find_candidates(flood_boundary_geojson, repo, buffer_m=buffer_m)
