"""
Google Earth Engine (GEE) Sentinel-1 SAR Flood Detection Service.

Implements real satellite SAR change detection using Sentinel-1 GRD imagery
(COPERNICUS/S1_GRD) from Google Earth Engine.

Reference:
GEE Community Tutorial: Detecting Changes in Sentinel-1 Imagery
https://developers.google.com/earth-engine/tutorials/community/detecting-changes-in-sentinel-1-imagery-pt-3
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Default project and historical event coordinates (South Yorkshire / River Don, Nov 2019)
DEFAULT_GEE_PROJECT = "satquery-flood-detection"
SOUTH_YORKSHIRE_BBOX = [-1.25, 53.50, -0.90, 53.65]  # [min_lon, min_lat, max_lon, max_lat]
DEFAULT_PRE_START = "2019-10-15"
DEFAULT_PRE_END = "2019-11-04"
DEFAULT_POST_START = "2019-11-05"
DEFAULT_POST_END = "2019-11-15"


class GEEFloodDetectionService:
    """
    Real Google Earth Engine Sentinel-1 SAR change detection service.
    """

    def __init__(self, project_id: str = DEFAULT_GEE_PROJECT) -> None:
        self.project_id = project_id
        self._ee_initialized = False

    def initialize_ee(self) -> None:
        """Initialize Google Earth Engine API with configured project."""
        if not self._ee_initialized:
            try:
                import ee
                ee.Initialize(project=self.project_id)
                self._ee_initialized = True
                logger.info(f"Google Earth Engine initialized successfully with project '{self.project_id}'")
            except Exception as exc:
                logger.error(f"Failed to initialize Google Earth Engine: {exc}")
                raise RuntimeError(
                    f"Google Earth Engine initialization failed for project '{self.project_id}': {exc}"
                ) from exc

    def detect_flood_sentinel1(
        self,
        bbox: Optional[List[float]] = None,
        pre_start: str = DEFAULT_PRE_START,
        pre_end: str = DEFAULT_PRE_END,
        post_start: str = DEFAULT_POST_START,
        post_end: str = DEFAULT_POST_END,
        threshold_db: float = -2.0,
        smoothing_radius: int = 50,
        polarization: str = "VV",
        pass_direction: str = "ASCENDING",
        simplify_tolerance: float = 0.0001,
    ) -> Dict[str, Any]:
        """
        Perform real Sentinel-1 SAR change detection for flood mapping.

        Args:
            bbox: AOI bounding box [min_lon, min_lat, max_lon, max_lat]
            pre_start: Pre-event start date (YYYY-MM-DD)
            pre_end: Pre-event end date (YYYY-MM-DD)
            post_start: Post-event start date (YYYY-MM-DD)
            post_end: Post-event end date (YYYY-MM-DD)
            threshold_db: SAR backscatter drop threshold in dB (default -2.0 dB)
            smoothing_radius: Spatial focal mean smoothing radius in metres
            polarization: S1 polarization ('VV' or 'VH')
            pass_direction: S1 orbit pass direction ('ASCENDING' or 'DESCENDING')
            simplify_tolerance: Geometry simplification tolerance in degrees

        Returns:
            Dict containing real detection statistics, acquisition metadata, and GeoJSON polygons.
        """
        self.initialize_ee()
        import ee

        aoi_bbox = bbox or SOUTH_YORKSHIRE_BBOX
        roi = ee.Geometry.Rectangle(aoi_bbox)

        # 1. Query Sentinel-1 GRD image collections
        s1_coll = (
            ee.ImageCollection("COPERNICUS/S1_GRD")
            .filterBounds(roi)
            .filter(ee.Filter.eq("instrumentMode", "IW"))
            .filter(ee.Filter.listContains("transmitterReceiverPolarisation", polarization))
        )

        if pass_direction in ("ASCENDING", "DESCENDING"):
            s1_coll = s1_coll.filter(ee.Filter.eq("orbitProperties_pass", pass_direction))

        pre_coll = s1_coll.filterDate(pre_start, pre_end)
        post_coll = s1_coll.filterDate(post_start, post_end)

        pre_size = pre_coll.size().getInfo()
        post_size = post_coll.size().getInfo()

        if pre_size == 0 or post_size == 0:
            raise ValueError(
                f"Insufficient Sentinel-1 GRD scenes found in GEE for AOI {aoi_bbox}. "
                f"Pre-event scenes: {pre_size}, Post-event scenes: {post_size}."
            )

        # Extract real acquisition metadata
        pre_info = pre_coll.getInfo()["features"]
        post_info = post_coll.getInfo()["features"]

        pre_scene_ids = [f["properties"].get("system:index", f["id"]) for f in pre_info]
        post_scene_ids = [f["properties"].get("system:index", f["id"]) for f in post_info]

        pre_timestamps = [
            ee.Date(f["properties"]["system:time_start"]).format("YYYY-MM-dd HH:mm:ss").getInfo()
            for f in pre_info
        ]
        post_timestamps = [
            ee.Date(f["properties"]["system:time_start"]).format("YYYY-MM-dd HH:mm:ss").getInfo()
            for f in post_info
        ]

        acquisition_metadata = {
            "gee_project": self.project_id,
            "satellite": "Sentinel-1 GRD (COPERNICUS/S1_GRD)",
            "instrument_mode": "IW",
            "polarization": polarization,
            "orbit_pass": pass_direction,
            "aoi_bbox": aoi_bbox,
            "pre_event": {
                "date_range": [pre_start, pre_end],
                "scene_count": pre_size,
                "scene_ids": pre_scene_ids,
                "acquisition_timestamps": pre_timestamps,
            },
            "post_event": {
                "date_range": [post_start, post_end],
                "scene_count": post_size,
                "scene_ids": post_scene_ids,
                "acquisition_timestamps": post_timestamps,
            },
            "processing_params": {
                "threshold_db": threshold_db,
                "smoothing_radius_m": smoothing_radius,
                "slope_threshold_deg": 5.0,
                "permanent_water_occurrence_threshold_pct": 50,
            },
        }

        # 2. Backscatter Compositing & Speckle Filtering
        pre_img = pre_coll.select(polarization).median()
        post_img = post_coll.select(polarization).median()

        pre_smoothed = pre_img.focal_mean(smoothing_radius, "circle", "meters")
        post_smoothed = post_img.focal_mean(smoothing_radius, "circle", "meters")

        # 3. Log-ratio / dB Difference Calculation
        # VV values in GEE S1_GRD are in dB (10*log10(sigma0))
        diff = post_smoothed.subtract(pre_smoothed)

        # 4. Binary Thresholding
        flood_mask_raw = diff.lt(threshold_db)

        # 5. Permanent Water Masking (JRC Global Surface Water)
        gsw = ee.Image("JRC/GSW1_4/GlobalSurfaceWater")
        perm_water = gsw.select("occurrence").gt(50)

        # 6. Slope Masking (USGS SRTM DEM < 5 degrees slope)
        dem = ee.Image("USGS/SRTMGL1_003")
        slope = ee.Terrain.slope(dem)

        # Final masked flood image
        flood_mask = flood_mask_raw.And(perm_water.Not()).And(slope.lt(5)).rename("flood")
        flood_mask_only = flood_mask.selfMask()

        # 7. Statistics & Area Estimation
        area_img = flood_mask_only.multiply(ee.Image.pixelArea())
        area_stats = area_img.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=roi,
            scale=30,
            maxPixels=1e8,
        )

        total_area_m2 = area_stats.get("flood").getInfo() or 0.0
        flood_area_km2 = total_area_m2 / 1_000_000.0
        flood_area_ha = total_area_m2 / 10_000.0

        # Calculate pixel counts over ROI
        pixel_count_stats = flood_mask.reduceRegion(
            reducer=ee.Reducer.frequencyHistogram(),
            geometry=roi,
            scale=30,
            maxPixels=1e8,
        ).get("flood").getInfo() or {}

        flooded_pixels = int(pixel_count_stats.get("1", 0))
        non_flooded_pixels = int(pixel_count_stats.get("0", 0))
        total_pixels = flooded_pixels + non_flooded_pixels
        flood_pct = round((flooded_pixels / max(total_pixels, 1)) * 100, 4)

        # 8. Raster to Vector (GeoJSON Polygon generation)
        vectors = flood_mask_only.reduceToVectors(
            geometry=roi,
            scale=30,
            geometryType="polygon",
            eightConnected=True,
            maxPixels=1e8,
        )

        ee_geojson = vectors.getInfo()
        raw_features = ee_geojson.get("features", [])

        # Process geometries using GeoPandas / Shapely if installed, or use Earth Engine GeoJSON directly
        try:
            import geopandas as gpd
            from shapely.geometry import shape

            shapely_geoms = []
            for feat in raw_features:
                geom_dict = feat.get("geometry")
                if geom_dict:
                    try:
                        s_geom = shape(geom_dict)
                        if not s_geom.is_empty and s_geom.is_valid:
                            if simplify_tolerance > 0:
                                s_geom = s_geom.simplify(simplify_tolerance, preserve_topology=True)
                            if not s_geom.is_empty:
                                shapely_geoms.append(s_geom)
                    except Exception:
                        pass

            if shapely_geoms:
                gdf = gpd.GeoDataFrame(geometry=shapely_geoms, crs="EPSG:4326")
                import json
                final_geojson = json.loads(gdf.to_json())
                polygon_count = len(gdf)
            else:
                final_geojson = {"type": "FeatureCollection", "features": []}
                polygon_count = 0
        except ImportError:
            # Fallback to direct Earth Engine GeoJSON output when GeoPandas is not installed
            final_features = []
            for feat in raw_features:
                geom = feat.get("geometry")
                if geom and geom.get("coordinates"):
                    final_features.append({
                        "type": "Feature",
                        "geometry": geom,
                        "properties": feat.get("properties", {}),
                    })
            final_geojson = {
                "type": "FeatureCollection",
                "features": final_features,
            }
            polygon_count = len(final_features)

        bounds_dict = {
            "left": aoi_bbox[0],
            "bottom": aoi_bbox[1],
            "right": aoi_bbox[2],
            "top": aoi_bbox[3],
        }

        return {
            "success": True,
            "method_used": "gee_sentinel1_sar_change_detection",
            "flooded_pixels": flooded_pixels,
            "total_pixels": total_pixels,
            "flood_percentage": flood_pct,
            "flood_area_km2": round(flood_area_km2, 4),
            "flood_area_ha": round(flood_area_ha, 4),
            "polygon_count": polygon_count,
            "bounds": bounds_dict,
            "crs": "EPSG:4326",
            "geojson": final_geojson,
            "acquisition_metadata": acquisition_metadata,
            "notes": [
                f"Real Sentinel-1 GRD change detection executed via Google Earth Engine (Project: {self.project_id}).",
                f"Analyzed {pre_size} pre-event and {post_size} post-event SAR scenes over South Yorkshire / River Don.",
                f"Applied SAR speckle filtering ({smoothing_radius}m focal mean), dB backscatter thresholding ({threshold_db} dB), JRC permanent water subtraction, and SRTM DEM slope filtering.",
                f"Vectorized into {polygon_count} real georeferenced flood polygons covering {flood_area_km2:.4f} km².",
            ],
            "error": None,
        }
