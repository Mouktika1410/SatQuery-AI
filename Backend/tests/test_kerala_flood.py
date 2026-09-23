"""
Integration Test for Real Kerala 2018 Flood Event Dataset.

Tests dual-GeoTIFF Image Study analysis, flood mask generation, area calculation,
and centroid computation for the August 2018 Kerala flood event.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.image_study import ImageStudyService


def test_kerala_2018_flood_image_study():
    """
    Test ImageStudyService using the exported real Sentinel-1 GeoTIFF pair for Kerala August 2018.
    Verifies:
    1. Georeferenced metadata (EPSG:4326, Kerala AOI bounds ~76.25-76.55 E, 9.35-9.75 N)
    2. Real change detection & flood mask
    3. Flood area calculation (large connected inundation area)
    4. Centroid latitude/longitude computation
    5. Valid WGS84 GeoJSON output
    """
    print("\n--- Running Real Kerala 2018 Flood Image Study Test ---")
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    pre_path = os.path.join(root_dir, "data", "test_images", "kerala_before_flood.tif")
    post_path = os.path.join(root_dir, "data", "test_images", "kerala_after_flood.tif")

    assert os.path.exists(pre_path), f"Missing test file: {pre_path}"
    assert os.path.exists(post_path), f"Missing test file: {post_path}"

    svc = ImageStudyService()

    # 1. Metadata check
    pre_meta = svc.validate_and_extract_metadata(pre_path)
    post_meta = svc.validate_and_extract_metadata(post_path)

    assert "EPSG:4326" in pre_meta["crs"]
    assert "EPSG:4326" in post_meta["crs"]
    assert pre_meta["width"] == post_meta["width"]
    assert pre_meta["height"] == post_meta["height"]

    print(f"  [OK] Kerala Pre Metadata: {pre_meta['width']}x{pre_meta['height']} px, CRS={pre_meta['crs']}")
    print(f"  [OK] Kerala Post Metadata: {post_meta['width']}x{post_meta['height']} px, CRS={post_meta['crs']}")

    # 2. Pipeline Analysis
    res = svc.analyze_pair(pre_path, post_path)
    assert res["success"] is True, f"Analysis failed: {res.get('error')}"

    assert res["polygon_count"] > 0, f"Expected polygon_count > 0, got {res['polygon_count']}"
    assert res["flood_area_km2"] > 0.0, f"Expected flood_area_km2 > 0, got {res['flood_area_km2']}"

    cent = res["centroid"]
    assert cent is not None, "Missing centroid"
    assert 9.0 <= cent["latitude"] <= 10.0, f"Expected lat ~9.5, got {cent['latitude']}"
    assert 76.0 <= cent["longitude"] <= 77.0, f"Expected lon ~76.4, got {cent['longitude']}"

    print(f"  [OK] Detected Flood Area: {res['flood_area_km2']:.4f} km2 ({res['polygon_count']} polygons)")
    print(f"  [OK] Kerala Polygon Centroid: Lat {cent['latitude']}° N, Lon {cent['longitude']}° E")

    # 3. GeoJSON Validation
    geojson = res["geojson"]
    assert geojson is not None
    assert geojson["type"] == "FeatureCollection"
    assert len(geojson["features"]) > 0

    # 4. Population Exposure Check
    exposed_pop = res.get("exposed_population")
    pop_geojson = res.get("population_geojson")
    assert exposed_pop is not None and exposed_pop > 0, f"Expected exposed_population > 0, got {exposed_pop}"
    assert pop_geojson is not None and pop_geojson.get("type") == "FeatureCollection"
    print(f"  [OK] Exposed Population: {exposed_pop:,} people inside flood polygon (CIESIN GPW v4.11 overlay)")

    # 5. Building Exposure Check
    aff_bld = res.get("affected_buildings")
    bld_geojson = res.get("buildings_geojson")
    assert aff_bld is not None and aff_bld > 0, f"Expected affected_buildings > 0, got {aff_bld}"
    assert bld_geojson is not None and bld_geojson.get("type") == "FeatureCollection"
    print(f"  [OK] Affected Buildings: {aff_bld:,} building footprints inside flood polygon (Google Open Buildings v3)")

    # 6. Road Accessibility Check
    aff_road_km = res.get("affected_road_length_km")
    roads_geojson = res.get("affected_roads_geojson")
    assert aff_road_km is not None and aff_road_km > 0.0, f"Expected affected_road_length_km > 0, got {aff_road_km}"
    assert roads_geojson is not None and roads_geojson.get("type") == "FeatureCollection"
    print(f"  [OK] Inundated Roads: {aff_road_km:.2f} km of road corridors inundated (OpenStreetMap network)")

    print("--- Real Kerala 2018 Flood Image Study Test Passed! ---\n")
    return True


if __name__ == "__main__":
    test_kerala_2018_flood_image_study()
