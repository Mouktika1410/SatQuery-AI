"""
Flood Polygon Generation Service.

Converts binary flood raster masks into clean GeoJSON vector polygons
using rasterio.features.shapes, Shapely, and GeoPandas.
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    import rasterio
    import rasterio.features
    RASTERIO_AVAILABLE = True
except ImportError:
    RASTERIO_AVAILABLE = False

try:
    import geopandas as gpd
    from shapely.geometry import shape, mapping
    from shapely.validation import make_valid
    GEOPANDAS_AVAILABLE = True
except ImportError:
    GEOPANDAS_AVAILABLE = False

try:
    from pyproj import CRS as PyProjCRS
    PYPROJ_AVAILABLE = True
except ImportError:
    PYPROJ_AVAILABLE = False


class PolygonGenerationService:
    """
    Service for converting binary flood masks to geospatial vector polygons.
    Outputs WGS84 GeoJSON suitable for direct use in Leaflet maps.
    """

    def generate(
        self,
        mask_array: Any,
        transform: Any,
        crs_wkt: str,
        simplify_tolerance: float = 0.0001,
    ) -> Dict[str, Any]:
        """
        Convert a binary flood mask array into GeoJSON polygon features.

        Args:
            mask_array: 2D numpy array (uint8, 0=no flood, 1=flood)
            transform: Affine transform of the raster
            crs_wkt: CRS as WKT/PROJ/EPSG string
            simplify_tolerance: Douglas-Peucker simplification tolerance (in CRS units)

        Returns:
            Dict with: success, geojson, polygon_count, total_area_km2,
                       total_area_ha, crs, simplification_tolerance, error
        """
        if not RASTERIO_AVAILABLE:
            return self._error("rasterio is not installed.")
        if not NUMPY_AVAILABLE:
            return self._error("numpy is not installed.")
        if not GEOPANDAS_AVAILABLE:
            return self._error("geopandas and/or shapely are not installed.")
        if mask_array is None:
            return self._error("mask_array is None — run flood detection first.")

        if not np.any(mask_array > 0):
            return {
                "success": True,
                "geojson": {"type": "FeatureCollection", "features": []},
                "polygon_count": 0,
                "total_area_km2": 0.0,
                "total_area_ha": 0.0,
                "crs": "EPSG:4326",
                "simplification_tolerance": simplify_tolerance,
                "error": None,
            }

        try:
            # 1. Extract polygon shapes from mask using rasterio
            binary_mask = (mask_array > 0).astype(np.uint8)
            shapes_gen = rasterio.features.shapes(
                binary_mask,
                mask=binary_mask,
                transform=transform,
            )

            img_bounds_geom = None
            try:
                h_img, w_img = binary_mask.shape
                minx = transform.c
                maxy = transform.f
                maxx = minx + transform.a * w_img
                miny = maxy + transform.e * h_img
                from shapely.geometry import box
                img_bounds_geom = box(min(minx, maxx), min(miny, maxy), max(minx, maxx), max(miny, maxy))
            except Exception:
                img_bounds_geom = None

            geometries = []
            for geom_dict, value in shapes_gen:
                if value == 1:
                    geom = shape(geom_dict)
                    if not geom.is_valid:
                        geom = make_valid(geom)
                    if not geom.is_empty:
                        # Ignore full-raster bounding box rectangle artifacts (> 95% total area)
                        if img_bounds_geom and img_bounds_geom.area > 0:
                            if (geom.area / img_bounds_geom.area) > 0.95:
                                continue
                        geometries.append(geom)

            if not geometries:
                return {
                    "success": True,
                    "geojson": {"type": "FeatureCollection", "features": []},
                    "polygon_count": 0,
                    "total_area_km2": 0.0,
                    "total_area_ha": 0.0,
                    "crs": "EPSG:4326",
                    "simplification_tolerance": simplify_tolerance,
                    "error": None,
                }

            # 2. Build GeoDataFrame with source CRS (use EPSG:4326 directly for geographic rasters to prevent WKT axis-order swapping)
            if isinstance(crs_wkt, str) and ("4326" in crs_wkt or "WGS 84" in crs_wkt or "WGS84" in crs_wkt or "GEOGCS" in crs_wkt):
                gdf = gpd.GeoDataFrame(geometry=geometries, crs="EPSG:4326")
            else:
                gdf = gpd.GeoDataFrame(geometry=geometries, crs=crs_wkt if crs_wkt else "EPSG:4326")

            # 3. Compute area in source CRS before reprojection
            try:
                # Get a metric projection for area calculation
                if gdf.crs.is_geographic:
                    metric_crs = gdf.estimate_utm_crs()
                    gdf_metric = gdf.to_crs(metric_crs)
                else:
                    gdf_metric = gdf
                total_area_m2 = float(gdf_metric.geometry.area.sum())
            except Exception:
                # Fallback area estimate from pixel count
                px_w = abs(transform.a)
                px_h = abs(transform.e)
                total_area_m2 = float(np.sum(binary_mask > 0)) * px_w * px_h

            total_area_km2 = total_area_m2 / 1_000_000
            total_area_ha = total_area_m2 / 10_000

            # 4. Simplify geometries while preserving topology
            if simplify_tolerance > 0:
                gdf["geometry"] = gdf.geometry.simplify(
                    simplify_tolerance, preserve_topology=True
                )
                # Fix any topology issues introduced by simplification
                gdf["geometry"] = gdf.geometry.apply(
                    lambda g: make_valid(g) if not g.is_valid else g
                )
                gdf = gdf[~gdf.geometry.is_empty]

            # 5. Reproject to WGS84 for Leaflet
            gdf_wgs84 = gdf.to_crs("EPSG:4326")

            # 6. Convert to GeoJSON
            import json
            geojson_str = gdf_wgs84.to_json()
            geojson_dict = json.loads(geojson_str)

            return {
                "success": True,
                "geojson": geojson_dict,
                "polygon_count": len(gdf_wgs84),
                "total_area_km2": round(total_area_km2, 4),
                "total_area_ha": round(total_area_ha, 4),
                "crs": "EPSG:4326",
                "simplification_tolerance": simplify_tolerance,
                "error": None,
            }

        except Exception as exc:
            logger.exception("Polygon generation failed")
            return self._error(str(exc))

    def from_mask_file(
        self, mask_path: str, simplify_tolerance: float = 0.0001
    ) -> Dict[str, Any]:
        """
        Load a mask raster from disk and call generate().
        """
        if not RASTERIO_AVAILABLE:
            return self._error("rasterio is not installed.")
        try:
            with rasterio.open(mask_path) as ds:
                mask_array = ds.read(1)
                transform = ds.transform
                crs_wkt = ds.crs.to_wkt() if ds.crs else "EPSG:4326"
            return self.generate(mask_array, transform, crs_wkt, simplify_tolerance)
        except Exception as exc:
            return self._error(f"Failed to read mask file: {exc}")

    @staticmethod
    def _error(message: str) -> Dict[str, Any]:
        return {
            "success": False,
            "geojson": None,
            "polygon_count": 0,
            "total_area_km2": 0.0,
            "total_area_ha": 0.0,
            "crs": "EPSG:4326",
            "simplification_tolerance": 0.0,
            "error": message,
        }
