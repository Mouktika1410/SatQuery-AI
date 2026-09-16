"""
Unit tests for raster validation and flood detection.

All tests use synthetic GeoTIFF data created in memory with numpy + rasterio.
No external datasets are required.
"""

import os
import math
import tempfile
import numpy as np
import pytest

rasterio = pytest.importorskip("rasterio", reason="rasterio not installed")
import rasterio
from rasterio.transform import from_bounds
from rasterio.crs import CRS


# ---------------------------------------------------------------------------
# Helper: create a synthetic GeoTIFF
# ---------------------------------------------------------------------------

def create_synthetic_geotiff(
    path: str,
    width: int = 64,
    height: int = 64,
    bands: int = 1,
    data: np.ndarray = None,
    epsg: int = 4326,
) -> str:
    """
    Write a synthetic GeoTIFF with a valid affine transform and CRS.
    If data is None, a random float32 array is generated.
    """
    if data is None:
        data = (np.random.rand(bands, height, width) * 255).astype(np.float32)
    elif data.ndim == 2:
        data = data[np.newaxis, :, :]

    # Small bounding box near Mumbai for realistic coordinates
    transform = from_bounds(72.8, 18.9, 73.0, 19.1, width, height)
    crs = CRS.from_epsg(epsg)

    profile = {
        "driver": "GTiff",
        "dtype": rasterio.float32,
        "width": width,
        "height": height,
        "count": bands,
        "crs": crs,
        "transform": transform,
        "nodata": -9999.0,
    }
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(data)
    return path


# ---------------------------------------------------------------------------
# Test 1 — Validate a valid synthetic GeoTIFF
# ---------------------------------------------------------------------------

def test_validate_geotiff_valid():
    """validate_geotiff returns valid=True for a well-formed GeoTIFF."""
    from app.services.image_validation import validate_geotiff

    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test.tif")
        create_synthetic_geotiff(path, width=32, height=32, bands=1)

        result = validate_geotiff(path)

    assert result["valid"] is True, f"Expected valid, got error: {result.get('error')}"
    assert result["width"] == 32
    assert result["height"] == 32
    assert result["band_count"] == 1
    assert result["crs"] is not None
    assert result["crs_epsg"] == 4326
    assert result["bounds"] is not None
    assert result["transform"] is not None
    assert result["error"] is None


# ---------------------------------------------------------------------------
# Test 2 — Validate a missing file
# ---------------------------------------------------------------------------

def test_validate_geotiff_missing_file():
    """validate_geotiff returns valid=False for a non-existent file."""
    from app.services.image_validation import validate_geotiff

    result = validate_geotiff("/nonexistent/path/file.tif")
    assert result["valid"] is False
    assert result["error"] is not None
    assert "not found" in result["error"].lower() or "nonexistent" in result["error"].lower()


# ---------------------------------------------------------------------------
# Test 3 — Otsu threshold separates bimodal distribution
# ---------------------------------------------------------------------------

def test_otsu_threshold_bimodal():
    """Otsu threshold should separate two clearly distinct intensity classes."""
    from app.services.flood_detection import FloodDetectionService

    svc = FloodDetectionService()

    # Create a clearly bimodal array: low cluster [0..50] and high cluster [200..255]
    low = np.random.randint(0, 50, size=500).astype(np.float32)
    high = np.random.randint(200, 255, size=500).astype(np.float32)
    bimodal = np.concatenate([low, high])

    threshold = svc._otsu_threshold(bimodal)

    # The optimal threshold should be somewhere between the two clusters
    assert 50 < threshold < 200, (
        f"Otsu threshold {threshold} did not fall between the two modes (50, 200)"
    )


# ---------------------------------------------------------------------------
# Test 4 — Differencing detection on synthetic flood pair
# ---------------------------------------------------------------------------

def test_differencing_detection_synthetic():
    """
    Flood detection should find a bright rectangular region in the post-image
    when the pre-image is dark.
    """
    from app.services.flood_detection import FloodDetectionService

    with tempfile.TemporaryDirectory() as tmpdir:
        # Pre-image: uniform low values (dry baseline)
        pre_data = np.full((1, 64, 64), 10.0, dtype=np.float32)
        pre_path = os.path.join(tmpdir, "pre.tif")
        create_synthetic_geotiff(pre_path, data=pre_data)

        # Post-image: same, but with a bright rectangle (simulated flood / change)
        post_data = np.full((1, 64, 64), 10.0, dtype=np.float32)
        post_data[0, 20:45, 20:45] = 200.0  # bright flood region
        post_path = os.path.join(tmpdir, "post.tif")
        create_synthetic_geotiff(post_path, data=post_data)

        result = FloodDetectionService().detect(
            pre_path, post_path, options={"method": "differencing", "morphology_iterations": 0}
        )

    assert result["success"] is True, f"Detection failed: {result.get('error')}"
    assert result["flooded_pixels"] > 0, "Expected flooded pixels but found 0"
    assert result["flood_percentage"] > 0.0
    assert result["flood_area_km2"] >= 0.0


# ---------------------------------------------------------------------------
# Test 5 — Morphological cleanup removes isolated pixels
# ---------------------------------------------------------------------------

def test_morphological_cleanup_removes_noise():
    """Small isolated pixels should be removed after morphological cleanup."""
    scipy = pytest.importorskip("scipy", reason="scipy not installed")
    from app.services.flood_detection import FloodDetectionService

    svc = FloodDetectionService()

    # Create a mostly-zero mask with a few isolated single pixels (noise)
    mask = np.zeros((50, 50), dtype=np.uint8)
    mask[5, 5] = 1    # isolated pixel
    mask[10, 10] = 1  # isolated pixel
    mask[20:30, 20:30] = 1  # real flood region (10x10 block)

    noise_pixels_before = int(np.sum(mask)) - 100  # 100 = the 10x10 block

    cleaned = svc._morphological_cleanup(mask, iterations=1)

    # The 10x10 block should survive; isolated pixels should be removed
    assert np.sum(cleaned[20:30, 20:30]) > 0, "Real flood region should survive cleanup"
    # After cleanup, isolated pixels at (5,5) and (10,10) should be 0
    assert cleaned[5, 5] == 0, "Isolated pixel at (5,5) should be removed"
    assert cleaned[10, 10] == 0, "Isolated pixel at (10,10) should be removed"


# ---------------------------------------------------------------------------
# Test 6 — Image pair compatibility validation
# ---------------------------------------------------------------------------

def test_validate_image_pair_compatible():
    """Two images with the same CRS and overlapping bounds should be compatible."""
    from app.services.image_validation import validate_image_pair

    with tempfile.TemporaryDirectory() as tmpdir:
        pre_path = os.path.join(tmpdir, "pre.tif")
        post_path = os.path.join(tmpdir, "post.tif")
        create_synthetic_geotiff(pre_path, width=32, height=32)
        create_synthetic_geotiff(post_path, width=32, height=32)

        result = validate_image_pair(pre_path, post_path)

    assert result["pre_flood"]["valid"] is True
    assert result["post_flood"]["valid"] is True
    assert result["compatible"] is True
