"""
GIS Overlay Service.

Performs deterministic spatial intersections between flood polygons
and geospatial infrastructure layers using GeoPandas and Shapely.
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

try:
    import geopandas as gpd
    import pandas as pd
    from shapely.validation import make_valid
    GEOPANDAS_AVAILABLE = True
except ImportError:
    GEOPANDAS_AVAILABLE = False


class GISOverlayService:
    """
    Deterministic spatial overlay and intersection operations.
    All results are computed from real geospatial data — no values are invented.
    """

    def overlay_flood_with_layers(
        self,
        flood_gdf: Any,
        layer_type: str,
        data_gdf: Any,
    ) -> Optional[Any]:
        """
        Intersect a data layer GeoDataFrame with the flood polygon GeoDataFrame.

        Returns a GeoDataFrame of features from data_gdf that intersect the flood,
        with the intersected geometry. Returns None on failure.
        """
        if not GEOPANDAS_AVAILABLE:
            return None
        if flood_gdf is None or data_gdf is None:
            return None

        try:
            # Ensure CRS match
            if data_gdf.crs != flood_gdf.crs:
                data_gdf = data_gdf.to_crs(flood_gdf.crs)

            # Fix invalid geometries
            flood_gdf = flood_gdf.copy()
            flood_gdf["geometry"] = flood_gdf.geometry.apply(
                lambda g: make_valid(g) if not g.is_valid else g
            )
            data_gdf = data_gdf.copy()
            data_gdf["geometry"] = data_gdf.geometry.apply(
                lambda g: make_valid(g) if not g.is_valid else g
            )

            # Intersect
            intersected = gpd.overlay(data_gdf, flood_gdf, how="intersection", keep_geom_type=False)
            intersected = intersected[~intersected.geometry.is_empty]
            return intersected if len(intersected) > 0 else None

        except Exception as exc:
            logger.error("GIS overlay failed for layer '%s': %s", layer_type, exc)
            return None

    def compute_affected_road_length_km(
        self, roads_gdf: Any, flood_gdf: Any
    ) -> float:
        """
        Calculate the total length of roads within the flood polygon in kilometres.

        Reprojects to a metric CRS before measuring to ensure accurate distances.
        """
        if not GEOPANDAS_AVAILABLE:
            return 0.0
        if roads_gdf is None or flood_gdf is None:
            return 0.0

        try:
            # Ensure CRS match
            if roads_gdf.crs != flood_gdf.crs:
                roads_gdf = roads_gdf.to_crs(flood_gdf.crs)

            # Clip road network to flood boundary
            clipped = gpd.clip(roads_gdf, flood_gdf)
            if clipped.empty:
                return 0.0

            # Reproject to metric CRS for length measurement
            try:
                metric_crs = clipped.estimate_utm_crs()
            except Exception:
                metric_crs = "EPSG:3857"  # Web Mercator fallback

            clipped_metric = clipped.to_crs(metric_crs)
            total_length_m = float(clipped_metric.geometry.length.sum())
            return round(total_length_m / 1000.0, 4)

        except Exception as exc:
            logger.error("Road length calculation failed: %s", exc)
            return 0.0
