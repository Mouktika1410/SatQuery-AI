"""
Deterministic exposure and impact scoring tools for LLM orchestration.
"""

from typing import Any, Dict, List, Optional
from app.services.exposure_analysis import ExposureAnalysisService
from app.services.impact_scoring import ImpactScoringService


def calculate_exposure_tool(
    flood_polygon_geojson: Dict[str, Any],
    region_id: str,
    data_dir: str = "",
) -> Dict[str, Any]:
    """
    Deterministic tool callable by the LLM to compute affected population, roads, and buildings.
    The LLM MUST call this tool to obtain verified statistics rather than guessing.
    """
    from app.core.config import settings
    from app.services.gis_repository import GISRepository

    repo = GISRepository(data_dir or settings.DATA_DIR)
    svc = ExposureAnalysisService()
    return svc.calculate_exposure(flood_polygon_geojson, region_id, repo)


def score_impact_tool(
    exposure_summary: Dict[str, Any],
    weights: Optional[Dict[str, float]] = None,
) -> List[Dict[str, Any]]:
    """
    Deterministic tool callable by the LLM to rank affected zones by vulnerability and urgency.
    """
    svc = ImpactScoringService()
    return svc.compute_priority_scores(exposure_summary, weights)
