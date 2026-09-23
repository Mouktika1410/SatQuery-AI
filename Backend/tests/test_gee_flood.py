"""
End-to-End Integration Test for Real GEE Sentinel-1 Flood Detection.

Tests the real flood-polygon detection pipeline using Google Earth Engine
and Sentinel-1 GRD imagery for the November 2019 South Yorkshire / River Don flood event.
"""

import os
import sys
import logging
import unittest
from typing import Any, Dict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.gee_flood_detection import GEEFloodDetectionService

logger = logging.getLogger(__name__)


def test_gee_sentinel1_south_yorkshire_nov2019():
    """
    Run an end-to-end test of real Sentinel-1 SAR flood detection
    on the South Yorkshire / River Don November 2019 event.

    Verifies:
    1. Real before acquisition dates & metadata
    2. Real post/flood acquisition dates & metadata
    3. Orbit direction & polarization (IW, VV, ASCENDING)
    4. Flood-mask pixel statistics (flooded_pixels > 0, total_pixels > 0)
    5. Polygon count (> 0)
    6. Flood area in km² (> 0)
    7. Valid WGS84 GeoJSON FeatureCollection
    """
    print("\n--- Running Real GEE Sentinel-1 Flood Detection Test ---")
    gee_svc = GEEFloodDetectionService(project_id="satquery-flood-detection")

    # South Yorkshire / River Don bounding box and dates for Nov 2019 flood
    bbox = [-1.25, 53.50, -0.90, 53.65]
    pre_start, pre_end = "2019-10-15", "2019-11-04"
    post_start, post_end = "2019-11-05", "2019-11-15"

    result = gee_svc.detect_flood_sentinel1(
        bbox=bbox,
        pre_start=pre_start,
        pre_end=pre_end,
        post_start=post_start,
        post_end=post_end,
        threshold_db=-2.0,
        smoothing_radius=50,
        polarization="VV",
        pass_direction="ASCENDING",
    )

    # Assertion 1: Success flag
    assert result.get("success") is True, f"GEE detection failed: {result.get('error')}"

    # Assertion 2: Real Acquisition Metadata & Timestamps
    meta = result.get("acquisition_metadata")
    assert meta is not None, "Missing acquisition metadata"
    assert meta["gee_project"] == "satquery-flood-detection"
    assert meta["instrument_mode"] == "IW"
    assert meta["polarization"] == "VV"
    assert meta["orbit_pass"] == "ASCENDING"

    pre_info = meta["pre_event"]
    post_info = meta["post_event"]

    assert len(pre_info["scene_ids"]) > 0, "No pre-event Sentinel-1 scenes found"
    assert len(post_info["scene_ids"]) > 0, "No post-event Sentinel-1 scenes found"

    print(f"  [OK] Pre-event S1 scenes ({pre_info['scene_count']}): {pre_info['scene_ids'][:2]}")
    print(f"  [OK] Pre-event timestamps: {pre_info['acquisition_timestamps'][:2]}")
    print(f"  [OK] Post-event S1 scenes ({post_info['scene_count']}): {post_info['scene_ids'][:2]}")
    print(f"  [OK] Post-event timestamps: {post_info['acquisition_timestamps'][:2]}")

    # Assertion 3: Flood-mask statistics
    flooded_px = result.get("flooded_pixels", 0)
    total_px = result.get("total_pixels", 0)
    flood_pct = result.get("flood_percentage", 0.0)

    assert flooded_px > 0, f"Expected flooded_pixels > 0, got {flooded_px}"
    assert total_px > 0, f"Expected total_pixels > 0, got {total_px}"
    print(f"  [OK] Flood Mask Stats: {flooded_px}/{total_px} pixels flooded ({flood_pct:.4f}%)")

    # Assertion 4: Polygon count and flood area
    polygon_count = result.get("polygon_count", 0)
    flood_area_km2 = result.get("flood_area_km2", 0.0)

    assert polygon_count > 0, f"Expected polygon_count > 0, got {polygon_count}"
    assert flood_area_km2 > 0.0, f"Expected flood_area_km2 > 0, got {flood_area_km2}"
    print(f"  [OK] Vectorized Flood Polygons: {polygon_count} polygon(s)")
    print(f"  [OK] Total Detected Flood Area: {flood_area_km2:.4f} km2 ({result.get('flood_area_ha'):.2f} ha)")

    # Assertion 5: Valid GeoJSON
    geojson = result.get("geojson")
    assert geojson is not None, "Missing GeoJSON"
    assert geojson.get("type") == "FeatureCollection", f"Expected FeatureCollection, got {geojson.get('type')}"
    features = geojson.get("features", [])
    assert len(features) > 0, "GeoJSON feature list is empty"
    first_geom = features[0].get("geometry", {})
    assert first_geom.get("type") in ("Polygon", "MultiPolygon"), f"Invalid geometry type: {first_geom.get('type')}"
    assert len(first_geom.get("coordinates", [])) > 0, "Empty geometry coordinates"

    print("  [OK] GeoJSON Validation: Valid FeatureCollection with real Sentinel-1 flood polygon geometries!")
    print("--- Real GEE Sentinel-1 Flood Detection Test Passed! ---\n")
    return True


if __name__ == "__main__":
    test_gee_sentinel1_south_yorkshire_nov2019()
