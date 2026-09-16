"""
Deterministic flood detection tool interface for LLM orchestration.
"""

from typing import Any, Dict
from app.services.flood_detection import FloodDetectionService


def detect_flood_tool(
    scene_id: str,
    pre_event_image: str,
    post_event_image: str,
    method: str = "auto",
) -> Dict[str, Any]:
    """
    Deterministic tool callable by the LLM to trigger satellite-based flood extent detection.
    Returns structured results produced by deterministic raster processing.
    """
    svc = FloodDetectionService()
    result = svc.detect(
        pre_event_image,
        post_event_image,
        options={"method": method, "morphology_iterations": 2},
    )
    # Remove raw numpy array if present so output is JSON serializable
    result.pop("mask_array", None)
    return result
