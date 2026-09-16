"""
Deterministic GIS polygonization and overlay tools for LLM orchestration.
"""

from typing import Any, Dict, List
from app.services.polygon_generation import PolygonGenerationService


def generate_polygons_tool(
    mask_reference: str,
    simplify_tolerance: float = 0.0001,
) -> Dict[str, Any]:
    """
    Deterministic tool callable by the LLM to vectorize a flood mask raster into GeoJSON features.
    """
    svc = PolygonGenerationService()
    return svc.from_mask_file(mask_reference, simplify_tolerance=simplify_tolerance)


def overlay_gis_layers_tool(
    flood_polygon_geojson: Dict[str, Any],
    layers_to_intersect: List[str],
    data_dir: str = "",
) -> Dict[str, Any]:
    """
    Deterministic tool callable by the LLM to overlay flood boundaries on GIS infrastructure layers.
    """
    from app.core.config import settings
    from app.services.gis_repository import GISRepository
    from app.services.exposure_analysis import ExposureAnalysisService

    repo = GISRepository(data_dir or settings.DATA_DIR)
    svc = ExposureAnalysisService()
    return svc.calculate_exposure(flood_polygon_geojson, "llm_query", repo)
