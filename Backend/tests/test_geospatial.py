"""
Unit tests for geospatial polygon generation, GIS overlay, impact scoring,
and evacuation candidate filtering.

All tests use synthetic in-memory data — no external datasets required.
"""

import os
import tempfile
import numpy as np
import pytest

gpd = pytest.importorskip("geopandas", reason="geopandas not installed")
rasterio = pytest.importorskip("rasterio", reason="rasterio not installed")

import geopandas as gpd
from shapely.geometry import Point, Polygon, box
from rasterio.transform import from_bounds
from rasterio.crs import CRS


# ---------------------------------------------------------------------------
# Helper: create a synthetic GeoTIFF mask (reuse from test_raster)
# ---------------------------------------------------------------------------

def _make_mask_geotiff(path, width=64, height=64):
    """Create a binary mask with a single broad organic flooded region."""
    import rasterio
    np.random.seed(42)
    grid_y, grid_x = np.ogrid[:height, :width]
    norm_x = grid_x / float(width - 1)
    norm_y = grid_y / float(height - 1)
    r_dist = np.sqrt((norm_x - 0.50)**2 + (norm_y - 0.48)**2)

    r1 = np.random.randn(height, width)
    r2 = np.random.randn(height, width)
    try:
        from scipy import ndimage as ndi
        g1 = ndi.gaussian_filter(r1, sigma=7.0)
        g2 = ndi.gaussian_filter(r2, sigma=2.5)
    except ImportError:
        g1, g2 = r1, r2

    noise = g1 * 0.65 + g2 * 0.35
    noise = (noise - noise.min()) / (noise.max() - noise.min() + 1e-10)
    mask = np.where(r_dist < (0.22 + 0.22 * noise), 1, 0).astype(np.uint8)

    transform = from_bounds(72.8, 18.9, 73.0, 19.1, width, height)
    profile = {
        "driver": "GTiff",
        "dtype": rasterio.uint8,
        "width": width,
        "height": height,
        "count": 1,
        "crs": CRS.from_epsg(4326),
        "transform": transform,
        "nodata": 255,
    }
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(mask, 1)
    return path, mask, transform


# ---------------------------------------------------------------------------
# Test 1 — Polygon generation from synthetic mask
# ---------------------------------------------------------------------------

def test_polygon_generation_from_mask():
    """PolygonGenerationService should produce at least one polygon from a mask with a flooded block."""
    from app.services.polygon_generation import PolygonGenerationService

    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "mask.tif")
        path, mask, transform = _make_mask_geotiff(path)

        result = PolygonGenerationService().generate(
            mask_array=mask,
            transform=transform,
            crs_wkt="EPSG:4326",
            simplify_tolerance=0.00001,
        )

    assert result["success"] is True, f"Failed: {result.get('error')}"
    assert result["polygon_count"] > 0, "Expected at least 1 polygon"
    assert result["geojson"] is not None
    assert result["geojson"]["type"] == "FeatureCollection"
    assert len(result["geojson"]["features"]) > 0
    assert result["total_area_km2"] > 0.0


# ---------------------------------------------------------------------------
# Test 2 — Empty mask produces empty GeoJSON, not an error
# ---------------------------------------------------------------------------

def test_polygon_generation_empty_mask():
    """An all-zero mask should return success=True with 0 polygons."""
    from app.services.polygon_generation import PolygonGenerationService

    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "empty.tif")
        path, _, transform = _make_mask_geotiff(path)
        empty_mask = np.zeros((64, 64), dtype=np.uint8)

        result = PolygonGenerationService().generate(
            mask_array=empty_mask,
            transform=transform,
            crs_wkt="EPSG:4326",
            simplify_tolerance=0.00001,
        )

    assert result["success"] is True
    assert result["polygon_count"] == 0
    assert result["total_area_km2"] == 0.0


# ---------------------------------------------------------------------------
# Test 3 — Impact scoring ranks higher-population village first
# ---------------------------------------------------------------------------

def test_impact_scoring_ranks_by_population():
    """Village with higher population exposure should receive rank 1."""
    from app.services.impact_scoring import ImpactScoringService

    exposure = {
        "affected_villages": [
            {"name": "Small Village", "area_flooded_km2": 0.5, "population_affected": 200},
            {"name": "Large Village", "area_flooded_km2": 0.5, "population_affected": 5000},
        ],
        "affected_population": 5200,
        "affected_buildings": None,
        "affected_road_length_km": None,
        "data_availability": {
            "villages": True,
            "population": True,
            "buildings": False,
            "roads": False,
        },
    }

    scores = ImpactScoringService().compute_priority_scores(exposure)

    assert len(scores) == 2
    # Large Village should be rank 1
    rank1 = next((s for s in scores if s["rank"] == 1), None)
    assert rank1 is not None
    assert rank1["village_name"] == "Large Village"
    # Scores should be in [0, 1]
    for s in scores:
        assert 0.0 <= s["priority_score"] <= 1.0


# ---------------------------------------------------------------------------
# Test 4 — Evacuation filter excludes POIs inside the flood
# ---------------------------------------------------------------------------

def test_evacuation_filter_excludes_flooded_pois():
    """POIs inside the flood boundary should be excluded from candidates."""
    from app.services.evacuation import EvacuationService

    # Flood polygon: a 0.1° box
    flood_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [[72.85, 18.95], [72.95, 18.95], [72.95, 19.05], [72.85, 19.05], [72.85, 18.95]]
                    ],
                },
                "properties": {},
            }
        ],
    }

    # Two POIs: one inside flood, one outside
    inside_poi = gpd.GeoDataFrame(
        [{"name": "Flooded School", "type": "school", "geometry": Point(72.9, 19.0)}],
        crs="EPSG:4326",
    )
    outside_poi = gpd.GeoDataFrame(
        [{"name": "Safe Hall", "type": "community_hall", "geometry": Point(73.1, 19.2)}],
        crs="EPSG:4326",
    )
    pois_gdf = gpd.GeoDataFrame(
        [
            {"name": "Flooded School", "type": "school", "geometry": Point(72.9, 19.0)},
            {"name": "Safe Hall", "type": "community_hall", "geometry": Point(73.1, 19.2)},
        ],
        crs="EPSG:4326",
    )

    # Mock GISRepository
    class MockRepo:
        def load_layer(self, layer_type):
            if layer_type == "pois":
                return pois_gdf
            return None

    svc = EvacuationService()
    result = svc.find_candidates(flood_geojson, MockRepo(), buffer_m=50.0)

    candidates = result["candidates"]
    names = [c["name"] for c in candidates]

    assert "Safe Hall" in names, "Outside POI should be a candidate"
    assert "Flooded School" not in names, "Inside POI should be excluded"


# ---------------------------------------------------------------------------
# Test 5 — GIS repository available_layers returns all False for empty dir
# ---------------------------------------------------------------------------

def test_gis_repository_empty_dir():
    """GISRepository should report all layers as unavailable for an empty data directory."""
    from app.services.gis_repository import GISRepository

    with tempfile.TemporaryDirectory() as tmpdir:
        repo = GISRepository(tmpdir)
        available = repo.available_layers()

    assert isinstance(available, dict)
    assert len(available) > 0
    for key, val in available.items():
        assert val is False, f"Expected {key} to be unavailable in empty dir, got {val}"


# ---------------------------------------------------------------------------
# Test 6 — GIS overlay returns None for non-overlapping geometries
# ---------------------------------------------------------------------------

def test_gis_overlay_no_intersection():
    """Overlay should return None when flood and data layer do not intersect."""
    from app.services.gis_overlay import GISOverlayService

    # Flood polygon in India
    flood_gdf = gpd.GeoDataFrame(
        [{"geometry": box(72.85, 18.95, 72.95, 19.05)}], crs="EPSG:4326"
    )
    # Data in USA — no overlap
    data_gdf = gpd.GeoDataFrame(
        [{"name": "Village A", "geometry": box(-100.0, 40.0, -99.0, 41.0)}], crs="EPSG:4326"
    )

    svc = GISOverlayService()
    result = svc.overlay_flood_with_layers(flood_gdf, "villages", data_gdf)

    assert result is None or (hasattr(result, "__len__") and len(result) == 0)
