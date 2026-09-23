"""
Integration Test for Image Study Workflow.

Tests dual GeoTIFF validation, change detection, centroid calculation,
and non-georeferenced image rejection.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.image_study import ImageStudyService


def test_image_study_real_geotiff_pair():
    """
    Test ImageStudyService using the exported real Sentinel-1 GeoTIFF pair for South Yorkshire Nov 2019.
    """
    print("\n--- Running Image Study Real GeoTIFF Pair Test ---")
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    pre_path = os.path.join(root_dir, "data", "test_images", "before_flood.tif")
    post_path = os.path.join(root_dir, "data", "test_images", "after_flood.tif")

    assert os.path.exists(pre_path), f"Missing test file: {pre_path}"
    assert os.path.exists(post_path), f"Missing test file: {post_path}"

    svc = ImageStudyService()

    # 1. Test metadata extraction
    pre_meta = svc.validate_and_extract_metadata(pre_path)
    post_meta = svc.validate_and_extract_metadata(post_path)

    assert pre_meta["width"] == 391
    assert pre_meta["height"] == 168
    assert "EPSG:4326" in pre_meta["crs"]
    assert post_meta["width"] == 391

    print(f"  [OK] Pre GeoTIFF Metadata: {pre_meta['width']}x{pre_meta['height']} px, CRS={pre_meta['crs']}")
    print(f"  [OK] Post GeoTIFF Metadata: {post_meta['width']}x{post_meta['height']} px, CRS={post_meta['crs']}")

    # 2. Test analysis pipeline & centroid calculation
    res = svc.analyze_pair(pre_path, post_path)
    assert res["success"] is True, f"Analysis failed: {res.get('error')}"

    assert res["polygon_count"] > 0, f"Expected polygon_count > 0, got {res['polygon_count']}"
    assert res["flood_area_km2"] > 0.0, f"Expected flood_area_km2 > 0, got {res['flood_area_km2']}"

    cent = res["centroid"]
    assert cent is not None, "Missing centroid"
    assert 53.0 <= cent["latitude"] <= 54.0, f"Expected lat ~53.5, got {cent['latitude']}"
    assert -1.5 <= cent["longitude"] <= -0.5, f"Expected lon ~ -1.0, got {cent['longitude']}"

    print(f"  [OK] Flood Area: {res['flood_area_km2']:.4f} km2 ({res['polygon_count']} polygons)")
    print(f"  [OK] Flood Polygon Centroid: Lat {cent['latitude']}° N, Lon {cent['longitude']}° W")

    # 3. Test GeoJSON structure
    geojson = res["geojson"]
    assert geojson is not None
    assert geojson["type"] == "FeatureCollection"
    assert len(geojson["features"]) > 0

    print("  [OK] WGS84 GeoJSON: Valid FeatureCollection with real flood polygons!")
    print("--- Image Study Real GeoTIFF Test Passed! ---\n")
    return True


def test_image_study_non_georeferenced_rejection():
    """
    Verify that non-georeferenced files or invalid images are rejected with a clear error.
    """
    print("--- Running Non-Georeferenced Image Rejection Test ---")
    svc = ImageStudyService()

    # Create dummy non-georeferenced plain text file pretending to be an image
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".png")
    os.write(tmp_fd, b"Not a georeferenced GeoTIFF image")
    os.close(tmp_fd)

    try:
        rejected = False
        try:
            svc.validate_and_extract_metadata(tmp_path)
        except ValueError as exc:
            rejected = True
            print(f"  [OK] Non-georeferenced file correctly rejected with message: {exc}")

        assert rejected is True, "Expected non-georeferenced file to be rejected!"
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    print("--- Non-Georeferenced Image Rejection Test Passed! ---\n")
    return True


if __name__ == "__main__":
    test_image_study_real_geotiff_pair()
    test_image_study_non_georeferenced_rejection()
