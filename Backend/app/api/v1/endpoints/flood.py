"""
Flood Analysis API Endpoints for SatQuery Phase 1.

Provides endpoints for:
- Image upload validation
- Flood detection
- Polygon generation
- Impact analysis
- Evacuation candidate analysis
- Full pipeline execution
"""

import os
import uuid
import tempfile
from typing import Any, Dict, Optional

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse, FileResponse

from app.core.config import settings
from app.schemas.flood import (
    UploadValidationResponse,
    ImageValidationResult,
    FloodDetectionResult,
    FloodPolygonResult,
    ImageStudyResult,
    ImpactMetrics,
    AffectedVillage,
    PriorityScore,
    EvacuationCandidatesResult,
    EvacuationCandidate,
    VLMAnalysisResult,
    PipelineResult,
)

# In-memory session cache: session_id -> {mask_array, transform, crs, flood_geojson, pipeline_result, ...}
_session_cache: Dict[str, Dict[str, Any]] = {}

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _save_temp(upload_file: Any, suffix: str, tmpdir: str) -> str:
    """Save an uploaded file to a temp directory synchronously."""
    path = os.path.join(tmpdir, f"{uuid.uuid4().hex}{suffix}")
    content = upload_file.file.read()
    with open(path, "wb") as f:
        f.write(content)
    return path


def _cleanup_files(*paths: str) -> None:
    """Remove temporary files, ignoring errors."""
    for p in paths:
        try:
            if p and os.path.isfile(p):
                os.remove(p)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# 1. Validate Image Pair
# ---------------------------------------------------------------------------

@router.post(
    "/validate",
    response_model=UploadValidationResponse,
    summary="Validate pre/post GeoTIFF image pair",
)
async def validate_images(
    background_tasks: BackgroundTasks,
    pre_flood: UploadFile = File(..., description="Pre-flood GeoTIFF image"),
    post_flood: UploadFile = File(..., description="Post-flood GeoTIFF image"),
) -> UploadValidationResponse:
    """
    Validate that both uploaded images are valid GeoTIFFs with geospatial metadata.
    Checks CRS, bounding box overlap, and dimension compatibility.
    """
    from app.services.image_validation import validate_image_pair

    tmpdir = tempfile.mkdtemp(prefix="satquery_")
    pre_path = _save_temp(pre_flood, ".tif", tmpdir)
    post_path = _save_temp(post_flood, ".tif", tmpdir)

    background_tasks.add_task(_cleanup_files, pre_path, post_path)

    result = validate_image_pair(pre_path, post_path)

    pre_result = ImageValidationResult(
        filename=pre_flood.filename or "pre_flood.tif", **{
            k: v for k, v in result["pre_flood"].items() if k != "filename"
        }
    )
    post_result = ImageValidationResult(
        filename=post_flood.filename or "post_flood.tif", **{
            k: v for k, v in result["post_flood"].items() if k != "filename"
        }
    )

    return UploadValidationResponse(
        pre_flood=pre_result,
        post_flood=post_result,
        compatible=result["compatible"],
        compatibility_notes=result["compatibility_notes"],
    )


# ---------------------------------------------------------------------------
# 2. Flood Detection
# ---------------------------------------------------------------------------

@router.post(
    "/detect",
    response_model=FloodDetectionResult,
    summary="Detect flood extent from image pair",
)
async def detect_flood(
    pre_flood: UploadFile = File(...),
    post_flood: UploadFile = File(...),
    method: str = Form("auto"),
    ndwi_green_band: int = Form(2),
    ndwi_nir_band: int = Form(4),
    morphology_iterations: int = Form(2),
    threshold: Optional[float] = Form(None),
    sar_polarization: Optional[str] = Form("auto"),
) -> FloodDetectionResult:
    """
    Run deterministic flood detection on uploaded GeoTIFF pair.
    Stores the flood mask in the session cache for downstream steps.
    """
    from app.services.flood_detection import FloodDetectionService

    session_id = uuid.uuid4().hex
    tmpdir = tempfile.mkdtemp(prefix="satquery_")
    pre_path = _save_temp(pre_flood, ".tif", tmpdir)
    post_path = _save_temp(post_flood, ".tif", tmpdir)

    options = {
        "method": method,
        "ndwi_green_band": ndwi_green_band,
        "ndwi_nir_band": ndwi_nir_band,
        "morphology_iterations": morphology_iterations,
        "threshold": threshold,
        "sar_polarization": sar_polarization,
    }

    result = FloodDetectionService().detect(pre_path, post_path, options)

    if result.get("success"):
        import rasterio
        with rasterio.open(pre_path) as ds:
            transform = ds.transform
            crs_wkt = ds.crs.to_wkt() if ds.crs else "EPSG:4326"

        _session_cache[session_id] = {
            "mask_array": result.pop("mask_array", None),
            "transform": transform,
            "crs_wkt": crs_wkt,
            "detection_result": result,
        }
        result["session_id"] = session_id

    _cleanup_files(pre_path, post_path)

    return FloodDetectionResult(**{k: v for k, v in result.items() if k in FloodDetectionResult.model_fields})


@router.post(
    "/detect/gee",
    response_model=FloodDetectionResult,
    summary="Detect real flood extent using Google Earth Engine Sentinel-1 GRD imagery",
)
async def detect_flood_gee(
    pre_start: str = Form("2019-10-15"),
    pre_end: str = Form("2019-11-04"),
    post_start: str = Form("2019-11-05"),
    post_end: str = Form("2019-11-15"),
    min_lon: float = Form(-1.25),
    min_lat: float = Form(53.50),
    max_lon: float = Form(-0.90),
    max_lat: float = Form(53.65),
    threshold_db: float = Form(-2.0),
    polarization: str = Form("VV"),
    pass_direction: str = Form("ASCENDING"),
) -> FloodDetectionResult:
    """
    Run real GEE Sentinel-1 SAR change detection for South Yorkshire / River Don (or custom AOI).
    Stores real flood mask and GeoJSON in session cache for downstream steps.
    """
    from app.services.gee_flood_detection import GEEFloodDetectionService

    session_id = uuid.uuid4().hex
    bbox = [min_lon, min_lat, max_lon, max_lat]

    gee_svc = GEEFloodDetectionService()
    result = gee_svc.detect_flood_sentinel1(
        bbox=bbox,
        pre_start=pre_start,
        pre_end=pre_end,
        post_start=post_start,
        post_end=post_end,
        threshold_db=threshold_db,
        polarization=polarization,
        pass_direction=pass_direction,
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"GEE Sentinel-1 flood detection failed: {result.get('error')}",
        )

    geojson = result.get("geojson")
    _session_cache[session_id] = {
        "flood_geojson": geojson,
        "detection_result": result,
        "crs_wkt": "EPSG:4326",
    }

    return FloodDetectionResult(**{k: v for k, v in result.items() if k in FloodDetectionResult.model_fields})


@router.post(
    "/image-study",
    response_model=ImageStudyResult,
    summary="Run Flood Image Study on dual georeferenced GeoTIFF rasters",
)
async def run_image_study(
    background_tasks: BackgroundTasks,
    pre_flood: UploadFile = File(..., description="Pre-flood georeferenced GeoTIFF image"),
    post_flood: UploadFile = File(..., description="Post-flood georeferenced GeoTIFF image"),
    method: str = Form("auto"),
) -> ImageStudyResult:
    """
    Run flood change detection and centroid calculation on two uploaded GeoTIFF rasters.
    Validates CRS/geotransform and rejects non-georeferenced images.
    Returns georeferenced flood GeoJSON, polygon count, flood area, and centroid coordinates.
    """
    from app.services.image_study import ImageStudyService

    session_id = uuid.uuid4().hex
    tmpdir = tempfile.mkdtemp(prefix="satquery_imagestudy_")
    pre_path = _save_temp(pre_flood, f"_pre_{session_id}.tif", tmpdir)
    post_path = _save_temp(post_flood, f"_post_{session_id}.tif", tmpdir)
    background_tasks.add_task(_cleanup_files, pre_path, post_path)

    try:
        svc = ImageStudyService()
        result = svc.analyze_pair(pre_path, post_path, options={"method": method})
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Image Study processing failed: {exc}",
        )

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Image Study analysis failed."),
        )

    result["session_id"] = session_id
    _session_cache[session_id] = {
        "flood_geojson": result.get("geojson"),
        "image_study_result": result,
    }

    return ImageStudyResult(**{k: v for k, v in result.items() if k in ImageStudyResult.model_fields})


# ---------------------------------------------------------------------------
# 3. Polygonize Flood Mask
# ---------------------------------------------------------------------------

@router.post(
    "/polygonize",
    response_model=FloodPolygonResult,
    summary="Convert flood mask to GeoJSON polygons",
)
async def polygonize(
    session_id: str = Form(...),
    simplify_tolerance: float = Form(0.0001),
) -> FloodPolygonResult:
    """
    Convert a previously computed flood mask to GeoJSON vector polygons.
    Requires a session_id from a prior /detect call.
    """
    from app.services.polygon_generation import PolygonGenerationService

    session = _session_cache.get(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found. Run /detect first.",
        )

    mask_array = session.get("mask_array")
    transform = session.get("transform")
    crs_wkt = session.get("crs_wkt", "EPSG:4326")

    if mask_array is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Flood mask not found in session. Run /detect first.",
        )

    result = PolygonGenerationService().generate(mask_array, transform, crs_wkt, simplify_tolerance)

    if result.get("success") and result.get("geojson"):
        _session_cache[session_id]["flood_geojson"] = result["geojson"]
        _session_cache[session_id]["polygon_result"] = result

    return FloodPolygonResult(**{k: v for k, v in result.items() if k in FloodPolygonResult.model_fields})


# ---------------------------------------------------------------------------
# 4. Impact Analysis
# ---------------------------------------------------------------------------

@router.post(
    "/impact",
    summary="Calculate flood impact metrics from GIS datasets",
)
async def analyze_impact(session_id: str = Form(...)):
    """
    Compute flood impact metrics by overlaying flood polygons with available GIS datasets.
    Results depend on which datasets are loaded in the data/ directory.
    """
    from app.services.exposure_analysis import ExposureAnalysisService
    from app.services.impact_scoring import ImpactScoringService
    from app.services.gis_repository import GISRepository

    session = _session_cache.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    flood_geojson = session.get("flood_geojson")
    if not flood_geojson:
        raise HTTPException(
            status_code=422,
            detail="Flood polygon GeoJSON not found. Run /polygonize first.",
        )

    gis_repo = GISRepository(settings.DATA_DIR)
    exposure_svc = ExposureAnalysisService()
    exposure = exposure_svc.calculate_exposure(flood_geojson, session_id, gis_repo)

    priority = ImpactScoringService().compute_priority_scores(exposure)

    _session_cache[session_id]["impact"] = exposure
    _session_cache[session_id]["priority_scores"] = priority

    return {
        "impact": exposure,
        "priority_scores": priority,
    }


# ---------------------------------------------------------------------------
# 5. Evacuation Candidates
# ---------------------------------------------------------------------------

@router.post(
    "/evacuation",
    summary="Identify candidate accessible sites for on-ground verification",
)
async def find_evacuation_candidates(
    session_id: str = Form(...),
    buffer_m: float = Form(100.0),
):
    """
    Identify candidate accessible sites outside the flood boundary.
    IMPORTANT: Results require on-ground verification. Not guaranteed safe zones.
    """
    from app.services.evacuation import EvacuationService
    from app.services.gis_repository import GISRepository

    session = _session_cache.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    flood_geojson = session.get("flood_geojson")
    if not flood_geojson:
        raise HTTPException(
            status_code=422,
            detail="Flood polygon GeoJSON not found. Run /polygonize first.",
        )

    gis_repo = GISRepository(settings.DATA_DIR)
    evac_result = EvacuationService().find_candidates(flood_geojson, gis_repo, buffer_m)
    _session_cache[session_id]["evacuation"] = evac_result

    return evac_result


# ---------------------------------------------------------------------------
# 6. Full Pipeline
# ---------------------------------------------------------------------------

@router.post(
    "/pipeline",
    response_model=PipelineResult,
    summary="Run complete flood analysis pipeline end-to-end",
)
async def run_full_pipeline(
    pre_flood: UploadFile = File(...),
    post_flood: UploadFile = File(...),
    method: str = Form("auto"),
    simplify_tolerance: float = Form(0.0001),
    buffer_m: float = Form(100.0),
    threshold: Optional[float] = Form(None),
    sar_polarization: Optional[str] = Form("auto"),
) -> PipelineResult:
    """
    Execute the complete flood analysis pipeline in one request:
    Validate → Detect → Polygonize → Impact Analysis → Evacuation Candidates.

    Returns a consolidated PipelineResult. Optional steps that fail
    (due to missing GIS datasets) are reported but do not abort the pipeline.
    """
    from app.services.image_validation import validate_image_pair
    from app.services.flood_detection import FloodDetectionService
    from app.services.polygon_generation import PolygonGenerationService
    from app.services.exposure_analysis import ExposureAnalysisService
    from app.services.impact_scoring import ImpactScoringService
    from app.services.evacuation import EvacuationService
    from app.services.gis_repository import GISRepository

    session_id = uuid.uuid4().hex
    warnings = []
    tmpdir = tempfile.mkdtemp(prefix="satquery_")
    pre_path = _save_temp(pre_flood, f"_pre_{session_id}.tif", tmpdir)
    post_path = _save_temp(post_flood, f"_post_{session_id}.tif", tmpdir)

    pipeline = PipelineResult(session_id=session_id)

    # Step 1: Validate
    try:
        val_raw = validate_image_pair(pre_path, post_path)
        pre_r = ImageValidationResult(
            filename=pre_flood.filename or "pre_flood.tif",
            **{k: v for k, v in val_raw["pre_flood"].items() if k != "filename"},
        )
        post_r = ImageValidationResult(
            filename=post_flood.filename or "post_flood.tif",
            **{k: v for k, v in val_raw["post_flood"].items() if k != "filename"},
        )
        pipeline.validation = UploadValidationResponse(
            pre_flood=pre_r,
            post_flood=post_r,
            compatible=val_raw["compatible"],
            compatibility_notes=val_raw["compatibility_notes"],
        )
        if not val_raw["compatible"]:
            warnings.append("Image pair compatibility issues detected; proceeding anyway.")
    except Exception as exc:
        warnings.append(f"Validation step failed: {exc}")

    # Step 2: Detect
    detection_result_raw = None
    mask_array = None
    transform_obj = None
    crs_wkt = "EPSG:4326"
    try:
        options = {
            "method": method,
            "morphology_iterations": 2,
            "threshold": threshold,
            "sar_polarization": sar_polarization,
        }
        det_svc = FloodDetectionService()
        detection_result_raw = det_svc.detect(pre_path, post_path, options)
        mask_array = detection_result_raw.pop("mask_array", None)

        import rasterio
        with rasterio.open(pre_path) as ds:
            transform_obj = ds.transform
            crs_wkt = ds.crs.to_wkt() if ds.crs else "EPSG:4326"

        pipeline.detection = FloodDetectionResult(
            **{k: v for k, v in detection_result_raw.items() if k in FloodDetectionResult.model_fields}
        )
    except Exception as exc:
        warnings.append(f"Detection step failed: {exc}")
        pipeline.error = str(exc)

    # Step 3: Polygonize
    flood_geojson = None
    if mask_array is not None:
        try:
            poly_svc = PolygonGenerationService()
            poly_result = poly_svc.generate(mask_array, transform_obj, crs_wkt, simplify_tolerance)
            pipeline.polygons = FloodPolygonResult(
                **{k: v for k, v in poly_result.items() if k in FloodPolygonResult.model_fields}
            )
            flood_geojson = poly_result.get("geojson")
        except Exception as exc:
            warnings.append(f"Polygonization step failed: {exc}")

    # Step 4: Impact Analysis
    if flood_geojson:
        try:
            gis_repo = GISRepository(settings.DATA_DIR)
            exposure_svc = ExposureAnalysisService()
            exposure = exposure_svc.calculate_exposure(flood_geojson, session_id, gis_repo)

            affected_villages = [
                AffectedVillage(**v) for v in exposure.get("affected_villages", [])
            ]
            pipeline.impact = ImpactMetrics(
                affected_villages=affected_villages,
                affected_population=exposure.get("affected_population"),
                affected_buildings=exposure.get("affected_buildings"),
                affected_road_length_km=exposure.get("affected_road_length_km"),
                affected_villages_geojson=exposure.get("affected_villages_geojson"),
                affected_roads_geojson=exposure.get("affected_roads_geojson"),
                affected_buildings_geojson=exposure.get("affected_buildings_geojson"),
                data_availability=exposure.get("data_availability", {}),
                disclaimer=exposure.get("disclaimer", ""),
            )

            raw_priority = ImpactScoringService().compute_priority_scores(exposure)
            pipeline.priority_scores = [PriorityScore(**p) for p in raw_priority]
        except Exception as exc:
            warnings.append(f"Impact analysis step failed: {exc}")

        # Step 5: Evacuation Candidates
        try:
            gis_repo = GISRepository(settings.DATA_DIR)
            evac_raw = EvacuationService().find_candidates(flood_geojson, gis_repo, buffer_m)
            candidates = [EvacuationCandidate(**c) for c in evac_raw.get("candidates", [])]
            pipeline.evacuation = EvacuationCandidatesResult(
                candidates=candidates,
                total_found=evac_raw.get("total_found", 0),
                filtered_reason=evac_raw.get("filtered_reason", ""),
                disclaimer=evac_raw.get("disclaimer", ""),
            )
        except Exception as exc:
            warnings.append(f"Evacuation analysis step failed: {exc}")

    # Step 6: VLM Visual Comparison (Gemini Multimodal visual change description)
    try:
        from app.services.orchestration import AgentOrchestrationService
        orchestration_svc = AgentOrchestrationService(api_key=settings.GEMINI_API_KEY)
        vlm_res = orchestration_svc.generate_visual_comparison(pre_path, post_path)
        pipeline.vlm_analysis = VLMAnalysisResult(**vlm_res)
    except Exception as exc:
        warnings.append(f"VLM visual comparison step encountered an error: {exc}")
        pipeline.vlm_analysis = VLMAnalysisResult(
            available=False,
            comparison="VLM visual comparison could not be performed.",
        )

    # Cache pipeline result for AI assistant
    pipeline.warnings = warnings
    _session_cache[session_id] = {
        "mask_array": mask_array,
        "transform": transform_obj,
        "crs_wkt": crs_wkt,
        "flood_geojson": flood_geojson,
        "pipeline_result": pipeline.model_dump(),
    }

    _cleanup_files(pre_path, post_path)
    return pipeline


# ---------------------------------------------------------------------------
# 7. Spatial Layers Access
# ---------------------------------------------------------------------------

@router.get(
    "/buildings",
    summary="Retrieve building footprints GeoJSON",
)
async def get_buildings():
    """Return building footprints GeoJSON from data/buildings/."""
    from app.services.gis_repository import GISRepository
    import json
    gis_repo = GISRepository(settings.DATA_DIR)
    bld_gdf = gis_repo.load_layer("buildings")
    if bld_gdf is not None:
        if bld_gdf.crs != "EPSG:4326":
            bld_gdf = bld_gdf.to_crs("EPSG:4326")
        return json.loads(bld_gdf.to_json())
    return {"type": "FeatureCollection", "features": []}


# ---------------------------------------------------------------------------
# 8. Session Management
# ---------------------------------------------------------------------------

@router.get(
    "/session/{session_id}",
    summary="Retrieve cached session results",
)
async def get_session_results(session_id: str):
    """Return cached pipeline results for a given session ID."""
    session = _session_cache.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    # Return only serializable data (exclude numpy arrays)
    return {k: v for k, v in session.items() if k not in ("mask_array", "transform")}


@router.delete(
    "/session/{session_id}",
    summary="Delete a cached session",
)
async def delete_session(session_id: str):
    """Remove a session from the in-memory cache."""
    if session_id in _session_cache:
        del _session_cache[session_id]
        return {"deleted": True, "session_id": session_id}
    raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")


# ---------------------------------------------------------------------------
# 9. Sample Test Images
# ---------------------------------------------------------------------------

@router.get(
    "/sample/{sample_name}",
    summary="Download sample satellite GeoTIFF files",
)
async def get_sample_image(sample_name: str):
    """Serve real Kerala pre/post flood sample images."""
    allowed = {
        "pre": "kerala_before_flood.tif",
        "post": "kerala_after_flood.tif",
        "kerala_before_flood.tif": "kerala_before_flood.tif",
        "kerala_after_flood.tif": "kerala_after_flood.tif",
    }
    if sample_name not in allowed:
        raise HTTPException(status_code=404, detail="Sample image not found")
    filename = allowed[sample_name]
    path = os.path.join(settings.DATA_DIR, "test_images", filename)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail=f"Sample file '{filename}' missing on disk")
    return FileResponse(path, media_type="image/tiff", filename=filename)
