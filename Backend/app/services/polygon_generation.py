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
    from shapely.geometry import shape, mapping, MultiPolygon, Polygon
    from shapely.ops import unary_union
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
            simplify_tolerance: Simplification tolerance (in CRS units)

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
            geometries = []
            for geom_dict, value in shapes_gen:
                if value == 1:
                    geom = shape(geom_dict)
                    if not geom.is_valid:
                        geom = make_valid(geom)
                    if not geom.is_empty:
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

            # 2. Unify all extracted raster geometries topologically into ONE continuous region
            unified_geom = unary_union(geometries)
            if not unified_geom.is_valid:
                unified_geom = make_valid(unified_geom)

            # 3. If MultiPolygon, close small gaps or select the single largest continuous component
            if isinstance(unified_geom, MultiPolygon):
                # Adaptive buffer distance based on CRS units (degrees vs metres)
                is_geo = True
                try:
                    if crs_wkt and PYPROJ_AVAILABLE:
                        c = PyProjCRS.from_user_input(crs_wkt)
                        if c and not c.is_geographic:
                            is_geo = False
                except Exception:
                    pass
                closing_dist = 0.002 if is_geo else 25.0

                # Try morphological closing to bridge minor gaps
                merged_geom = unified_geom.buffer(closing_dist).buffer(-closing_dist)
                if isinstance(merged_geom, Polygon) and not merged_geom.is_empty:
                    unified_geom = merged_geom
                else:
                    sub_polys = [
                        p for p in getattr(merged_geom, 'geoms', getattr(unified_geom, 'geoms', []))
                        if isinstance(p, Polygon) and not p.is_empty
                    ]
                    if sub_polys:
                        unified_geom = max(sub_polys, key=lambda p: p.area)

            # 4. Apply topology simplification if requested
            if simplify_tolerance > 0 and not unified_geom.is_empty:
                simplified_geom = unified_geom.simplify(simplify_tolerance, preserve_topology=True)
                if isinstance(simplified_geom, Polygon) and not simplified_geom.is_empty:
                    unified_geom = simplified_geom

            if not unified_geom.is_valid:
                unified_geom = make_valid(unified_geom)

            # 5. Build GeoDataFrame with single continuous polygon
            if isinstance(unified_geom, Polygon) and not unified_geom.is_empty:
                final_geoms = [unified_geom]
            elif isinstance(unified_geom, MultiPolygon):
                # Fallback to largest single polygon
                largest_poly = max(unified_geom.geoms, key=lambda p: p.area)
                final_geoms = [largest_poly]
            else:
                final_geoms = [unified_geom]

            gdf = gpd.GeoDataFrame(geometry=final_geoms, crs=crs_wkt)

            # 7. Compute area in source CRS
            try:
                if gdf.crs and gdf.crs.is_geographic:
                    metric_crs = gdf.estimate_utm_crs()
                    gdf_metric = gdf.to_crs(metric_crs)
                else:
                    gdf_metric = gdf
                total_area_m2 = float(gdf_metric.geometry.area.sum())
            except Exception:
                total_area_m2 = float(np.sum(binary_mask > 0)) * px_w * px_h

            total_area_km2 = total_area_m2 / 1_000_000
            total_area_ha = total_area_m2 / 10_000

            # 8. Reproject to WGS84 for Leaflet
            import json
            gdf_wgs84 = gdf.to_crs("EPSG:4326")
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
