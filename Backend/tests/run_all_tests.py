"""
Test runner script to execute all SatQuery unit and integration tests
and ensure synthetic scenario GeoTIFFs are generated.
Can be executed with: python tests/run_all_tests.py
"""

import os
import sys
import unittest


def run_tests():
    print("=" * 65)
    print(" SatQuery Backend — Phase 1 Test Suite")
    print("=" * 65)

    # 0. Generate synthetic sample datasets if missing
    print("\n[0/5] Verifying Synthetic Sample Datasets...")
    try:
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        scripts_dir = os.path.join(root_dir, "scripts")
        data_dir = os.path.join(root_dir, "data")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        import create_synthetic_tifs
        create_synthetic_tifs.generate_all_sample_files(data_dir)
        print("  ✓ Synthetic GeoTIFFs ready in data/input/ and data/dem/")
    except Exception as exc:
        print(f"  Note: Synthetic dataset generator notice: {exc}")

    # 1. Test Health Endpoints
    print("\n[1/5] Testing Health Endpoints...")
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
        print("  ✓ Health endpoints: PASS")
    except Exception as exc:
        print(f"  ✗ Health endpoints failed: {exc}")
        return False

    # 2. Test Database Connectivity Check
    print("\n[2/5] Testing Database Check...")
    try:
        from tests.test_database import test_database_connectivity
        result = test_database_connectivity()
        print(f"  ✓ Database check handler executed successfully (connected={result.get('connected')})")
    except Exception as exc:
        print(f"  ✗ Database check failed: {exc}")
        return False

    # 3. Test Raster Validation and Otsu Differencing
    print("\n[3/5] Testing Raster Validation and Flood Detection...")
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
        print("  ✓ Raster, detection & VLM conversion tests: PASS (9 tests)")
    except Exception as exc:
        print(f"  ✗ Raster tests failed: {exc}")
        return False

    # 4. Test Geospatial Polygonization & Overlays
    print("\n[4/5] Testing Geospatial Polygonization, Impact & Evacuation...")
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
        print("  ✓ Geospatial tests: PASS (6 tests)")
    except Exception as exc:
        print(f"  ✗ Geospatial tests failed: {exc}")
        return False

    # 5. Test Full End-to-End Pipeline
    print("\n[5/6] Testing Full End-to-End Pipeline Integration...")
    try:
        from tests.test_pipeline import (
            test_full_synthetic_pipeline,
            test_pipeline_empty_flood_produces_valid_empty_result,
        )
        test_full_synthetic_pipeline()
        test_pipeline_empty_flood_produces_valid_empty_result()
        print("  ✓ Full pipeline integration: PASS (2 tests)")
    except Exception as exc:
        print(f"  ✗ Full pipeline integration failed: {exc}")
        return False

    # 6. Test AI Assistant Chat Orchestration
    print("\n[6/6] Testing AI Assistant Orchestration & Grounding...")
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
        print("  ✓ AI Assistant & VLM orchestration tests: PASS (9 tests)")
    except Exception as exc:
        print(f"  ✗ AI Assistant tests failed: {exc}")
        return False

    print("\n" + "=" * 65)
    print(" ALL TESTS PASSED SUCCESSFULLY! (24 test assertions verified)")
    print("=" * 65)
    return True


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
