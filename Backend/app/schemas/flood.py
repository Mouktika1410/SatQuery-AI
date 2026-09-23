"""
Pydantic v2 schemas for all Phase 1 SatQuery flood analysis request/response models.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Image Validation Schemas
# ---------------------------------------------------------------------------

class ImageValidationResult(BaseModel):
    """Validation result for a single GeoTIFF image."""
    filename: str
    valid: bool
    width: Optional[int] = None
    height: Optional[int] = None
    band_count: Optional[int] = None
    crs: Optional[str] = None
    crs_epsg: Optional[int] = None
    transform: Optional[List[float]] = None  # 6 affine transform coefficients
    bounds: Optional[Dict[str, float]] = None  # left, bottom, right, top
    data_type: Optional[str] = None
    nodata: Optional[float] = None
    error: Optional[str] = None


class UploadValidationResponse(BaseModel):
    """Validation result for a pre/post GeoTIFF image pair."""
    pre_flood: ImageValidationResult
    post_flood: ImageValidationResult
    compatible: bool
    compatibility_notes: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Flood Detection Schemas
# ---------------------------------------------------------------------------

class FloodDetectionOptions(BaseModel):
    """Configuration options for flood detection algorithm selection."""
    method: str = Field(
        default="auto",
        description="Detection method: 'auto', 'ndwi', or 'differencing'",
    )
    ndwi_green_band: int = Field(
        default=2,
        description="Band index for Green channel (1-indexed, used by NDWI)",
    )
    ndwi_nir_band: int = Field(
        default=4,
        description="Band index for NIR channel (1-indexed, used by NDWI)",
    )
    threshold: Optional[float] = Field(
        default=None,
        description="Override Otsu auto-threshold with a fixed value",
    )
    morphology_iterations: int = Field(
        default=2,
        description="Morphological cleanup iterations (0 = disabled)",
    )


class FloodDetectionResult(BaseModel):
    """Results from the deterministic flood detection algorithm."""
    success: bool
    method_used: str
    flooded_pixels: int = 0
    total_pixels: int = 0
    flood_percentage: float = 0.0
    flood_area_km2: float = 0.0
    bounds: Optional[Dict[str, float]] = None
    mask_path: Optional[str] = None
    crs: Optional[str] = None
    notes: List[str] = Field(default_factory=list)
    acquisition_metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Flood Polygon Schemas
# ---------------------------------------------------------------------------

class FloodPolygonResult(BaseModel):
    """Result of converting a flood raster mask into vector polygons."""
    success: bool
    geojson: Optional[Dict[str, Any]] = None
    polygon_count: int = 0
    total_area_km2: float = 0.0
    total_area_ha: float = 0.0
    crs: str = "EPSG:4326"
    simplification_tolerance: float = 0.0001
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Image Study Schemas
# ---------------------------------------------------------------------------

class RasterMetadata(BaseModel):
    """Metadata extracted from a georeferenced satellite GeoTIFF raster."""
    filename: str
    width: int
    height: int
    band_count: int
    crs: str
    bounds: Dict[str, float]  # left, bottom, right, top
    pixel_size_x: float
    pixel_size_y: float


class CentroidCoordinates(BaseModel):
    """Geographic centroid coordinates of detected flood polygons."""
    latitude: float
    longitude: float


class ImageStudyResult(BaseModel):
    """Results from dual-GeoTIFF Image Study flood analysis."""
    success: bool
    session_id: Optional[str] = None
    pre_metadata: Optional[RasterMetadata] = None
    post_metadata: Optional[RasterMetadata] = None
    flood_area_km2: float = 0.0
    flood_area_ha: float = 0.0
    polygon_count: int = 0
    centroid: Optional[CentroidCoordinates] = None
    geojson: Optional[Dict[str, Any]] = None
    exposed_population: Optional[int] = Field(
        default=None, description="Modeled estimate of population in flood polygon"
    )
    population_geojson: Optional[Dict[str, Any]] = Field(
        default=None, description="GeoJSON feature collection of population grid cells"
    )
    affected_buildings: Optional[int] = Field(
        default=None, description="Count of building footprints intersecting flood extent"
    )
    buildings_geojson: Optional[Dict[str, Any]] = Field(
        default=None, description="GeoJSON feature collection of building footprints"
    )
    affected_road_length_km: Optional[float] = Field(
        default=None, description="Total length in km of inundated road segments"
    )
    affected_roads_geojson: Optional[Dict[str, Any]] = Field(
        default=None, description="GeoJSON feature collection of inundated road segments"
    )
    bounds: Optional[Dict[str, float]] = None
    notes: List[str] = Field(default_factory=list)
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Impact Analysis Schemas
# ---------------------------------------------------------------------------

class AffectedVillage(BaseModel):
    """Metrics for a single village affected by the flood."""
    name: str
    area_flooded_km2: float = 0.0
    population_affected: Optional[int] = Field(
        default=None, description="Modeled estimate of population in affected zone"
    )
    geometry: Optional[Dict[str, Any]] = None


class ImpactMetrics(BaseModel):
    """
    Deterministic impact analysis results based on available GIS datasets.
    Modeled attributes (such as population) are explicitly marked as estimates.
    """
    affected_villages: List[AffectedVillage] = Field(default_factory=list)
    affected_population: Optional[int] = Field(
        default=None, description="Modeled estimate of affected population"
    )
    affected_buildings: Optional[int] = Field(
        default=None, description="Count of building footprints intersecting flood extent"
    )
    affected_road_length_km: Optional[float] = Field(
        default=None, description="Total length in km of inundated road segments"
    )
    # GeoJSON FeatureCollections for overlay on Leaflet map
    affected_villages_geojson: Optional[Dict[str, Any]] = None
    affected_roads_geojson: Optional[Dict[str, Any]] = None
    # Transparently reports which datasets were actually used in calculations
    data_availability: Dict[str, bool] = Field(
        default_factory=lambda: {
            "villages": False,
            "population": False,
            "buildings": False,
            "roads": False,
            "dem": False,
        }
    )
    disclaimer: str = (
        "Impact figures and population metrics are modeled estimates based on overlaying "
        "satellite flood extents with available geospatial layers. Field verification is advised."
    )


# ---------------------------------------------------------------------------
# Priority Scoring Schemas
# ---------------------------------------------------------------------------

class PriorityScore(BaseModel):
    """Heuristic priority score for a single affected village/zone."""
    village_name: str
    priority_score: float = Field(
        ...,
        description="Normalized heuristic score in range [0, 1]. Higher = higher response priority.",
    )
    rank: int
    contributing_factors: Dict[str, float] = Field(
        default_factory=dict,
        description="Per-factor normalized contributions to the final score.",
    )
    disclaimer: str = (
        "Heuristic decision-support score based on available normalized geospatial factors. "
        "Not a validated machine-learned prediction."
    )


# ---------------------------------------------------------------------------
# Evacuation Candidate Schemas
# ---------------------------------------------------------------------------

class EvacuationCandidate(BaseModel):
    """
    A candidate accessible site for on-ground verification.
    IMPORTANT: These are candidate accessible locations outside the flood polygon.
    They are NOT guaranteed safe shelters or verified evacuation centers.
    """
    name: str
    type: str
    lat: float
    lon: float
    distance_to_flood_km: Optional[float] = None
    elevation_m: Optional[float] = Field(
        default=None, description="Elevation sampled from DEM raster in meters (if available)"
    )
    notes: str = "Candidate accessible site for on-ground verification only. Not a verified shelter."


class EvacuationCandidatesResult(BaseModel):
    """Result of candidate accessible site identification."""
    candidates: List[EvacuationCandidate] = Field(default_factory=list)
    total_found: int = 0
    filtered_reason: str = ""
    disclaimer: str = (
        "Candidate accessible sites for on-ground verification only. "
        "These locations are filtered based on spatial exclusion from detected flood extents, "
        "elevation, and road proximity. They are NOT guaranteed safe shelters."
    )


# ---------------------------------------------------------------------------
# VLM Visual Comparison Schemas
# ---------------------------------------------------------------------------

class VLMAnalysisResult(BaseModel):
    """Qualitative visual comparison generated by Gemini Multimodal VLM."""
    available: bool = False
    comparison: str = "VLM visual comparison is not available."
    disclaimer: str = (
        "Visual comparison performed by Gemini Multimodal VLM. "
        "Qualitative visual description separate from quantitative GIS measurements."
    )


# ---------------------------------------------------------------------------
# Full Pipeline Schema
# ---------------------------------------------------------------------------

class PipelineResult(BaseModel):
    """Complete end-to-end flood analysis pipeline result."""
    session_id: str
    validation: Optional[UploadValidationResponse] = None
    detection: Optional[FloodDetectionResult] = None
    polygons: Optional[FloodPolygonResult] = None
    impact: Optional[ImpactMetrics] = None
    priority_scores: List[PriorityScore] = Field(default_factory=list)
    evacuation: Optional[EvacuationCandidatesResult] = None
    vlm_analysis: Optional[VLMAnalysisResult] = None
    error: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)

