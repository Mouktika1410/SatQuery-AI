"""
Image Study Service.

Handles dual-GeoTIFF raster validation, change detection, raster-to-vector
polygonization, and geographic centroid computation for the Flood Image Study workflow.
"""

import os
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    import rasterio
    RASTERIO_AVAILABLE = True
except ImportError:
    RASTERIO_AVAILABLE = False

try:
    from shapely.geometry import shape
    from shapely.ops import unary_union
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False


class ImageStudyService:
    """
    Service for georeferenced satellite image study and flood mapping.
    """

    def validate_and_extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Validate that a file is a valid georeferenced GeoTIFF and extract metadata.

        Raises ValueError if the image is unreadable or lacks CRS/geotransform metadata.
        """
        if not RASTERIO_AVAILABLE:
            raise RuntimeError("rasterio is required for GeoTIFF image study.")

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            with rasterio.open(file_path) as ds:
                if not ds.crs:
                    raise ValueError(
                        f"File '{os.path.basename(file_path)}' is not georeferenced. "
                        "Missing Coordinate Reference System (CRS). "
                        "Only georeferenced GeoTIFF images with valid geospatial metadata are supported."
                    )

                b = ds.bounds
                px_w = abs(ds.transform.a)
                px_h = abs(ds.transform.e)

                crs_str = f"EPSG:{ds.crs.to_epsg()}" if ds.crs.to_epsg() else ds.crs.to_string()

                return {
                    "filename": os.path.basename(file_path),
                    "width": ds.width,
                    "height": ds.height,
                    "band_count": ds.count,
                    "crs": crs_str,
                    "bounds": {
                        "left": float(b.left),
                        "bottom": float(b.bottom),
                        "right": float(b.right),
                        "top": float(b.top),
                    },
                    "pixel_size_x": float(px_w),
                    "pixel_size_y": float(px_h),
                }
        except Exception as exc:
            if isinstance(exc, ValueError):
                raise
            raise ValueError(f"Failed to parse GeoTIFF file '{os.path.basename(file_path)}': {exc}") from exc

    def analyze_pair(
        self,
        pre_path: str,
        post_path: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Run the complete Image Study analysis pipeline on a pre/post GeoTIFF pair.

        Steps:
        1. Validate & extract metadata for both GeoTIFFs
        2. Execute flood detection & change analysis
        3. Convert flood mask to WGS84 GeoJSON vector polygons
        4. Compute geographic centroid (latitude, longitude) of flood geometries
        5. Return consolidated result
        """
        # Step 1: Validate GeoTIFF inputs & extract metadata
        pre_meta = self.validate_and_extract_metadata(pre_path)
        post_meta = self.validate_and_extract_metadata(post_path)

        # Step 2: Flood detection
        from app.services.flood_detection import FloodDetectionService
        opts = options or {"method": "auto", "morphology_iterations": 2}
        det_svc = FloodDetectionService()
        det_res = det_svc.detect(pre_path, post_path, opts)

        if not det_res.get("success"):
            return {
                "success": False,
                "pre_metadata": pre_meta,
                "post_metadata": post_meta,
                "flood_area_km2": 0.0,
                "flood_area_ha": 0.0,
                "polygon_count": 0,
                "centroid": None,
                "geojson": None,
                "bounds": None,
                "notes": det_res.get("notes", []),
                "error": det_res.get("error", "Flood detection failed."),
            }

        mask_array = det_res.pop("mask_array", None)

        # Step 3: Polygonize flood mask to WGS84 GeoJSON
        import rasterio
        with rasterio.open(pre_path) as ds:
            transform = ds.transform
            crs_wkt = ds.crs.to_wkt() if ds.crs else "EPSG:4326"

        from app.services.polygon_generation import PolygonGenerationService
        poly_svc = PolygonGenerationService()
        poly_res = poly_svc.generate(mask_array, transform, crs_wkt, simplify_tolerance=0.0001)

        geojson = poly_res.get("geojson")
        polygon_count = poly_res.get("polygon_count", 0)
        flood_area_km2 = poly_res.get("total_area_km2", 0.0)
        flood_area_ha = poly_res.get("total_area_ha", 0.0)

        # Step 4: Compute Centroid (latitude, longitude)
        centroid_dict = None
        if geojson and geojson.get("features") and SHAPELY_AVAILABLE:
            try:
                geoms = []
                for feat in geojson["features"]:
                    g_dict = feat.get("geometry")
                    if g_dict:
                        g = shape(g_dict)
                        if not g.is_empty and g.is_valid:
                            geoms.append(g)

                if geoms:
                    unified = unary_union(geoms)
                    cent = unified.centroid
                    centroid_dict = {
                        "latitude": round(float(cent.y), 6),
                        "longitude": round(float(cent.x), 6),
                    }
            except Exception as exc:
                logger.warning(f"Centroid calculation failed: {exc}")

        notes = det_res.get("notes", [])

        # Step 5: Population & Building Exposure GIS Analysis
        exposed_population = None
        population_geojson = None
        affected_buildings = None
        buildings_geojson = None
        try:
            import json
            data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data"))
            from app.services.gis_repository import GISRepository
            from app.services.exposure_analysis import ExposureAnalysisService
            gis_repo = GISRepository(data_dir)
            exp_svc = ExposureAnalysisService()

            # --- Village Boundaries Exposure ---
            villages_gdf = gis_repo.load_layer("villages")
            visual_villages_gdf = gis_repo.load_layer("villages_visual")
            affected_villages = []
            affected_villages_geojson = None
            if villages_gdf is not None and geojson:
                flood_gdf = exp_svc._geojson_to_gdf(geojson)
                aff_villages, v_geojson = exp_svc._compute_affected_villages(flood_gdf, villages_gdf, visual_villages_gdf)
                affected_villages = aff_villages
                affected_villages_geojson = v_geojson
                if affected_villages:
                    v_names = ", ".join([v["name"] for v in affected_villages[:4]])
                    notes.append(f"Administrative Boundaries: {len(affected_villages)} affected village/division(s) ({v_names}).")

            # --- Population Exposure ---
            pop_gdf = gis_repo.load_layer("population")
            if pop_gdf is not None and geojson:
                flood_gdf = exp_svc._geojson_to_gdf(geojson)
                if pop_gdf.crs != flood_gdf.crs:
                    pop_gdf = pop_gdf.to_crs(flood_gdf.crs)

                pop_total = exp_svc._compute_affected_population(flood_gdf, pop_gdf)
                if pop_total is not None:
                    exposed_population = pop_total

                intersected_pop = exp_svc._overlay.overlay_flood_with_layers(flood_gdf, "population", pop_gdf)
                intersected_pop_idx = set(intersected_pop.index) if intersected_pop is not None else set()

                pop_copy = pop_gdf.copy()
                pop_copy["is_exposed"] = pop_copy.index.isin(intersected_pop_idx)
                pop_wgs84 = pop_copy.to_crs("EPSG:4326")
                population_geojson = json.loads(pop_wgs84.to_json())

                if exposed_population is not None:
                    notes.append(f"Population Exposure: Estimated {exposed_population:,} people inside detected flood extent.")

            # --- Building Exposure ---
            bld_gdf = gis_repo.load_layer("buildings")
            if bld_gdf is not None and geojson:
                flood_gdf = exp_svc._geojson_to_gdf(geojson)
                if bld_gdf.crs != flood_gdf.crs:
                    bld_gdf = bld_gdf.to_crs(flood_gdf.crs)

                bld_count = exp_svc._compute_affected_buildings(flood_gdf, bld_gdf)
                if bld_count is not None:
                    affected_buildings = bld_count

                intersected_bld = exp_svc._overlay.overlay_flood_with_layers(flood_gdf, "buildings", bld_gdf)
                intersected_bld_idx = set(intersected_bld.index) if intersected_bld is not None else set()

                bld_copy = bld_gdf.copy()
                bld_copy["is_exposed"] = bld_copy.index.isin(intersected_bld_idx)
                bld_wgs84 = bld_copy.to_crs("EPSG:4326")
                buildings_geojson = json.loads(bld_wgs84.to_json())

            # --- Road Exposure & Accessibility ---
            roads_gdf = gis_repo.load_layer("roads")
            affected_road_length_km = None
            affected_roads_geojson = None
            if roads_gdf is not None and geojson:
                flood_gdf = exp_svc._geojson_to_gdf(geojson)
                road_km, roads_geojson = exp_svc._compute_affected_roads(roads_gdf, flood_gdf)
                if road_km is not None:
                    affected_road_length_km = road_km
                    affected_roads_geojson = roads_geojson
                    if affected_road_length_km > 0:
                        notes.append(f"Road Accessibility: {affected_road_length_km:.2f} km of road corridors inundated.")

        except Exception as exc:
            logger.warning(f"Exposure calculation failed in ImageStudyService: {exc}")

        bounds = det_res.get("bounds") or pre_meta.get("bounds")

        notes.append(f"Image Study analyzed 2 georeferenced GeoTIFF rasters ({pre_meta['crs']}).")
        notes.append(f"Detected {polygon_count} flood polygon(s) covering {flood_area_km2:.4f} km².")
        if centroid_dict:
            notes.append(f"Flood centroid: Lat {centroid_dict['latitude']}°, Lon {centroid_dict['longitude']}°.")

        return {
            "success": True,
            "pre_metadata": pre_meta,
            "post_metadata": post_meta,
            "flood_area_km2": flood_area_km2,
            "flood_area_ha": flood_area_ha,
            "polygon_count": polygon_count,
            "centroid": centroid_dict,
            "geojson": geojson,
            "affected_villages": affected_villages,
            "affected_villages_geojson": affected_villages_geojson,
            "exposed_population": exposed_population,
            "population_geojson": population_geojson,
            "affected_buildings": affected_buildings,
            "buildings_geojson": buildings_geojson,
            "affected_road_length_km": affected_road_length_km,
            "affected_roads_geojson": affected_roads_geojson,
            "bounds": bounds,
            "notes": notes,
            "error": None,
        }
