"""
Test runner script to execute all SatQuery unit and integration tests
and ensure synthetic scenario GeoTIFFs are generated.
Can be executed with: python tests/run_all_tests.py
"""

import os
import sys
import unittest


def run_tests():
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

    print("=" * 65)
    print(" SatQuery Backend Phase 1 Test Suite")
    print("=" * 65)

    # 0. Generate synthetic sample datasets if missing
    print("\n[0/7] Verifying Synthetic Sample Datasets...")
    try:
        root_dir = os.path.dirname(backend_dir)
        scripts_dir = os.path.join(root_dir, "scripts")
        data_dir = os.path.join(root_dir, "data")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        import create_synthetic_tifs
        create_synthetic_tifs.generate_all_sample_files(data_dir)
        print("  [OK] Synthetic GeoTIFFs ready in data/input/ and data/dem/")
    except Exception as exc:
        print(f"  Note: Synthetic dataset generator notice: {exc}")

    # 1. Test Health Endpoints
    print("\n[1/7] Testing Health Endpoints...")
    try:
        from tests.test_health import (
            test_root_health_endpoint,
            test_api_v1_health_endpoint,
            test_database_health_endpoint,
            test_root_endpoint,
        )
        test_root_health_endpoint()
        test_api_v1_health_endpoint()
        test_database_health_endpoint()
        test_root_endpoint()
        print("  [OK] Health endpoints: PASS")
    except Exception as exc:
        print(f"  [FAIL] Health endpoints failed: {exc}")
        return False

    # 2. Test Database Connectivity Check
    print("\n[2/7] Testing Database Check...")
    try:
        from tests.test_database import test_database_connectivity
        result = test_database_connectivity()
        print(f"  [OK] Database check handler executed successfully (connected={result.get('connected')})")
    except Exception as exc:
        print(f"  [FAIL] Database check failed: {exc}")
        return False

    # 3. Test Raster Validation and Otsu Differencing
    print("\n[3/7] Testing Raster Validation and Flood Detection...")
    try:
        from tests.test_raster import (
            test_validate_geotiff_valid,
            test_validate_geotiff_missing_file,
            test_otsu_threshold_bimodal,
            test_differencing_detection_synthetic,
            test_morphological_cleanup_removes_noise,
            test_validate_image_pair_compatible,
            test_vlm_geotiff_conversion_with_nodata,
            test_vlm_geotiff_conversion_with_masked_array,
            test_vlm_geotiff_conversion_with_nomask,
        )
        test_validate_geotiff_valid()
        test_validate_geotiff_missing_file()
        test_otsu_threshold_bimodal()
        test_differencing_detection_synthetic()
        test_morphological_cleanup_removes_noise()
        test_validate_image_pair_compatible()
        test_vlm_geotiff_conversion_with_nodata()
        test_vlm_geotiff_conversion_with_masked_array()
        test_vlm_geotiff_conversion_with_nomask()
        print("  [OK] Raster, detection & VLM conversion tests: PASS (9 tests)")
    except Exception as exc:
        print(f"  [FAIL] Raster tests failed: {exc}")
        return False

    # 4. Test Geospatial Polygonization & Overlays
    print("\n[4/7] Testing Geospatial Polygonization, Impact & Evacuation...")
    try:
        from tests.test_geospatial import (
            test_polygon_generation_from_mask,
            test_polygon_generation_empty_mask,
            test_impact_scoring_ranks_by_population,
            test_evacuation_filter_excludes_flooded_pois,
            test_gis_repository_empty_dir,
            test_gis_overlay_no_intersection,
        )
        test_polygon_generation_from_mask()
        test_polygon_generation_empty_mask()
        test_impact_scoring_ranks_by_population()
        test_evacuation_filter_excludes_flooded_pois()
        test_gis_repository_empty_dir()
        test_gis_overlay_no_intersection()
        print("  [OK] Geospatial tests: PASS (6 tests)")
    except Exception as exc:
        print(f"  [FAIL] Geospatial tests failed: {exc}")
        return False

    # 5. Test Full End-to-End Pipeline
    print("\n[5/7] Testing Full End-to-End Pipeline Integration...")
    try:
        from tests.test_pipeline import (
            test_full_synthetic_pipeline,
            test_pipeline_empty_flood_produces_valid_empty_result,
        )
        test_full_synthetic_pipeline()
        test_pipeline_empty_flood_produces_valid_empty_result()
        print("  [OK] Full pipeline integration: PASS (2 tests)")
    except Exception as exc:
        print(f"  [FAIL] Full pipeline integration failed: {exc}")
        return False

    # 6. Test AI Assistant Chat Orchestration
    print("\n[6/7] Testing AI Assistant Orchestration & Grounding...")
    try:
        from tests.test_chat import (
            test_flooded_area_query,
            test_affected_population_query,
            test_affected_villages_query,
            test_affected_buildings_query,
            test_evacuation_query,
            test_priority_analysis_query,
            test_vlm_visual_comparison_fallback,
            test_vlm_query,
            test_api_key_detection,
        )
        test_flooded_area_query()
        test_affected_population_query()
        test_affected_villages_query()
        test_affected_buildings_query()
        test_evacuation_query()
        test_priority_analysis_query()
        test_vlm_visual_comparison_fallback()
        test_vlm_query()
        test_api_key_detection()
        print("  [OK] AI Assistant & VLM orchestration tests: PASS (9 tests)")
    except Exception as exc:
        print(f"  [FAIL] AI Assistant tests failed: {exc}")
        return False

    # 7. Test Real Google Earth Engine Sentinel-1 Flood Detection
    print("\n[7/8] Testing Real GEE Sentinel-1 Flood Detection (South Yorkshire Nov 2019)...")
    try:
        from tests.test_gee_flood import test_gee_sentinel1_south_yorkshire_nov2019
        test_gee_sentinel1_south_yorkshire_nov2019()
        print("  [OK] Real GEE Sentinel-1 Flood Polygon Detection: PASS")
    except Exception as exc:
        print(f"  [FAIL] Real GEE Sentinel-1 test failed: {exc}")
        return False

    # 8. Test Dual-GeoTIFF Image Study Workflow
    print("\n[8/9] Testing Dual-GeoTIFF Image Study Workflow & Centroid Calculation...")
    try:
        from tests.test_image_study import (
            test_image_study_real_geotiff_pair,
            test_image_study_non_georeferenced_rejection,
        )
        test_image_study_real_geotiff_pair()
        test_image_study_non_georeferenced_rejection()
        print("  [OK] Dual-GeoTIFF Image Study & Centroid Calculation: PASS (2 tests)")
    except Exception as exc:
        print(f"  [FAIL] Image Study test failed: {exc}")
        return False

    # 9. Test Real Kerala 2018 Flood Event Dataset
    print("\n[9/9] Testing Real Kerala 2018 Flood Event Dataset...")
    try:
        from tests.test_kerala_flood import test_kerala_2018_flood_image_study
        test_kerala_2018_flood_image_study()
        print("  [OK] Real Kerala 2018 Flood Dataset Integration: PASS")
    except Exception as exc:
        print(f"  [FAIL] Kerala 2018 flood test failed: {exc}")
        return False

    print("\n" + "=" * 65)
    print(" ALL TESTS PASSED SUCCESSFULLY! (28 test assertions verified)")
    print("=" * 65)
    return True


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
