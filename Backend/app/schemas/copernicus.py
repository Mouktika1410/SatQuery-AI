"""
Pydantic v2 schemas for Copernicus Data Space Ecosystem (CDSE) Sentinel-1 acquisition.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.schemas.flood import FloodDetectionResult, PipelineResult


class AOIBounds(BaseModel):
    """Area of Interest bounding box in WGS84 coordinates."""
    west: float = Field(..., description="Westernmost longitude (-180 to 180)")
    south: float = Field(..., description="Southernmost latitude (-90 to 90)")
    east: float = Field(..., description="Easternmost longitude (-180 to 180)")
    north: float = Field(..., description="Northernmost latitude (-90 to 90)")


class Sentinel1ProductSummary(BaseModel):
    """Summary of a Sentinel-1 IW GRD product from Copernicus Data Space."""
    id: str = Field(..., description="Copernicus Data Space product UUID")
    name: str = Field(..., description="Product title / SAFE archive name")
    content_date_start: str = Field(..., description="Acquisition start UTC timestamp")
    content_date_end: str = Field(..., description="Acquisition end UTC timestamp")
    orbit_direction: Optional[str] = Field(None, description="ASCENDING or DESCENDING")
    relative_orbit: Optional[int] = Field(None, description="Relative orbit / track number")
    polarizations: List[str] = Field(default_factory=list, description="Polarizations (e.g. ['VV', 'VH'])")
    size_mb: Optional[float] = Field(None, description="Product archive size in megabytes")
    footprint: Optional[Dict[str, Any]] = Field(None, description="GeoJSON polygon footprint")
    quicklook_url: Optional[str] = Field(None, description="Thumbnail / quicklook preview URL")
    download_url: Optional[str] = Field(None, description="Direct OData download URL")


class CopernicusSearchRequest(BaseModel):
    """Search request parameters for Sentinel-1 products."""
    bbox: Optional[AOIBounds] = Field(None, description="Bounding box [west, south, east, north]")
    geojson: Optional[Dict[str, Any]] = Field(None, description="GeoJSON polygon or feature collection")
    start_date: str = Field(..., description="Start date (YYYY-MM-DD or ISO 8601 UTC)")
    end_date: str = Field(..., description="End date (YYYY-MM-DD or ISO 8601 UTC)")
    orbit_direction: Optional[str] = Field("ANY", description="'ASCENDING', 'DESCENDING', or 'ANY'")
    polarization: Optional[str] = Field("VV", description="'VV', 'VH', or 'ANY'")
    limit: int = Field(10, ge=1, le=50, description="Max number of items to return")


class CopernicusSearchResponse(BaseModel):
    """Response containing matching Sentinel-1 products from CDSE."""
    total_found: int = Field(0, description="Number of products matching query")
    products: List[Sentinel1ProductSummary] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)
    error: Optional[str] = None


class MatchedSARPair(BaseModel):
    """A matched pre/post Sentinel-1 pair sharing identical orbit geometry."""
    relative_orbit: Optional[int] = Field(None, description="Shared track / relative orbit")
    orbit_direction: Optional[str] = Field(None, description="Shared ASCENDING or DESCENDING pass")
    pre_product: Sentinel1ProductSummary
    post_product: Sentinel1ProductSummary
    days_apart: float = Field(..., description="Temporal baseline in days")
    compatible: bool = Field(True, description="True if geometry and polarizations match")
    recommendation_score: float = Field(1.0, description="Ranking score (higher = better match)")
    notes: List[str] = Field(default_factory=list)


class CopernicusPairSearchRequest(BaseModel):
    """Request to find and match pre/post Sentinel-1 pairs over an AOI."""
    bbox: Optional[AOIBounds] = None
    geojson: Optional[Dict[str, Any]] = None
    pre_start_date: str = Field(..., description="Pre-flood search window start (YYYY-MM-DD)")
    pre_end_date: str = Field(..., description="Pre-flood search window end (YYYY-MM-DD)")
    post_start_date: str = Field(..., description="Post-flood search window start (YYYY-MM-DD)")
    post_end_date: str = Field(..., description="Post-flood search window end (YYYY-MM-DD)")
    orbit_direction: Optional[str] = Field("ANY", description="'ASCENDING', 'DESCENDING', or 'ANY'")
    limit: int = Field(5, ge=1, le=20)


class CopernicusPairSearchResponse(BaseModel):
    """Response containing matched pre/post Sentinel-1 candidate pairs."""
    total_pairs: int = 0
    recommended_pair: Optional[MatchedSARPair] = None
    pairs: List[MatchedSARPair] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)
    error: Optional[str] = None


class CopernicusAcquisitionRequest(BaseModel):
    """Request to download selected Sentinel-1 products and execute analysis."""
    pre_product_id: str = Field(..., description="CDSE pre-flood product UUID")
    post_product_id: str = Field(..., description="CDSE post-flood product UUID")
    polarization: str = Field("VV", description="Polarization channel to extract ('VV' or 'VH')")
    run_pipeline: bool = Field(True, description="Execute full analysis pipeline if True, detect only if False")
    download_only: bool = Field(False, description="Download and extract GeoTIFFs only without running flood analysis")
    method: str = Field("sar", description="Detection method ('sar' or 'auto')")
    threshold: Optional[float] = Field(None, description="Custom backscatter drop threshold (dB)")
    simplify_tolerance: float = Field(0.0001, description="Polygon simplification tolerance")
    buffer_m: float = Field(100.0, description="Evacuation buffer distance in meters")
    aoi_bbox: Optional[AOIBounds] = Field(None, description="Optional AOI crop bounds")


class CopernicusAcquisitionResponse(BaseModel):
    """Result of Copernicus data acquisition and downstream flood analysis."""
    success: bool
    pre_file_path: Optional[str] = None
    post_file_path: Optional[str] = None
    pre_product_name: Optional[str] = None
    post_product_name: Optional[str] = None
    detection: Optional[FloodDetectionResult] = None
    pipeline: Optional[PipelineResult] = None
    notes: List[str] = Field(default_factory=list)
    error: Optional[str] = None


class CopernicusAuthStatus(BaseModel):
    """Safe status report of Copernicus Data Space credentials and authentication."""
    configured: bool = Field(..., description="True if credentials are set in environment")
    auth_type: Optional[str] = Field(None, description="'password' or 'client_credentials'")
    authenticated: bool = Field(..., description="True if token was successfully acquired")
    message: str = Field(..., description="Human-readable status summary")
