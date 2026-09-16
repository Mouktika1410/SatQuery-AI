"""
Tool Catalog and Registry for LLM Function Calling.

Exposes the list of deterministic geospatial tools that the LLM agent can call.
Architectural rule: The LLM acts as an orchestrator only. It never invents
metrics or geospatial geometries; it queries deterministic tools and formats
the verified tool outputs.
"""

from typing import Any, Dict, List


def get_tool_catalog() -> List[Dict[str, Any]]:
    """
    Returns the declarative definitions of all deterministic tools registered
    for LLM agent function calling.
    """
    return [
        {
            "name": "detect_flood_tool",
            "description": "Deterministic satellite-based flood extent detection from imagery.",
            "parameters": {
                "type": "object",
                "properties": {
                    "scene_id": {"type": "string"},
                    "pre_event_image": {"type": "string"},
                    "post_event_image": {"type": "string"},
                    "method": {"type": "string", "default": "otsu"},
                },
                "required": ["scene_id", "pre_event_image", "post_event_image"],
            },
        },
        {
            "name": "generate_polygons_tool",
            "description": "Convert binary raster flood mask into clean GeoJSON polygons.",
            "parameters": {
                "type": "object",
                "properties": {
                    "mask_reference": {"type": "string"},
                    "simplify_tolerance": {"type": "number", "default": 0.0001},
                },
                "required": ["mask_reference"],
            },
        },
        {
            "name": "overlay_gis_layers_tool",
            "description": "Intersect flood boundaries with geospatial infrastructure layers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "flood_polygon_geojson": {"type": "object"},
                    "layers_to_intersect": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["flood_polygon_geojson", "layers_to_intersect"],
            },
        },
        {
            "name": "calculate_exposure_tool",
            "description": "Compute deterministic population, building, and road exposure metrics.",
            "parameters": {
                "type": "object",
                "properties": {
                    "flood_polygon_geojson": {"type": "object"},
                    "region_id": {"type": "string"},
                },
                "required": ["flood_polygon_geojson", "region_id"],
            },
        },
        {
            "name": "score_impact_tool",
            "description": "Calculate vulnerability and urgency priority scores for affected areas.",
            "parameters": {
                "type": "object",
                "properties": {
                    "exposure_summary": {"type": "object"},
                    "weights": {"type": "object"},
                },
                "required": ["exposure_summary"],
            },
        },
        {
            "name": "analyze_evacuation_routes_tool",
            "description": "Identify road network cut-offs and compute viable evacuation paths.",
            "parameters": {
                "type": "object",
                "properties": {
                    "origin_locations": {"type": "array"},
                    "flood_boundary_geojson": {"type": "object"},
                    "shelter_destinations": {"type": "array"},
                },
                "required": ["origin_locations", "flood_boundary_geojson"],
            },
        },
    ]
