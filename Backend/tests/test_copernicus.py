"""
Unit and integration tests for Copernicus Data Space Ecosystem (CDSE) Sentinel-1 acquisition.

Tests cover:
1. AOI conversion (bounding box, dict, list, GeoJSON) to OData WKT POLYGON.
2. OData product item parsing (orbit direction, relative orbit, polarizations).
3. Auth status reporting without credential leakage.
4. Token acquisition and error handling (missing credentials, invalid credentials).
5. Co-orbit SAR pair matching and recommendation ranking.
6. Measurement GeoTIFF extraction from Sentinel-1 .SAFE zip archive.
7. End-to-end acquire_and_analyze pipeline execution.
8. FastAPI /api/v1/copernicus endpoints (/status, /search, /pairs, /acquire).
"""

import os
import io
import json
import zipfile
import tempfile
import numpy as np
import pytest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.copernicus import AOIBounds, Sentinel1ProductSummary
from app.services.copernicus_client import (
    CopernicusDataSpaceClient,
    CopernicusCredentialsError,
)

client = TestClient(app)


# ---------------------------------------------------------------------------
# Test 1: AOI to WKT Polygon Conversion
# ---------------------------------------------------------------------------

def test_aoi_to_wkt_polygon():
    """Verify various AOI geometry formats convert to valid WGS84 WKT."""
    c = CopernicusDataSpaceClient()

    # 1. AOIBounds model
    bounds = AOIBounds(west=72.8, south=18.9, east=73.0, north=19.1)
    wkt1 = c.aoi_to_wkt_polygon(bounds)
    assert wkt1.startswith("POLYGON((")
    assert "72.800000 18.900000" in wkt1
    assert "73.000000 19.100000" in wkt1

    # 2. List [w, s, e, n]
    wkt2 = c.aoi_to_wkt_polygon([72.8, 18.9, 73.0, 19.1])
    assert wkt2 == wkt1

    # 3. Dict with west, south, east, north
    wkt3 = c.aoi_to_wkt_polygon({"west": 72.8, "south": 18.9, "east": 73.0, "north": 19.1})
    assert wkt3 == wkt1

    # 4. GeoJSON Polygon
    geojson_poly = {
        "type": "Polygon",
        "coordinates": [
            [[72.8, 18.9], [73.0, 18.9], [73.0, 19.1], [72.8, 19.1], [72.8, 18.9]]
        ],
    }
    wkt4 = c.aoi_to_wkt_polygon(geojson_poly)
    assert "72.800000 18.900000" in wkt4


# ---------------------------------------------------------------------------
# Test 2: OData Product Item Parsing
# ---------------------------------------------------------------------------

def test_parse_odata_product():
    """Verify raw CDSE OData JSON item is correctly mapped to Sentinel1ProductSummary."""
    raw_item = {
        "Id": "test-uuid-1234",
        "Name": "S1A_IW_GRDH_1SDV_20240723T010328_20240723T010353_054881_06AF21_15ED.SAFE",
        "ContentDate": {
            "Start": "2024-07-23T01:03:28.875Z",
            "End": "2024-07-23T01:03:53.000Z",
        },
        "ContentLength": 524288000,  # 500 MB
        "GeoFootprint": {
            "type": "Polygon",
            "coordinates": [[[72.0, 18.0], [74.0, 18.0], [74.0, 20.0], [72.0, 20.0], [72.0, 18.0]]],
        },
        "Attributes": [
            {"Name": "orbitDirection", "Value": "DESCENDING"},
            {"Name": "relativeOrbitNumber", "Value": 34},
            {"Name": "polarisationChannels", "Value": "VV&VH"},
            {"Name": "operationalMode", "Value": "IW"},
        ],
    }

    prod = CopernicusDataSpaceClient._parse_odata_product(raw_item)
    assert prod.id == "test-uuid-1234"
    assert "S1A_IW_GRDH" in prod.name
    assert prod.orbit_direction == "DESCENDING"
    assert prod.relative_orbit == 34
    assert "VV" in prod.polarizations
    assert "VH" in prod.polarizations
    assert prod.size_mb == 500.0
    assert "Quicklook" in prod.quicklook_url
    assert "zipper" in prod.download_url


# ---------------------------------------------------------------------------
# Test 3: Auth Status Unconfigured
# ---------------------------------------------------------------------------

def test_copernicus_auth_status_unconfigured():
    """Verify auth status reports unconfigured when no credentials exist, without errors."""
    client_instance = CopernicusDataSpaceClient(
        username=None, password=None, client_id=None, client_secret=None
    )
    status = client_instance.get_auth_status()
    assert status.configured is False
    assert status.authenticated is False
    assert "not configured" in status.message.lower()


# ---------------------------------------------------------------------------
# Test 4: Token Error When Missing Credentials
# ---------------------------------------------------------------------------

def test_copernicus_get_token_credentials_error():
    """Calling get_access_token without credentials raises CopernicusCredentialsError."""
    client_instance = CopernicusDataSpaceClient(
        username=None, password=None, client_id=None, client_secret=None
    )
    with pytest.raises(CopernicusCredentialsError) as exc_info:
        client_instance.get_access_token()
    assert "credentials are not configured" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# Test 5: Token Acquisition With Mock
# ---------------------------------------------------------------------------

@patch("app.services.copernicus_client.requests.post")
def test_copernicus_token_acquisition_success(mock_post):
    """Verify OAuth2 password grant returns and caches bearer token."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "access_token": "mock-token-xyz-12345",
        "expires_in": 600,
        "token_type": "Bearer",
    }
    mock_post.return_value = mock_resp

    client_instance = CopernicusDataSpaceClient(
        username="test_user@example.com",
        password="test_password_123",
    )
    token = client_instance.get_access_token()
    assert token == "mock-token-xyz-12345"

    # Second call should use cache without invoking requests.post again
    token2 = client_instance.get_access_token()
    assert token2 == token
    assert mock_post.call_count == 1


# ---------------------------------------------------------------------------
# Test 6: Co-Orbit Pair Matching Logic
# ---------------------------------------------------------------------------

def test_find_compatible_pairs_ranking():
    """
    Verify pair matching ranks pairs sharing identical relative orbit track and pass
    highest, as co-orbit pairs provide identical radar geometry.
    """
    client_instance = CopernicusDataSpaceClient()

    # Pre-flood products
    pre_prod_1 = Sentinel1ProductSummary(
        id="pre-1",
        name="S1A_IW_GRDH_Track34_Pre",
        content_date_start="2024-07-11T01:00:00Z",
        content_date_end="2024-07-11T01:01:00Z",
        orbit_direction="DESCENDING",
        relative_orbit=34,
        polarizations=["VV", "VH"],
    )
    pre_prod_2 = Sentinel1ProductSummary(
        id="pre-2",
        name="S1A_IW_GRDH_Track102_Pre",
        content_date_start="2024-07-10T01:00:00Z",
        content_date_end="2024-07-10T01:01:00Z",
        orbit_direction="ASCENDING",
        relative_orbit=102,
        polarizations=["VV", "VH"],
    )

    # Post-flood products
    post_prod_1 = Sentinel1ProductSummary(
        id="post-1",
        name="S1A_IW_GRDH_Track34_Post",
        content_date_start="2024-07-23T01:00:00Z",
        content_date_end="2024-07-23T01:01:00Z",
        orbit_direction="DESCENDING",
        relative_orbit=34,
        polarizations=["VV", "VH"],
    )

    with patch.object(client_instance, "search_sentinel1_grd") as mock_search:
        mock_search.side_effect = [
            {"total_found": 2, "products": [pre_prod_1, pre_prod_2], "notes": [], "error": None},
            {"total_found": 1, "products": [post_prod_1], "notes": [], "error": None},
        ]

        result = client_instance.find_compatible_pairs(
            aoi=[72.8, 18.9, 73.0, 19.1],
            pre_start_date="2024-07-01",
            pre_end_date="2024-07-15",
            post_start_date="2024-07-16",
            post_end_date="2024-07-31",
        )

    assert result["total_pairs"] == 2
    recommended = result["recommended_pair"]
    assert recommended is not None
    # Best pair must be the one with matching track 34 and DESCENDING pass
    assert recommended.pre_product.id == "pre-1"
    assert recommended.post_product.id == "post-1"
    assert recommended.relative_orbit == 34
    assert recommended.orbit_direction == "DESCENDING"
    assert recommended.compatible is True
    assert recommended.recommendation_score > 15.0


# ---------------------------------------------------------------------------
# Test 7: Measurement GeoTIFF Extraction from Zip
# ---------------------------------------------------------------------------

def test_extract_measurement_tiff_from_zip():
    """Verify extraction of target polarization measurement GeoTIFF from a Sentinel-1 .SAFE zip."""
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = os.path.join(tmpdir, "S1A_product.zip")
        output_tiff = os.path.join(tmpdir, "extracted_VV.tif")

        # Create a mock zip archive mimicking a Sentinel-1 .SAFE product
        fake_tiff_data = b"FAKE_TIFF_BINARY_DATA_VV"
        with zipfile.ZipFile(zip_path, "w") as z:
            z.writestr(
                "S1A_IW_GRDH_1SDV_20240723.SAFE/measurement/s1a-iw-grd-vv-20240723t010328-054881-06af21-001.tiff",
                fake_tiff_data,
            )
            z.writestr(
                "S1A_IW_GRDH_1SDV_20240723.SAFE/measurement/s1a-iw-grd-vh-20240723t010328-054881-06af21-002.tiff",
                b"FAKE_TIFF_BINARY_DATA_VH",
            )

        extracted = CopernicusDataSpaceClient._extract_measurement_tiff(zip_path, output_tiff, polarization="VV")
        assert os.path.isfile(extracted)
        with open(extracted, "rb") as f:
            content = f.read()
        assert content == fake_tiff_data


# ---------------------------------------------------------------------------
# Test 8: End-to-End acquire_and_analyze Execution
# ---------------------------------------------------------------------------

def test_acquire_and_analyze_pipeline():
    """
    Test end-to-end acquire_and_analyze flow:
    Mocks product download with synthetic Sentinel-1 GeoTIFFs and verifies
    downstream flood detection and pipeline impact scoring.
    """
    import rasterio
    from rasterio.transform import from_bounds
    from rasterio.crs import CRS

    with tempfile.TemporaryDirectory() as tmpdir:
        pre_file = os.path.join(tmpdir, "pre_s1.tif")
        post_file = os.path.join(tmpdir, "post_s1.tif")

        # Create realistic SAR rasters around Mumbai (WGS84 72.8-73.0, 18.9-19.1)
        transform = from_bounds(72.8, 18.9, 73.0, 19.1, 48, 48)
        pre_data = np.full((1, 48, 48), -11.0, dtype=np.float32)
        post_data = pre_data.copy()
        post_data[0, 16:32, 16:32] = -22.0  # Inundation specular drop

        for path, data in [(pre_file, pre_data), (post_file, post_data)]:
            with rasterio.open(
                path, "w",
                driver="GTiff", dtype=rasterio.float32, width=48, height=48, count=1,
                crs=CRS.from_epsg(4326), transform=transform, nodata=-9999.0
            ) as dst:
                dst.write(data)
                dst.set_band_description(1, "VV")
                dst.update_tags(SENSOR="SENTINEL-1", POLARISATION="VV")

        client_instance = CopernicusDataSpaceClient(cache_dir=tmpdir)

        # Mock download_product to return these rasters
        with patch.object(client_instance, "download_product") as mock_download:
            mock_download.side_effect = lambda pid, polarization="VV": pre_file if "pre" in pid else post_file

            result = client_instance.acquire_and_analyze(
                pre_product_id="prod-pre-uuid",
                post_product_id="prod-post-uuid",
                polarization="VV",
                run_pipeline=True,
                method="sar",
            )

        assert result["success"] is True
        assert result["detection"] is not None
        assert result["detection"].method_used == "sar+otsu"
        assert result["detection"].flooded_pixels > 0
        assert result["pipeline"] is not None
        assert result["pipeline"].polygons is not None
        assert result["pipeline"].polygons.polygon_count >= 1


# ---------------------------------------------------------------------------
# Test 9: FastAPI Copernicus Endpoints
# ---------------------------------------------------------------------------

def test_api_copernicus_status():
    """GET /api/v1/copernicus/status returns valid status object."""
    resp = client.get("/api/v1/copernicus/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "configured" in data
    assert "authenticated" in data
    assert "message" in data


@patch.object(CopernicusDataSpaceClient, "search_sentinel1_grd")
def test_api_copernicus_search(mock_search):
    """POST /api/v1/copernicus/search executes search query."""
    mock_search.return_value = {
        "total_found": 1,
        "products": [
            Sentinel1ProductSummary(
                id="pid-1",
                name="S1A_IW_GRDH_1SDV_20240723",
                content_date_start="2024-07-23T01:03:28Z",
                content_date_end="2024-07-23T01:03:53Z",
                orbit_direction="DESCENDING",
                relative_orbit=34,
                polarizations=["VV", "VH"],
                size_mb=450.0,
            )
        ],
        "notes": ["Search completed successfully."],
        "error": None,
    }

    req_body = {
        "bbox": {"west": 72.8, "south": 18.9, "east": 73.0, "north": 19.1},
        "start_date": "2024-07-01",
        "end_date": "2024-07-31",
        "orbit_direction": "ANY",
        "polarization": "VV",
        "limit": 5,
    }
    resp = client.post("/api/v1/copernicus/search", json=req_body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_found"] == 1
    assert len(data["products"]) == 1
    assert data["products"][0]["id"] == "pid-1"


@patch.object(CopernicusDataSpaceClient, "find_compatible_pairs")
def test_api_copernicus_pairs(mock_pairs):
    """POST /api/v1/copernicus/pairs finds compatible co-orbit pairs."""
    prod_a = Sentinel1ProductSummary(
        id="pre-1",
        name="S1A_Pre",
        content_date_start="2024-07-11T01:00:00Z",
        content_date_end="2024-07-11T01:01:00Z",
        orbit_direction="DESCENDING",
        relative_orbit=34,
        polarizations=["VV", "VH"],
    )
    prod_b = Sentinel1ProductSummary(
        id="post-1",
        name="S1A_Post",
        content_date_start="2024-07-23T01:00:00Z",
        content_date_end="2024-07-23T01:01:00Z",
        orbit_direction="DESCENDING",
        relative_orbit=34,
        polarizations=["VV", "VH"],
    )

    mock_pairs.return_value = {
        "total_pairs": 1,
        "recommended_pair": {
            "relative_orbit": 34,
            "orbit_direction": "DESCENDING",
            "pre_product": prod_a,
            "post_product": prod_b,
            "days_apart": 12.0,
            "compatible": True,
            "recommendation_score": 18.0,
            "notes": ["Co-orbit match"],
        },
        "pairs": [],
        "notes": [],
        "error": None,
    }

    req_body = {
        "bbox": {"west": 72.8, "south": 18.9, "east": 73.0, "north": 19.1},
        "pre_start_date": "2024-07-01",
        "pre_end_date": "2024-07-15",
        "post_start_date": "2024-07-16",
        "post_end_date": "2024-07-31",
    }
    resp = client.post("/api/v1/copernicus/pairs", json=req_body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_pairs"] == 1
    assert data["recommended_pair"]["relative_orbit"] == 34
