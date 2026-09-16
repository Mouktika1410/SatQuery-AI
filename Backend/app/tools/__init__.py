"""
Deterministic tool catalog for LLM function/tool calling.
"""

from app.tools.flood_tools import detect_flood_tool
from app.tools.gis_tools import generate_polygons_tool, overlay_gis_layers_tool
from app.tools.exposure_tools import calculate_exposure_tool, score_impact_tool
from app.tools.evacuation_tools import analyze_evacuation_routes_tool
from app.tools.registry import get_tool_catalog

__all__ = [
    "detect_flood_tool",
    "generate_polygons_tool",
    "overlay_gis_layers_tool",
    "calculate_exposure_tool",
    "score_impact_tool",
    "analyze_evacuation_routes_tool",
    "get_tool_catalog",
]
