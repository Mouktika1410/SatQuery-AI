"""
Copernicus Data Space Ecosystem (CDSE) Sentinel-1 Acquisition Client.

Provides automated search, pairing, downloading, and pipeline ingestion
for Sentinel-1 IW GRD products using the official Copernicus Data Space OData & Auth APIs.

Credentials are kept strictly in backend configuration and never exposed to clients.
"""

import os
import re
import time
import zipfile
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

import requests

from app.core.config import settings
from app.schemas.copernicus import (
    AOIBounds,
    Sentinel1ProductSummary,
    MatchedSARPair,
    CopernicusAuthStatus,
)

logger = logging.getLogger(__name__)


class CopernicusCredentialsError(Exception):
    """Raised when Copernicus Data Space credentials are missing or invalid."""
    pass


class CopernicusAPIError(Exception):
    """Raised when Copernicus Data Space API calls fail."""
    pass


_UNSET: Any = object()


class CopernicusDataSpaceClient:
    """
    Client for interacting with the Copernicus Data Space Ecosystem (CDSE) APIs:
    - Keycloak OpenID Connect authentication (password & client_credentials grant)
    - OData v1 catalogue search for Sentinel-1 Level-1 GRD products
    - Pre/post flood acquisition pair matching with co-orbit preference
    - Direct streaming / cached download via zipper endpoint
    - Direct hand-off to SatQuery flood detection & analysis pipeline
    """

    def __init__(
        self,
        username: Any = _UNSET,
        password: Any = _UNSET,
        client_id: Any = _UNSET,
        client_secret: Any = _UNSET,
        cache_dir: Optional[str] = None,
    ) -> None:
        self.username = settings.COPERNICUS_USERNAME if username is _UNSET else username
        self.password = settings.COPERNICUS_PASSWORD if password is _UNSET else password
        self.client_id = settings.COPERNICUS_CLIENT_ID if client_id is _UNSET else client_id
        self.client_secret = settings.COPERNICUS_CLIENT_SECRET if client_secret is _UNSET else client_secret
        self.cache_dir = cache_dir or settings.copernicus_cache_dir

        self._cached_token: Optional[str] = None
        self._token_expires_at: float = 0.0

    # -----------------------------------------------------------------------
    # Authentication & Credential Management
    # -----------------------------------------------------------------------

    def get_auth_status(self) -> CopernicusAuthStatus:
        """
        Check whether Copernicus credentials are configured and valid.
        Returns a safe status summary without exposing sensitive credentials.
        """
        has_client_cred = bool(self.client_id and self.client_secret)
        has_pass_cred = bool(self.username and self.password)

        if not (has_client_cred or has_pass_cred):
            return CopernicusAuthStatus(
                configured=False,
                auth_type=None,
                authenticated=False,
                message=(
                    "Copernicus Data Space credentials not configured. "
                    "Set COPERNICUS_USERNAME and COPERNICUS_PASSWORD (or COPERNICUS_CLIENT_ID "
                    "and COPERNICUS_CLIENT_SECRET) in .env to enable satellite product downloads."
                ),
            )

        auth_type = "client_credentials" if has_client_cred else "password"
        try:
            token = self.get_access_token()
            authenticated = bool(token)
            message = "Copernicus Data Space authentication successful."
        except CopernicusCredentialsError as exc:
            authenticated = False
            message = f"Authentication failed: {exc}"
        except Exception as exc:
            authenticated = False
            message = f"Unexpected error during authentication: {exc}"

        return CopernicusAuthStatus(
            configured=True,
            auth_type=auth_type,
            authenticated=authenticated,
            message=message,
        )

    def get_access_token(self, force_refresh: bool = False) -> str:
        """
        Acquire a valid OAuth2 bearer token from the CDSE Keycloak service.
        Caches the token in-memory until near expiry.
        """
        now = time.time()
        if (
            not force_refresh
            and self._cached_token
            and now < (self._token_expires_at - 60)
        ):
            return self._cached_token

        has_client_cred = bool(self.client_id and self.client_secret)
        has_pass_cred = bool(self.username and self.password)

        if not (has_client_cred or has_pass_cred):
            raise CopernicusCredentialsError(
                "Copernicus Data Space credentials are not configured in environment. "
                "Please configure COPERNICUS_USERNAME and COPERNICUS_PASSWORD (or "
                "COPERNICUS_CLIENT_ID and COPERNICUS_CLIENT_SECRET) in your .env file."
            )

        token_url = settings.COPERNICUS_TOKEN_URL

        if has_client_cred:
            payload = {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            }
        else:
            payload = {
                "grant_type": "password",
                "client_id": "cdse-public",
                "username": self.username,
                "password": self.password,
            }

        try:
            resp = requests.post(token_url, data=payload, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                token = data.get("access_token")
                expires_in = float(data.get("expires_in", 600))
                if not token:
                    raise CopernicusCredentialsError("Token endpoint returned 200 but no access_token.")
                self._cached_token = token
                self._token_expires_at = now + expires_in
                return token
            elif resp.status_code in (400, 401):
                err_desc = ""
                try:
                    err_json = resp.json()
                    err_desc = err_json.get("error_description") or err_json.get("error") or ""
                except Exception:
                    err_desc = resp.text
                raise CopernicusCredentialsError(f"Authentication failed ({resp.status_code}): {err_desc}")
            else:
                raise CopernicusAPIError(f"Token endpoint returned HTTP {resp.status_code}: {resp.text}")
        except requests.RequestException as exc:
            raise CopernicusAPIError(f"Failed to connect to Copernicus identity endpoint: {exc}")

    # -----------------------------------------------------------------------
    # AOI & Geometry Formatting
    # -----------------------------------------------------------------------

    @staticmethod
    def aoi_to_wkt_polygon(aoi: Union[AOIBounds, Dict[str, Any], List[float], str]) -> str:
        """
        Convert various AOI inputs into a WGS84 WKT POLYGON string.
        Supported inputs:
        - AOIBounds instance
        - dict with 'west', 'south', 'east', 'north' or 'bbox'
        - list/tuple: [west, south, east, north]
        - GeoJSON geometry (Polygon or MultiPolygon)
        """
        if isinstance(aoi, AOIBounds):
            w, s, e, n = aoi.west, aoi.south, aoi.east, aoi.north
            return f"POLYGON(({w:.6f} {s:.6f}, {e:.6f} {s:.6f}, {e:.6f} {n:.6f}, {w:.6f} {n:.6f}, {w:.6f} {s:.6f}))"

        if isinstance(aoi, (list, tuple)) and len(aoi) == 4:
            w, s, e, n = float(aoi[0]), float(aoi[1]), float(aoi[2]), float(aoi[3])
            return f"POLYGON(({w:.6f} {s:.6f}, {e:.6f} {s:.6f}, {e:.6f} {n:.6f}, {w:.6f} {n:.6f}, {w:.6f} {s:.6f}))"

        if isinstance(aoi, dict):
            # Check for bounding box keys
            if all(k in aoi for k in ("west", "south", "east", "north")):
                w, s, e, n = float(aoi["west"]), float(aoi["south"]), float(aoi["east"]), float(aoi["north"])
                return f"POLYGON(({w:.6f} {s:.6f}, {e:.6f} {s:.6f}, {e:.6f} {n:.6f}, {w:.6f} {n:.6f}, {w:.6f} {s:.6f}))"
            if "bbox" in aoi and isinstance(aoi["bbox"], (list, tuple)) and len(aoi["bbox"]) == 4:
                return CopernicusDataSpaceClient.aoi_to_wkt_polygon(aoi["bbox"])

            # GeoJSON Polygon
            gtype = aoi.get("type", "").lower()
            if gtype == "polygon" and "coordinates" in aoi:
                ring = aoi["coordinates"][0]
                pts = ", ".join(f"{float(p[0]):.6f} {float(p[1]):.6f}" for p in ring)
                return f"POLYGON(({pts}))"
            elif gtype == "feature" and "geometry" in aoi:
                return CopernicusDataSpaceClient.aoi_to_wkt_polygon(aoi["geometry"])

        if isinstance(aoi, str):
            # Already WKT
            if aoi.strip().upper().startswith("POLYGON"):
                return aoi.strip()

        # Fallback default: Mumbai region
        return "POLYGON((72.700000 18.800000, 73.100000 18.800000, 73.100000 19.200000, 72.700000 19.200000, 72.700000 18.800000))"

    # -----------------------------------------------------------------------
    # Product Search
    # -----------------------------------------------------------------------

    def search_sentinel1_grd(
        self,
        aoi: Optional[Union[AOIBounds, Dict[str, Any], List[float], str]] = None,
        start_date: str = "2024-07-01",
        end_date: str = "2024-07-31",
        orbit_direction: Optional[str] = "ANY",
        polarization: Optional[str] = "VV",
        limit: int = 10,
    ) -> Dict[str, Any]:
        """
        Search for Sentinel-1 IW GRD products in Copernicus Data Space Ecosystem.

        Returns dict with:
        - total_found: int
        - products: List[Sentinel1ProductSummary]
        - notes: List[str]
        - error: Optional[str]
        """
        notes: List[str] = []

        # Format dates to ISO UTC strings
        def to_iso(dt_str: str, is_end: bool = False) -> str:
            dt_clean = dt_str.strip()
            if len(dt_clean) == 10:  # YYYY-MM-DD
                suffix = "T23:59:59.999Z" if is_end else "T00:00:00.000Z"
                return f"{dt_clean}{suffix}"
            if not dt_clean.endswith("Z"):
                return f"{dt_clean}Z"
            return dt_clean

        start_iso = to_iso(start_date, is_end=False)
        end_iso = to_iso(end_date, is_end=True)

        filters = [
            "Collection/Name eq 'SENTINEL-1'",
            "contains(Name, 'GRD')",
            "contains(Name, 'IW')",
            f"ContentDate/Start ge {start_iso}",
            f"ContentDate/Start le {end_iso}",
        ]

        if aoi:
            wkt = self.aoi_to_wkt_polygon(aoi)
            filters.append(f"OData.CSC.Intersects(area=geography'SRID=4326;{wkt}')")
            notes.append(f"Spatial AOI intersection filter applied: {wkt[:40]}...")

        orbit_dir_norm = (orbit_direction or "ANY").upper().strip()
        if orbit_dir_norm in ("ASCENDING", "DESCENDING"):
            filters.append(
                f"Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'orbitDirection' and "
                f"att/OData.CSC.StringAttribute/Value eq '{orbit_dir_norm}')"
            )
            notes.append(f"Orbit direction filter applied: {orbit_dir_norm}")

        filter_query = " and ".join(filters)

        # Build OData URL with literal $ parameters (CDSE rejects URL-encoded %24)
        base_url = settings.COPERNICUS_CATALOGUE_URL
        query_url = (
            f"{base_url}?$filter={filter_query}"
            f"&$orderby=ContentDate/Start desc"
            f"&$top={max(1, min(limit, 50))}"
            f"&$expand=Attributes"
        )

        try:
            resp = requests.get(query_url, timeout=30)
            if resp.status_code != 200:
                logger.error(f"CDSE catalogue query failed ({resp.status_code}): {resp.text}")
                return {
                    "total_found": 0,
                    "products": [],
                    "notes": notes,
                    "error": f"Copernicus catalogue query failed (HTTP {resp.status_code}): {resp.text[:200]}",
                }

            data = resp.json()
            raw_items = data.get("value", [])
            products: List[Sentinel1ProductSummary] = []

            for item in raw_items:
                parsed = self._parse_odata_product(item)
                # Filter by polarization if requested
                pol_req = (polarization or "ANY").upper().strip()
                if pol_req != "ANY" and parsed.polarizations:
                    if not any(pol_req in p.upper() for p in parsed.polarizations):
                        continue
                products.append(parsed)

            notes.append(f"Found {len(products)} matching Sentinel-1 IW GRD products.")
            return {
                "total_found": len(products),
                "products": products,
                "notes": notes,
                "error": None,
            }

        except requests.RequestException as exc:
            logger.exception("Failed to connect to Copernicus catalogue")
            return {
                "total_found": 0,
                "products": [],
                "notes": notes,
                "error": f"Failed to connect to Copernicus Data Space catalogue: {exc}",
            }

    # -----------------------------------------------------------------------
    # Co-Orbit SAR Pair Matching
    # -----------------------------------------------------------------------

    def find_compatible_pairs(
        self,
        aoi: Optional[Union[AOIBounds, Dict[str, Any], List[float], str]],
        pre_start_date: str,
        pre_end_date: str,
        post_start_date: str,
        post_end_date: str,
        orbit_direction: Optional[str] = "ANY",
        limit: int = 5,
    ) -> Dict[str, Any]:
        """
        Search for pre-flood and post-flood products, then automatically pair
        them based on matching radar geometry (same relative orbit track and pass).

        Matching the relative orbit is essential in SAR flood mapping because
        identical incidence angles and look directions guarantee that radar
        backscatter differences are caused by surface water, not terrain distortion.
        """
        notes: List[str] = []

        pre_res = self.search_sentinel1_grd(
            aoi=aoi,
            start_date=pre_start_date,
            end_date=pre_end_date,
            orbit_direction=orbit_direction,
            limit=30,
        )
        if pre_res.get("error"):
            return {"total_pairs": 0, "recommended_pair": None, "pairs": [], "notes": notes, "error": pre_res["error"]}

        post_res = self.search_sentinel1_grd(
            aoi=aoi,
            start_date=post_start_date,
            end_date=post_end_date,
            orbit_direction=orbit_direction,
            limit=30,
        )
        if post_res.get("error"):
            return {"total_pairs": 0, "recommended_pair": None, "pairs": [], "notes": notes, "error": post_res["error"]}

        pre_products: List[Sentinel1ProductSummary] = pre_res.get("products", [])
        post_products: List[Sentinel1ProductSummary] = post_res.get("products", [])

        if not pre_products:
            notes.append(f"No pre-flood Sentinel-1 products found between {pre_start_date} and {pre_end_date}.")
        if not post_products:
            notes.append(f"No post-flood Sentinel-1 products found between {post_start_date} and {post_end_date}.")

        matched_pairs: List[MatchedSARPair] = []

        for post_prod in post_products:
            for pre_prod in pre_products:
                if pre_prod.id == post_prod.id:
                    continue

                pair_notes = []
                # Check orbit geometry
                orbit_match = (
                    pre_prod.relative_orbit is not None
                    and post_prod.relative_orbit is not None
                    and pre_prod.relative_orbit == post_prod.relative_orbit
                )
                dir_match = (
                    pre_prod.orbit_direction is not None
                    and post_prod.orbit_direction is not None
                    and pre_prod.orbit_direction == post_prod.orbit_direction
                )

                # Compute temporal baseline
                try:
                    pre_dt = datetime.fromisoformat(pre_prod.content_date_start.replace("Z", "+00:00"))
                    post_dt = datetime.fromisoformat(post_prod.content_date_start.replace("Z", "+00:00"))
                    days_apart = round((post_dt - pre_dt).total_seconds() / 86400.0, 1)
                except Exception:
                    days_apart = 12.0

                if days_apart <= 0:
                    continue  # Pre-flood must precede post-flood

                # Calculate ranking score
                score = 0.0
                if orbit_match and dir_match:
                    score += 10.0
                    pair_notes.append(
                        f"Exact co-orbit geometry match: Track {pre_prod.relative_orbit} ({pre_prod.orbit_direction}). "
                        "Radar incidence angle and look direction are identical."
                    )
                elif dir_match:
                    score += 4.0
                    pair_notes.append(f"Partial match: Same orbit direction ({pre_prod.orbit_direction}) but different tracks.")
                else:
                    score += 1.0
                    pair_notes.append("Opposing pass geometry: Higher chance of topographic backscatter mismatch.")

                # Preferred temporal baseline: 6 to 24 days
                if 6.0 <= days_apart <= 24.0:
                    score += 5.0
                elif days_apart < 6.0:
                    score += 2.0
                else:
                    score += max(0.0, 5.0 - (days_apart - 24.0) * 0.1)

                # Polarization bonus: VV is optimal
                if "VV" in pre_prod.polarizations and "VV" in post_prod.polarizations:
                    score += 3.0

                matched_pairs.append(
                    MatchedSARPair(
                        relative_orbit=pre_prod.relative_orbit if orbit_match else None,
                        orbit_direction=pre_prod.orbit_direction if dir_match else None,
                        pre_product=pre_prod,
                        post_product=post_prod,
                        days_apart=days_apart,
                        compatible=orbit_match and dir_match,
                        recommendation_score=round(score, 2),
                        notes=pair_notes,
                    )
                )

        # Sort pairs: best recommendation score first
        matched_pairs.sort(key=lambda p: p.recommendation_score, reverse=True)
        recommended = matched_pairs[0] if matched_pairs else None

        notes.append(f"Evaluated and ranked {len(matched_pairs)} candidate pre/post acquisition pairs.")

        return {
            "total_pairs": len(matched_pairs),
            "recommended_pair": recommended,
            "pairs": matched_pairs[:limit],
            "notes": notes,
            "error": None,
        }

    # -----------------------------------------------------------------------
    # Product Download & Measurement GeoTIFF Extraction
    # -----------------------------------------------------------------------

    def download_product(
        self,
        product_id: str,
        polarization: str = "VV",
        destination_dir: Optional[str] = None,
    ) -> str:
        """
        Download a Sentinel-1 product from CDSE and extract the measurement GeoTIFF.

        Returns absolute path to the extracted georeferenced GeoTIFF.
        Uses in-memory stream extraction or zip extraction to prevent unnecessary storage bloat.
        """
        target_dir = destination_dir or self.cache_dir
        os.makedirs(target_dir, exist_ok=True)

        pol_norm = polarization.upper().strip()
        expected_tiff_name = f"{product_id}_{pol_norm}.tif"
        cached_path = os.path.join(target_dir, expected_tiff_name)

        # If already downloaded and valid (> 100 KB), return cached file immediately
        if os.path.isfile(cached_path) and os.path.getsize(cached_path) > 100 * 1024:
            logger.info(f"Using cached Sentinel-1 GeoTIFF: {cached_path}")
            return cached_path

        # Obtain valid authentication token
        token = self.get_access_token()
        headers = {"Authorization": f"Bearer {token}"}

        # Download product archive from zipper endpoint
        download_url = f"{settings.COPERNICUS_ZIPPER_URL}({product_id})/$value"
        zip_path = os.path.join(target_dir, f"{product_id}.zip")

        logger.info(f"Initiating download for product {product_id} from {download_url}...")
        try:
            resp = requests.get(download_url, headers=headers, stream=True, timeout=120, allow_redirects=True)
            if resp.status_code == 401:
                # Token might have expired, refresh once
                token = self.get_access_token(force_refresh=True)
                headers["Authorization"] = f"Bearer {token}"
                resp = requests.get(download_url, headers=headers, stream=True, timeout=120, allow_redirects=True)

            if resp.status_code not in (200, 206):
                raise CopernicusAPIError(
                    f"Product download failed (HTTP {resp.status_code}): {resp.text[:300]}"
                )

            # Stream download to temporary zip archive
            total_size = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            last_log_time = time.time()
            with open(zip_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=2 * 1024 * 1024):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        now = time.time()
                        if now - last_log_time >= 5.0:
                            if total_size > 0:
                                pct = (downloaded / total_size) * 100.0
                                logger.info(f"Downloading {product_id}: {downloaded / (1024*1024):.1f} / {total_size / (1024*1024):.1f} MB ({pct:.1f}%)")
                            else:
                                logger.info(f"Downloading {product_id}: {downloaded / (1024*1024):.1f} MB")
                            last_log_time = now

            logger.info(f"Product archive downloaded ({os.path.getsize(zip_path)} bytes). Extracting measurement GeoTIFF...")

            # Extract measurement GeoTIFF matching the requested polarization
            extracted_path = self._extract_measurement_tiff(zip_path, cached_path, pol_norm)

            # Cleanup zip archive to conserve disk space
            try:
                if os.path.isfile(zip_path):
                    os.remove(zip_path)
            except Exception:
                pass

            return extracted_path

        except requests.RequestException as exc:
            raise CopernicusAPIError(f"Network error during Copernicus download: {exc}")

    @staticmethod
    def _extract_measurement_tiff(zip_path: str, output_path: str, polarization: str = "VV") -> str:
        """
        Extract the target measurement TIFF from a Sentinel-1 .SAFE zip archive.
        Looks inside the measurement/ directory for the matching polarization.
        """
        pol_target = polarization.lower()
        with zipfile.ZipFile(zip_path, "r") as z:
            names = z.namelist()
            # Match measurement files, e.g.:
            # .../measurement/s1a-iw-grd-vv-20240723t010328-...tiff
            measurement_candidates = [
                n for n in names
                if "/measurement/" in n.lower()
                and (n.lower().endswith(".tiff") or n.lower().endswith(".tif"))
                and pol_target in os.path.basename(n).lower()
            ]

            if not measurement_candidates:
                # Fallback: any measurement tiff
                measurement_candidates = [
                    n for n in names
                    if "/measurement/" in n.lower()
                    and (n.lower().endswith(".tiff") or n.lower().endswith(".tif"))
                ]

            if not measurement_candidates:
                raise CopernicusAPIError(
                    f"No measurement GeoTIFF found inside Sentinel-1 archive: {zip_path}"
                )

            target_entry = measurement_candidates[0]
            logger.info(f"Extracting measurement asset '{target_entry}' to '{output_path}'")

            with z.open(target_entry) as src, open(output_path, "wb") as dst:
                while True:
                    chunk = src.read(1024 * 1024)
                    if not chunk:
                        break
                    dst.write(chunk)

        # Georeference: Raw Sentinel-1 GRD TIFFs contain GCPs rather than a standard affine transform.
        # Apply the GCP transform and CRS in-place so downstream GeoTIFF readers (rasterio, GIS)
        # can directly read bounds, CRS, and transform without requiring manual GCP warping.
        try:
            import rasterio
            from rasterio.transform import from_gcps
            with rasterio.open(output_path, "r+") as ds:
                if (ds.crs is None or ds.transform.is_identity) and ds.gcps and ds.gcps[0]:
                    ds.transform = from_gcps(ds.gcps[0])
                    ds.crs = ds.gcps[1] or "EPSG:4326"
                    logger.info(f"Applied GCP georeferencing to {output_path} (CRS: {ds.crs})")
        except Exception as exc:
            logger.warning(f"Could not apply GCP georeferencing to {output_path}: {exc}")

        return output_path

    # -----------------------------------------------------------------------
    # End-to-End Acquisition & Pipeline Execution
    # -----------------------------------------------------------------------

    def acquire_and_analyze(
        self,
        pre_product_id: str,
        post_product_id: str,
        polarization: str = "VV",
        run_pipeline: bool = True,
        download_only: bool = False,
        method: str = "sar",
        threshold: Optional[float] = None,
        simplify_tolerance: float = 0.0001,
        buffer_m: float = 100.0,
    ) -> Dict[str, Any]:
        """
        Download pre and post Sentinel-1 products from CDSE and run the
        existing SatQuery flood detection or full end-to-end pipeline.
        """
        notes: List[str] = []

        # 1. Download / retrieve pre-flood GeoTIFF
        try:
            pre_path = self.download_product(pre_product_id, polarization=polarization)
            notes.append(f"Pre-flood Sentinel-1 product acquired: {os.path.basename(pre_path)}")
        except Exception as exc:
            return {
                "success": False,
                "error": f"Failed to acquire pre-flood product ({pre_product_id}): {exc}",
                "notes": notes,
            }

        # 2. Download / retrieve post-flood GeoTIFF
        try:
            post_path = self.download_product(post_product_id, polarization=polarization)
            notes.append(f"Post-flood Sentinel-1 product acquired: {os.path.basename(post_path)}")
        except Exception as exc:
            return {
                "success": False,
                "error": f"Failed to acquire post-flood product ({post_product_id}): {exc}",
                "notes": notes,
            }

        if download_only:
            return {
                "success": True,
                "pre_file_path": pre_path,
                "post_file_path": post_path,
                "pre_product_name": os.path.basename(pre_path),
                "post_product_name": os.path.basename(post_path),
                "detection": None,
                "pipeline": None,
                "notes": notes + ["Measurement GeoTIFFs downloaded and extracted successfully (download-only mode)."],
                "error": None,
            }

        # 3. Execute Detection or Full Pipeline
        from app.services.flood_detection import FloodDetectionService

        det_options = {
            "method": method,
            "sar_polarization": polarization,
            "threshold": threshold,
            "morphology_iterations": 2,
        }

        if not run_pipeline:
            det_res = FloodDetectionService().detect(pre_path, post_path, det_options)
            return {
                "success": det_res.get("success", False),
                "pre_file_path": pre_path,
                "post_file_path": post_path,
                "detection": det_res,
                "pipeline": None,
                "notes": notes + det_res.get("notes", []),
                "error": det_res.get("error"),
            }

        # Full pipeline execution
        from app.services.image_validation import validate_image_pair
        from app.services.polygon_generation import PolygonGenerationService
        from app.services.exposure_analysis import ExposureAnalysisService
        from app.services.impact_scoring import ImpactScoringService
        from app.services.evacuation import EvacuationService
        from app.services.gis_repository import GISRepository
        from app.schemas.flood import (
            PipelineResult,
            UploadValidationResponse,
            ImageValidationResult,
            FloodDetectionResult,
            FloodPolygonResult,
            ImpactMetrics,
            AffectedVillage,
            PriorityScore,
            EvacuationCandidate,
            EvacuationCandidatesResult,
        )
        import uuid

        session_id = uuid.uuid4().hex
        pipeline = PipelineResult(session_id=session_id)

        # Step 1: Validate
        val_raw = validate_image_pair(pre_path, post_path)
        pipeline.validation = UploadValidationResponse(
            pre_flood=ImageValidationResult(
                filename=os.path.basename(pre_path),
                **{k: v for k, v in val_raw["pre_flood"].items() if k != "filename"}
            ),
            post_flood=ImageValidationResult(
                filename=os.path.basename(post_path),
                **{k: v for k, v in val_raw["post_flood"].items() if k != "filename"}
            ),
            compatible=val_raw["compatible"],
            compatibility_notes=val_raw["compatibility_notes"],
        )

        # Step 2: Detect
        det_svc = FloodDetectionService()
        det_res = det_svc.detect(pre_path, post_path, det_options)
        mask_array = det_res.pop("mask_array", None)

        import rasterio
        with rasterio.open(pre_path) as ds:
            transform_obj = ds.transform
            crs_wkt = ds.crs.to_wkt() if ds.crs else "EPSG:4326"

        pipeline.detection = FloodDetectionResult(
            **{k: v for k, v in det_res.items() if k in FloodDetectionResult.model_fields}
        )

        # Step 3: Polygonize
        flood_geojson = None
        if mask_array is not None:
            poly_svc = PolygonGenerationService()
            poly_res = poly_svc.generate(mask_array, transform_obj, crs_wkt, simplify_tolerance)
            pipeline.polygons = FloodPolygonResult(
                **{k: v for k, v in poly_res.items() if k in FloodPolygonResult.model_fields}
            )
            flood_geojson = poly_res.get("geojson")

        # Step 4: Impact Analysis
        if flood_geojson:
            gis_repo = GISRepository(settings.DATA_DIR)
            exposure = ExposureAnalysisService().calculate_exposure(flood_geojson, session_id, gis_repo)
            affected_villages = [AffectedVillage(**v) for v in exposure.get("affected_villages", [])]
            pipeline.impact = ImpactMetrics(
                affected_villages=affected_villages,
                affected_population=exposure.get("affected_population"),
                affected_buildings=exposure.get("affected_buildings"),
                affected_road_length_km=exposure.get("affected_road_length_km"),
                affected_villages_geojson=exposure.get("affected_villages_geojson"),
                affected_roads_geojson=exposure.get("affected_roads_geojson"),
                data_availability=exposure.get("data_availability", {}),
                disclaimer=exposure.get("disclaimer", ""),
            )

            raw_priority = ImpactScoringService().compute_priority_scores(exposure)
            pipeline.priority_scores = [PriorityScore(**p) for p in raw_priority]

            # Step 5: Evacuation Candidates
            evac_raw = EvacuationService().find_candidates(flood_geojson, gis_repo, buffer_m)
            candidates = [EvacuationCandidate(**c) for c in evac_raw.get("candidates", [])]
            pipeline.evacuation = EvacuationCandidatesResult(
                candidates=candidates,
                total_found=evac_raw.get("total_found", 0),
                filtered_reason=evac_raw.get("filtered_reason", ""),
                disclaimer=evac_raw.get("disclaimer", ""),
            )

        notes.extend(pipeline.warnings)
        return {
            "success": True,
            "pre_file_path": pre_path,
            "post_file_path": post_path,
            "detection": pipeline.detection,
            "pipeline": pipeline,
            "notes": notes,
            "error": None,
        }

    # -----------------------------------------------------------------------
    # Helper: Parse OData Product Item
    # -----------------------------------------------------------------------

    @staticmethod
    def _parse_odata_product(item: Dict[str, Any]) -> Sentinel1ProductSummary:
        """Parse raw OData JSON item into a Sentinel1ProductSummary model."""
        pid = item.get("Id", "")
        name = item.get("Name", "")
        content_date = item.get("ContentDate", {})
        start_date = content_date.get("Start", "")
        end_date = content_date.get("End", "")
        size_bytes = item.get("ContentLength")
        size_mb = round(size_bytes / (1024 * 1024), 2) if size_bytes else None
        footprint = item.get("GeoFootprint")

        # Extract attributes from expanded Attributes array
        attributes = item.get("Attributes", [])
        attr_map = {a.get("Name"): a.get("Value") for a in attributes if isinstance(a, dict)}

        orbit_dir = attr_map.get("orbitDirection")
        rel_orbit = attr_map.get("relativeOrbitNumber")
        if rel_orbit is not None:
            try:
                rel_orbit = int(rel_orbit)
            except Exception:
                rel_orbit = None

        # Extract polarizations from polarisationChannels or product title
        pols = []
        pol_raw = attr_map.get("polarisationChannels") or ""
        if "VV" in pol_raw:
            pols.append("VV")
        if "VH" in pol_raw:
            pols.append("VH")
        if "HH" in pol_raw:
            pols.append("HH")
        if "HV" in pol_raw:
            pols.append("HV")

        if not pols:
            # Fallback regex on Name (e.g. S1A_IW_GRDH_1SDV_... -> DV = VV+VH, SH = HH, SV = VV)
            if "_1SDV_" in name or "_2SDV_" in name:
                pols = ["VV", "VH"]
            elif "_1SSV_" in name or "_2SSV_" in name:
                pols = ["VV"]
            elif "_1SDH_" in name or "_2SDH_" in name:
                pols = ["HH", "HV"]
            elif "_1SSH_" in name or "_2SSH_" in name:
                pols = ["HH"]
            else:
                pols = ["VV"]

        quicklook_url = f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products({pid})/Products('Quicklook')/$value"
        download_url = f"https://zipper.dataspace.copernicus.eu/odata/v1/Products({pid})/$value"

        return Sentinel1ProductSummary(
            id=pid,
            name=name,
            content_date_start=start_date,
            content_date_end=end_date,
            orbit_direction=orbit_dir,
            relative_orbit=rel_orbit,
            polarizations=pols,
            size_mb=size_mb,
            footprint=footprint,
            quicklook_url=quicklook_url,
            download_url=download_url,
        )
