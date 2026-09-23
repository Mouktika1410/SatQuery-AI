"""
Copernicus Data Space Ecosystem (CDSE) Sentinel-1 Acquisition Endpoints.

Provides endpoints to:
1. Check CDSE credential & authentication status
2. Search for Sentinel-1 IW GRD products by AOI and date range
3. Find and rank compatible pre/post co-orbit pairs (same relative orbit track)
4. Automatically acquire (download) products and feed them into the flood detection pipeline
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, status

from app.schemas.copernicus import (
    CopernicusAuthStatus,
    CopernicusSearchRequest,
    CopernicusSearchResponse,
    CopernicusPairSearchRequest,
    CopernicusPairSearchResponse,
    CopernicusAcquisitionRequest,
    CopernicusAcquisitionResponse,
)
from app.services.copernicus_client import CopernicusDataSpaceClient

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/status",
    response_model=CopernicusAuthStatus,
    summary="Check Copernicus Data Space credentials status",
)
async def get_copernicus_status() -> CopernicusAuthStatus:
    """
    Check if Copernicus Data Space credentials are configured and valid.
    Credentials and tokens are never returned in the response.
    """
    client = CopernicusDataSpaceClient()
    return client.get_auth_status()


@router.post(
    "/search",
    response_model=CopernicusSearchResponse,
    summary="Search Sentinel-1 IW GRD products in Copernicus Data Space",
)
async def search_copernicus_products(
    request: CopernicusSearchRequest,
) -> CopernicusSearchResponse:
    """
    Search for Sentinel-1 IW GRD products using AOI bounding box or GeoJSON
    and date range via the official Copernicus Data Space OData Catalogue API.
    """
    client = CopernicusDataSpaceClient()

    aoi = request.bbox or request.geojson
    result = client.search_sentinel1_grd(
        aoi=aoi,
        start_date=request.start_date,
        end_date=request.end_date,
        orbit_direction=request.orbit_direction,
        polarization=request.polarization,
        limit=request.limit,
    )

    return CopernicusSearchResponse(
        total_found=result.get("total_found", 0),
        products=result.get("products", []),
        notes=result.get("notes", []),
        error=result.get("error"),
    )


@router.post(
    "/pairs",
    response_model=CopernicusPairSearchResponse,
    summary="Find and rank co-orbit Sentinel-1 pre/post acquisition pairs",
)
async def find_copernicus_pairs(
    request: CopernicusPairSearchRequest,
) -> CopernicusPairSearchResponse:
    """
    Search and automatically rank compatible pre/post Sentinel-1 product pairs.
    Pairs sharing the same relative orbit track and pass direction are ranked highest
    to guarantee identical radar viewing geometry for change detection.
    """
    client = CopernicusDataSpaceClient()

    aoi = request.bbox or request.geojson
    result = client.find_compatible_pairs(
        aoi=aoi,
        pre_start_date=request.pre_start_date,
        pre_end_date=request.pre_end_date,
        post_start_date=request.post_start_date,
        post_end_date=request.post_end_date,
        orbit_direction=request.orbit_direction,
        limit=request.limit,
    )

    return CopernicusPairSearchResponse(
        total_pairs=result.get("total_pairs", 0),
        recommended_pair=result.get("recommended_pair"),
        pairs=result.get("pairs", []),
        notes=result.get("notes", []),
        error=result.get("error"),
    )


@router.post(
    "/acquire",
    response_model=CopernicusAcquisitionResponse,
    summary="Download Sentinel-1 products and execute flood analysis",
)
async def acquire_and_analyze(
    request: CopernicusAcquisitionRequest,
) -> CopernicusAcquisitionResponse:
    """
    Download pre-flood and post-flood Sentinel-1 IW GRD products from Copernicus
    Data Space, extract measurement GeoTIFFs, and pass them into the flood detection pipeline.
    """
    client = CopernicusDataSpaceClient()

    result = client.acquire_and_analyze(
        pre_product_id=request.pre_product_id,
        post_product_id=request.post_product_id,
        polarization=request.polarization,
        run_pipeline=request.run_pipeline,
        download_only=request.download_only,
        method=request.method,
        threshold=request.threshold,
        simplify_tolerance=request.simplify_tolerance,
        buffer_m=request.buffer_m,
    )

    if not result.get("success"):
        return CopernicusAcquisitionResponse(
            success=False,
            error=result.get("error", "Acquisition or analysis failed."),
            notes=result.get("notes", []),
        )

    return CopernicusAcquisitionResponse(
        success=True,
        pre_file_path=result.get("pre_file_path"),
        post_file_path=result.get("post_file_path"),
        pre_product_name=result.get("pre_product_name"),
        post_product_name=result.get("post_product_name"),
        detection=result.get("detection"),
        pipeline=result.get("pipeline"),
        notes=result.get("notes", []),
        error=None,
    )
