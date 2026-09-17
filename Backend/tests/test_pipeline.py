"""
Integration test: full pipeline validate → detect → polygonize → impact → priority → evacuation.
Requires rasterio and geopandas.
"""

import os
import tempfile
import numpy as np
import pytest

rasterio = pytest.importorskip("rasterio", reason="rasterio not installed")
gpd = pytest.importorskip("geopandas", reason="geopandas not installed")

import rasterio
from rasterio.transform import from_bounds
from rasterio.crs import CRS
from shapely.geometry import Point, Polygon


def _create_geotiff(path, data, width=64, height=64, bands=1):
    transform = from_bounds(72.8, 18.9, 73.0, 19.1, width, height)
    profile = {
        "driver": "GTiff",
        "dtype": rasterio.float32,
        "width": width,
        "height": height,
        "count": bands,
        "crs": CRS.from_epsg(4326),
        "transform": transform,
        "nodata": -9999.0,
    }
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(data)
    return path


def test_full_synthetic_pipeline():
    """
    End-to-end integration test:
    Validate → Detect → Polygonize → Impact → Priority → Evacuation → AI Assistant.
    """
    from app.services.image_validation import validate_image_pair
    from app.services.flood_detection import FloodDetectionService
    from app.services.polygon_generation import PolygonGenerationService
    from app.services.exposure_analysis import ExposureAnalysisService
    from app.services.impact_scoring import ImpactScoringService
    from app.services.evacuation import EvacuationService
    from app.services.orchestration import AgentOrchestrationService
    from app.services.gis_repository import GISRepository

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create pre-image: uniform dark baseline
        pre_data = np.full((1, 64, 64), 10.0, dtype=np.float32)
        pre_path = os.path.join(tmpdir, "pre.tif")
        _create_geotiff(pre_path, pre_data)

        # Create post-image: single broad organic flood region
        np.random.seed(42)
        grid_y, grid_x = np.ogrid[:64, :64]
        norm_x = grid_x / 63.0
        norm_y = grid_y / 63.0
        r_dist = np.sqrt((norm_x - 0.50)**2 + (norm_y - 0.48)**2)

        r1 = np.random.randn(64, 64)
        r2 = np.random.randn(64, 64)
        try:
            from scipy import ndimage as ndi
            g1 = ndi.gaussian_filter(r1, sigma=7.0)
            g2 = ndi.gaussian_filter(r2, sigma=2.5)
        except ImportError:
            g1, g2 = r1, r2

        noise = g1 * 0.65 + g2 * 0.35
        noise = (noise - noise.min()) / (noise.max() - noise.min() + 1e-10)
        organic_mask = r_dist < (0.22 + 0.22 * noise)

        post_data = np.full((1, 64, 64), 10.0, dtype=np.float32)
        post_data[0, organic_mask] = 200.0
        post_path = os.path.join(tmpdir, "post.tif")
        _create_geotiff(post_path, post_data)

        # Step 1: Validate
        val = validate_image_pair(pre_path, post_path)
        assert val["pre_flood"]["valid"] is True, "Pre-image validation failed"
        assert val["post_flood"]["valid"] is True, "Post-image validation failed"
        assert val["compatible"] is True, "Images should be compatible"

        # Step 2: Detect
        det = FloodDetectionService().detect(
            pre_path, post_path,
            options={"method": "differencing", "morphology_iterations": 1}
        )
        assert det["success"] is True, f"Detection failed: {det.get('error')}"
        assert det["flooded_pixels"] > 0
        mask_array = det.pop("mask_array")

        # Step 3: Polygonize
        with rasterio.open(pre_path) as ds:
            transform = ds.transform
            crs_wkt = ds.crs.to_wkt()

        poly = PolygonGenerationService().generate(
            mask_array=mask_array,
            transform=transform,
            crs_wkt=crs_wkt,
            simplify_tolerance=0.00001,
        )
        assert poly["success"] is True, f"Polygonization failed: {poly.get('error')}"
        assert poly["polygon_count"] > 0
        assert poly["geojson"] is not None
        assert poly["total_area_km2"] > 0.0

        features = poly["geojson"].get("features", [])
        assert len(features) > 0, "GeoJSON should have at least one polygon feature"

        # Step 4: Impact & Exposure Analysis (using mock layers)
        villages_gdf = gpd.GeoDataFrame(
            [
                {"name": "Village North", "geometry": Polygon([(72.85, 18.95), (72.95, 18.95), (72.95, 19.05), (72.85, 19.05), (72.85, 18.95)])},
                {"name": "Village South", "geometry": Polygon([(72.80, 18.80), (72.85, 18.80), (72.85, 18.85), (72.80, 18.85), (72.80, 18.80)])},
            ],
            crs="EPSG:4326"
        )
        pois_gdf = gpd.GeoDataFrame(
            [
                {"name": "Flooded Community Center", "type": "community_hall", "geometry": Point(72.90, 19.00)},
                {"name": "High Ground School", "type": "school", "geometry": Point(73.10, 19.20)},
            ],
            crs="EPSG:4326"
        )

        class MockGISRepo:
            def load_layer(self, layer_type):
                if layer_type == "villages":
                    return villages_gdf
                if layer_type == "pois":
                    return pois_gdf
                return None
            def get_dem_path(self):
                return None
            def sample_elevation(self, lat, lon):
                return 45.0

        mock_repo = MockGISRepo()
        exposure_svc = ExposureAnalysisService()
        exposure = exposure_svc.calculate_exposure(poly["geojson"], "test_session", mock_repo)

        assert exposure["data_availability"]["villages"] is True
        assert len(exposure["affected_villages"]) > 0

        # Step 5: Priority Scoring
        impact_svc = ImpactScoringService()
        scores = impact_svc.compute_priority_scores(exposure)
        assert len(scores) > 0
        assert scores[0]["rank"] == 1
        assert 0.0 <= scores[0]["priority_score"] <= 1.0

        # Step 6: Evacuation Candidates Analysis
        evac_svc = EvacuationService()
        evac_result = evac_svc.find_candidates(poly["geojson"], mock_repo, buffer_m=50.0)
        assert evac_result["total_found"] > 0
        candidates = evac_result["candidates"]
        cand_names = [c["name"] for c in candidates]
        assert "High Ground School" in cand_names
        assert "Flooded Community Center" not in cand_names

        # Step 7: AI Assistant Grounded Query
        pipeline_data = {
            "detection": det,
            "polygons": poly,
            "impact": exposure,
            "priority_scores": scores,
            "evacuation": evac_result,
        }
        assistant = AgentOrchestrationService()
        chat_resp = assistant.answer_query("What is the flooded area?", pipeline_data)
        assert chat_resp["answer"] is not None
        assert "flooded area" in chat_resp["answer"].lower() or "km²" in chat_resp["answer"]
        assert len(chat_resp["data_used"]) > 0


def test_pipeline_empty_flood_produces_valid_empty_result():
    """Pipeline on two identical images should return 0 flooded pixels."""
    from app.services.flood_detection import FloodDetectionService
    from app.services.polygon_generation import PolygonGenerationService

    with tempfile.TemporaryDirectory() as tmpdir:
        identical_data = np.full((1, 32, 32), 50.0, dtype=np.float32)
        pre_path = os.path.join(tmpdir, "pre.tif")
        post_path = os.path.join(tmpdir, "post.tif")
        _create_geotiff(pre_path, identical_data, width=32, height=32)
        _create_geotiff(post_path, identical_data, width=32, height=32)

        det = FloodDetectionService().detect(
            pre_path, post_path,
            options={"method": "differencing", "morphology_iterations": 0}
        )
        assert det["success"] is True
        # Identical images → zero flood
        assert det["flooded_pixels"] == 0 or det["flood_percentage"] < 1.0
