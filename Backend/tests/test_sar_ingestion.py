"""
Unit and integration tests for Sentinel-1 SAR GeoTIFF ingestion and flood detection.

Tests cover:
1. Validation of Sentinel-1 single-band (VV) and dual-band (VV/VH) GeoTIFFs.
2. Calibrated decibel (dB) backscatter ingestion (-35 to +5 dB range).
3. Linear amplitude / intensity backscatter conversion.
4. Specular reflection change detection (radar backscatter drop over flooded areas).
5. Cross-CRS reprojection (e.g., UTM Zone 43N to WGS84).
6. Full end-to-end pipeline execution on Sentinel-1 SAR imagery.
"""

import os
import tempfile
import numpy as np
import pytest

rasterio = pytest.importorskip("rasterio", reason="rasterio not installed")
import rasterio
from rasterio.transform import from_bounds, from_origin
from rasterio.crs import CRS


# ---------------------------------------------------------------------------
# Helper: create synthetic Sentinel-1 SAR GeoTIFF
# ---------------------------------------------------------------------------

def create_sentinel1_geotiff(
    path: str,
    width: int = 64,
    height: int = 64,
    bands: int = 1,
    data: np.ndarray = None,
    epsg: int = 32643,  # UTM Zone 43N (typical projected CRS for Western India)
    pixel_size_m: float = 10.0,  # 10m Sentinel-1 GRD resolution
    polarizations: list = None,
    nodata: float = -9999.0,
    dtype: str = "float32",
) -> str:
    """
    Write a synthetic Sentinel-1 SAR GeoTIFF matching GRD product specifications.
    """
    if data is None:
        # Default SAR dB range: dry land background between -13 dB and -8 dB
        data = (-12.0 + np.random.randn(bands, height, width) * 1.5).astype(np.float32)
    elif data.ndim == 2:
        data = data[np.newaxis, :, :]

    # Projected UTM coordinates (origin near Mumbai UTM 43N)
    transform = from_origin(270000.0, 2100000.0, pixel_size_m, pixel_size_m)
    crs = CRS.from_epsg(epsg)

    profile = {
        "driver": "GTiff",
        "dtype": getattr(rasterio, dtype),
        "width": width,
        "height": height,
        "count": bands,
        "crs": crs,
        "transform": transform,
        "nodata": nodata,
    }

    with rasterio.open(path, "w", **profile) as dst:
        dst.write(data)
        # Set band descriptions (e.g. 'VV', 'VH')
        if polarizations:
            for idx, pol in enumerate(polarizations, start=1):
                dst.set_band_description(idx, pol)
        elif bands == 1:
            dst.set_band_description(1, "VV")
        elif bands == 2:
            dst.set_band_description(1, "VV")
            dst.set_band_description(2, "VH")

        # Set Sentinel-1 SAR metadata tags
        dst.update_tags(
            SENSOR="SENTINEL-1",
            ACQUISITION_MODE="IW",
            PRODUCT_TYPE="GRD",
        )

    return path


# ---------------------------------------------------------------------------
# Test 1: Validate Sentinel-1 SAR GeoTIFF in Decibels
# ---------------------------------------------------------------------------

def test_validate_sentinel1_sar_geotiff_db():
    """Verify that a single-band Sentinel-1 VV GeoTIFF in dB is recognized as SAR."""
    from app.services.image_validation import validate_geotiff

    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "S1A_IW_GRDH_VV.tif")
        # Typical SAR dB values: mean -11 dB
        data = np.full((1, 48, 48), -11.5, dtype=np.float32)
        create_sentinel1_geotiff(path, width=48, height=48, data=data, polarizations=["VV"])

        result = validate_geotiff(path)

    assert result["valid"] is True
    assert result["is_sar"] is True
    assert result["sensor"] == "Sentinel-1 SAR"
    assert result["polarizations"] == ["VV"]
    assert result["crs_epsg"] == 32643
    assert result["width"] == 48
    assert result["height"] == 48


# ---------------------------------------------------------------------------
# Test 2: Validate Dual-Polarization (VV + VH) Sentinel-1 GeoTIFF
# ---------------------------------------------------------------------------

def test_validate_sentinel1_sar_dual_pol():
    """Verify dual-pol (VV, VH) Sentinel-1 GeoTIFF extracts both polarizations."""
    from app.services.image_validation import validate_geotiff

    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "S1_dual_pol.tif")
        b1_vv = np.full((1, 32, 32), -11.0, dtype=np.float32)
        b2_vh = np.full((1, 32, 32), -17.0, dtype=np.float32)
        dual_data = np.concatenate([b1_vv, b2_vh], axis=0)
        create_sentinel1_geotiff(path, width=32, height=32, bands=2, data=dual_data, polarizations=["VV", "VH"])

        result = validate_geotiff(path)

    assert result["valid"] is True
    assert result["is_sar"] is True
    assert result["band_count"] == 2
    assert set(result["polarizations"]) == {"VV", "VH"}


# ---------------------------------------------------------------------------
# Test 3: Validate SAR Image Pair Compatibility
# ---------------------------------------------------------------------------

def test_validate_sar_image_pair_compatibility():
    """Validate spatial compatibility between pre and post Sentinel-1 SAR acquisitions."""
    from app.services.image_validation import validate_image_pair

    with tempfile.TemporaryDirectory() as tmpdir:
        pre_path = os.path.join(tmpdir, "pre_s1.tif")
        post_path = os.path.join(tmpdir, "post_s1.tif")

        create_sentinel1_geotiff(pre_path, width=64, height=64)
        create_sentinel1_geotiff(post_path, width=64, height=64)

        result = validate_image_pair(pre_path, post_path)

    assert result["compatible"] is True
    assert result["pre_flood"]["is_sar"] is True
    assert result["post_flood"]["is_sar"] is True
    notes_text = " ".join(result["compatibility_notes"])
    assert "Sentinel-1 SAR image pair validated" in notes_text


# ---------------------------------------------------------------------------
# Test 4: SAR Flood Detection via Specular Reflection Drop (Calibrated dB)
# ---------------------------------------------------------------------------

def test_sar_flood_detection_specular_drop_db():
    """
    Test flood detection on Sentinel-1 SAR data in calibrated decibels.
    Water causes specular reflection -> significant backscatter drop.
    """
    from app.services.flood_detection import FloodDetectionService

    with tempfile.TemporaryDirectory() as tmpdir:
        pre_path = os.path.join(tmpdir, "pre_flood_s1.tif")
        post_path = os.path.join(tmpdir, "post_flood_s1.tif")

        # 64x64 grid
        # Pre-flood: dry land background (-11 dB)
        np.random.seed(42)
        pre_data = (-11.0 + np.random.randn(1, 64, 64) * 0.5).astype(np.float32)

        # Post-flood: background is still dry land (-11 dB),
        # but a 24x24 central region is inundated -> backscatter drops to -22 dB
        post_data = pre_data.copy()
        post_data[0, 20:44, 20:44] = (-22.0 + np.random.randn(24, 24) * 0.5).astype(np.float32)

        create_sentinel1_geotiff(pre_path, width=64, height=64, data=pre_data)
        create_sentinel1_geotiff(post_path, width=64, height=64, data=post_data)

        # Run auto detection (should auto-detect SAR)
        service = FloodDetectionService()
        result = service.detect(pre_path, post_path, options={"method": "auto", "morphology_iterations": 1})

    assert result["success"] is True
    assert result["method_used"] == "sar+otsu"
    assert result["flooded_pixels"] > 0

    # The flooded patch is 24x24 = 576 pixels (with minor boundary filtering)
    assert 450 <= result["flooded_pixels"] <= 600

    # Check that notes mention SAR backscatter drop
    notes_str = " ".join(result["notes"])
    assert "Sentinel-1 SAR detection" in notes_str
    assert "calibrated decibels (dB)" in notes_str


# ---------------------------------------------------------------------------
# Test 5: SAR Flood Detection from Linear Amplitude (Power / DN Conversion)
# ---------------------------------------------------------------------------

def test_sar_flood_detection_linear_amplitude():
    """
    Test flood detection when SAR data is provided in linear amplitude / power units.
    Pipeline converts linear values to decibel scale before thresholding.
    """
    from app.services.flood_detection import FloodDetectionService

    with tempfile.TemporaryDirectory() as tmpdir:
        pre_path = os.path.join(tmpdir, "pre_linear.tif")
        post_path = os.path.join(tmpdir, "post_linear.tif")

        # Linear amplitude: land ~ 250 DN (amplitude), water ~ 30 DN
        np.random.seed(42)
        pre_data = (250.0 + np.random.randn(1, 64, 64) * 15.0).astype(np.float32)
        post_data = pre_data.copy()
        post_data[0, 20:44, 20:44] = (30.0 + np.random.randn(24, 24) * 5.0).astype(np.float32)

        create_sentinel1_geotiff(pre_path, width=64, height=64, data=pre_data, dtype="float32")
        create_sentinel1_geotiff(post_path, width=64, height=64, data=post_data, dtype="float32")

        service = FloodDetectionService()
        result = service.detect(pre_path, post_path, options={"method": "sar", "morphology_iterations": 1})

    assert result["success"] is True
    assert result["flooded_pixels"] > 400
    notes_str = " ".join(result["notes"])
    assert "decibel scale (dB)" in notes_str


# ---------------------------------------------------------------------------
# Test 6: Cross-CRS Reprojection (Pre in WGS84, Post in UTM Zone 43N)
# ---------------------------------------------------------------------------

def test_sar_cross_crs_reprojection():
    """
    Test that differing CRSs (e.g. pre in EPSG:4326, post in UTM 32643)
    are automatically reprojected and aligned.
    """
    from app.services.flood_detection import FloodDetectionService

    with tempfile.TemporaryDirectory() as tmpdir:
        pre_path = os.path.join(tmpdir, "pre_wgs84.tif")
        post_path = os.path.join(tmpdir, "post_utm.tif")

        # Pre in WGS84 (bounds around Mumbai: 72.8 to 73.0, 18.9 to 19.1)
        wgs_transform = from_bounds(72.8, 18.9, 73.0, 19.1, 64, 64)
        pre_data = np.full((1, 64, 64), -11.0, dtype=np.float32)

        with rasterio.open(
            pre_path, "w",
            driver="GTiff", dtype=rasterio.float32, width=64, height=64, count=1,
            crs=CRS.from_epsg(4326), transform=wgs_transform, nodata=-9999.0
        ) as dst:
            dst.write(pre_data)
            dst.set_band_description(1, "VV")

        # Post in UTM 43N matching approximately the same geographic extent
        create_sentinel1_geotiff(post_path, width=64, height=64)

        service = FloodDetectionService()
        result = service.detect(pre_path, post_path, options={"method": "sar"})

    assert result["success"] is True
    notes_str = " ".join(result["notes"])
    assert "reprojected" in notes_str.lower()


# ---------------------------------------------------------------------------
# Test 7: Full End-to-End Pipeline Execution on Sentinel-1 SAR
# ---------------------------------------------------------------------------

def test_full_pipeline_sentinel1_sar():
    """
    Full pipeline execution on Sentinel-1 SAR GeoTIFFs:
    Validate -> Detect -> Polygonize -> Impact Analysis.
    """
    from app.services.image_validation import validate_image_pair
    from app.services.flood_detection import FloodDetectionService
    from app.services.polygon_generation import PolygonGenerationService
    from app.services.exposure_analysis import ExposureAnalysisService
    from app.services.gis_repository import GISRepository

    with tempfile.TemporaryDirectory() as tmpdir:
        pre_path = os.path.join(tmpdir, "S1A_pre.tif")
        post_path = os.path.join(tmpdir, "S1A_post.tif")

        # Create realistic SAR data
        # WGS84 for direct overlap with demo villages around Mumbai (72.8 - 73.0, 18.9 - 19.1)
        transform = from_bounds(72.8, 18.9, 73.0, 19.1, 64, 64)
        pre_data = (-11.0 + np.random.randn(1, 64, 64) * 0.3).astype(np.float32)
        post_data = pre_data.copy()
        # Inundate central region
        post_data[0, 15:45, 15:45] = -22.0

        for p, d in [(pre_path, pre_data), (post_path, post_data)]:
            with rasterio.open(
                p, "w",
                driver="GTiff", dtype=rasterio.float32, width=64, height=64, count=1,
                crs=CRS.from_epsg(4326), transform=transform, nodata=-9999.0
            ) as dst:
                dst.write(d)
                dst.set_band_description(1, "VV")
                dst.update_tags(SENSOR="SENTINEL-1", POLARISATION="VV")

        # 1. Validation
        val = validate_image_pair(pre_path, post_path)
        assert val["compatible"] is True
        assert val["pre_flood"]["is_sar"] is True

        # 2. SAR Detection
        det = FloodDetectionService().detect(pre_path, post_path, options={"method": "auto"})
        assert det["success"] is True
        assert det["method_used"] == "sar+otsu"
        mask = det["mask_array"]

        # 3. Polygonization
        with rasterio.open(pre_path) as ds:
            poly_result = PolygonGenerationService().generate(
                mask, ds.transform, ds.crs.to_wkt()
            )
        assert poly_result["success"] is True
        assert poly_result["geojson"] is not None
        assert poly_result["polygon_count"] >= 1
        assert poly_result["total_area_km2"] > 0
