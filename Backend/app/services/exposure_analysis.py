"""
Exposure Analysis Service.

Calculates deterministic impact metrics for available geospatial layers.
All statistics are computed from real data overlays. When a dataset is unavailable,
the corresponding metric is set to None — never invented. Modeled metrics
such as population are explicitly documented as estimates.
"""

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    import geopandas as gpd
    from shapely.geometry import shape, mapping
    from shapely.validation import make_valid
    GEOPANDAS_AVAILABLE = True
except ImportError:
    GEOPANDAS_AVAILABLE = False

from app.services.gis_overlay import GISOverlayService


class ExposureAnalysisService:
    """
    Deterministic exposure analysis for flood impact assessment.
    """

    def __init__(self) -> None:
        self._overlay = GISOverlayService()

    def calculate_exposure(
        self,
        flood_geojson: Dict[str, Any],
        region_id: str,
        gis_repo: Any,  # GISRepository instance
    ) -> Dict[str, Any]:
        """
        Compute impact metrics for all available GIS layers.

        Returns a dict structured to match the ImpactMetrics schema.
        Only reports metrics for layers that are actually available.
        """
        result: Dict[str, Any] = {
            "affected_villages": [],
            "affected_population": None,
            "affected_buildings": None,
            "affected_road_length_km": None,
            "affected_villages_geojson": None,
            "affected_roads_geojson": None,
            "data_availability": {
                "villages": False,
                "population": False,
                "buildings": False,
                "roads": False,
                "dem": False,
            },
            "disclaimer": (
                "Impact figures and population metrics are modeled estimates based on "
                "overlaying satellite flood extents with available geospatial layers."
            ),
        }

        # Check DEM availability
        if hasattr(gis_repo, "get_dem_path"):
            result["data_availability"]["dem"] = gis_repo.get_dem_path() is not None

        if not GEOPANDAS_AVAILABLE:
            logger.warning("geopandas not available — skipping exposure analysis.")
            return result

        if not flood_geojson:
            return result

        # Build flood GeoDataFrame from GeoJSON
        try:
            flood_gdf = self._geojson_to_gdf(flood_geojson)
        except Exception as exc:
            logger.error("Failed to parse flood GeoJSON: %s", exc)
            return result

        # --- Villages -------------------------------------------------------
        villages_gdf = gis_repo.load_layer("villages")
        visual_villages_gdf = gis_repo.load_layer("villages_visual")
        if villages_gdf is not None:
            result["data_availability"]["villages"] = True
            affected, villages_geojson = self._compute_affected_villages(
                flood_gdf, villages_gdf, visual_villages_gdf
            )
            result["affected_villages"] = affected
            result["affected_villages_geojson"] = villages_geojson

        # --- Population -----------------------------------------------------
        pop_gdf = gis_repo.load_layer("population")
        if pop_gdf is not None:
            result["data_availability"]["population"] = True
            pop_total = self._compute_affected_population(flood_gdf, pop_gdf)
            result["affected_population"] = pop_total

        # --- Buildings -------------------------------------------------------
        buildings_gdf = gis_repo.load_layer("buildings")
        if buildings_gdf is not None:
            result["data_availability"]["buildings"] = True
            building_count = self._compute_affected_buildings(flood_gdf, buildings_gdf)
            result["affected_buildings"] = building_count

        # --- Roads -----------------------------------------------------------
        roads_gdf = gis_repo.load_layer("roads")
        if roads_gdf is not None:
            result["data_availability"]["roads"] = True
            road_km, roads_geojson = self._compute_affected_roads(roads_gdf, flood_gdf)
            result["affected_road_length_km"] = road_km
            result["affected_roads_geojson"] = roads_geojson

        return result

    # ------------------------------------------------------------------
    # Per-layer analysis helpers
    # ------------------------------------------------------------------

    def _compute_affected_villages(
        self, flood_gdf: Any, villages_gdf: Any, visual_villages_gdf: Optional[Any] = None
    ) -> tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Intersect village boundaries with flood polygon and compute overlap area."""
        try:
            if villages_gdf.crs != flood_gdf.crs:
                villages_gdf = villages_gdf.to_crs(flood_gdf.crs)

            # Intersect villages with flood (analytical closed polygon calculations)
            intersected = self._overlay.overlay_flood_with_layers(
                flood_gdf, "villages", villages_gdf
            )
            if intersected is None or len(intersected) == 0:
                return [], None

            # Reproject to metric CRS for area
            try:
                metric_crs = intersected.estimate_utm_crs()
            except Exception:
                metric_crs = "EPSG:3857"

            intersected_m = intersected.to_crs(metric_crs)

            results = []
            name_col = self._find_name_column(intersected)

            for _, row in intersected_m.iterrows():
                area_km2 = row.geometry.area / 1_000_000 if row.geometry else 0.0
                name = str(row.get(name_col, "Unknown")) if name_col else "Unknown"
                results.append(
                    {
                        "name": name,
                        "area_flooded_km2": round(area_km2, 4),
                        "population_affected": None,
                    }
                )

            # Sort by area descending
            results.sort(key=lambda x: x["area_flooded_km2"], reverse=True)

            # Export village boundary geometries of affected villages as WGS84 GeoJSON.
            # If visual_villages_gdf is provided, use it for the display overlay
            # (keeping open dashed lines for map rendering while preserving analytical values).
            try:
                affected_names = {r["name"] for r in results}
                target_gdf = visual_villages_gdf if visual_villages_gdf is not None else villages_gdf
                if target_gdf.crs != "EPSG:4326":
                    target_gdf = target_gdf.to_crs("EPSG:4326")
                orig_name_col = self._find_name_column(target_gdf)
                if orig_name_col:
                    affected_gdf = target_gdf[target_gdf[orig_name_col].isin(affected_names)].copy()
                else:
                    affected_gdf = target_gdf.copy()
                affected_wgs84 = affected_gdf.to_crs("EPSG:4326")
                villages_geojson = json.loads(affected_wgs84.to_json())
            except Exception:
                villages_geojson = None

            return results, villages_geojson

        except Exception as exc:
            logger.error("Village exposure computation failed: %s", exc)
            return [], None

    def _compute_affected_roads(
        self, roads_gdf: Any, flood_gdf: Any
    ) -> tuple[float, Optional[Dict[str, Any]]]:
        """Calculate inundated road length and return intersected GeoJSON."""
        try:
            if roads_gdf.crs != flood_gdf.crs:
                roads_gdf = roads_gdf.to_crs(flood_gdf.crs)

            clipped = gpd.clip(roads_gdf, flood_gdf)
            if clipped.empty:
                return 0.0, None

            from shapely.geometry import LineString as SLineString, MultiLineString as SMultiLineString
            def _extract_lines(geom: Any) -> Any:
                if geom is None or geom.is_empty:
                    return None
                if isinstance(geom, (SLineString, SMultiLineString)):
                    return geom
                if hasattr(geom, "geoms"):
                    lines = [g for g in geom.geoms if isinstance(g, (SLineString, SMultiLineString))]
                    if lines:
                        return SMultiLineString(lines) if len(lines) > 1 else lines[0]
                return None

            clipped["geometry"] = clipped["geometry"].apply(_extract_lines)
            clipped = clipped[clipped.geometry.notnull() & ~clipped.geometry.is_empty]
            if clipped.empty:
                return 0.0, None

            try:
                metric_crs = clipped.estimate_utm_crs()
            except Exception:
                metric_crs = "EPSG:3857"

            clipped_metric = clipped.to_crs(metric_crs)
            total_length_m = float(clipped_metric.geometry.length.sum())
            total_km = round(total_length_m / 1000.0, 4)

            try:
                clipped_wgs84 = clipped.to_crs("EPSG:4326")
                roads_geojson = json.loads(clipped_wgs84.to_json())
            except Exception:
                roads_geojson = None

            return total_km, roads_geojson
        except Exception as exc:
            logger.error("Road exposure computation failed: %s", exc)
            return 0.0, None

    def _compute_affected_population(
        self, flood_gdf: Any, pop_gdf: Any
    ) -> Optional[int]:
        """Sum population in features that intersect the flood polygon."""
        try:
            if pop_gdf.crs != flood_gdf.crs:
                pop_gdf = pop_gdf.to_crs(flood_gdf.crs)

            pop_col = None
            for col in ["population", "pop", "pop_total", "total_pop", "POP", "Population"]:
                if col in pop_gdf.columns:
                    pop_col = col
                    break

            if pop_col is None:
                logger.info("No population column found in population layer.")
                return None

            intersected = self._overlay.overlay_flood_with_layers(
                flood_gdf, "population", pop_gdf
            )
            if intersected is None:
                return 0

            total = int(intersected[pop_col].fillna(0).sum())
            return total

        except Exception as exc:
            logger.error("Population computation failed: %s", exc)
            return None

    def _compute_affected_buildings(
        self, flood_gdf: Any, buildings_gdf: Any
    ) -> Optional[int]:
        """Count building footprints that intersect the flood polygon."""
        try:
            if buildings_gdf.crs != flood_gdf.crs:
                buildings_gdf = buildings_gdf.to_crs(flood_gdf.crs)

            intersected = self._overlay.overlay_flood_with_layers(
                flood_gdf, "buildings", buildings_gdf
            )
            if intersected is None:
                return 0
            return len(intersected)

        except Exception as exc:
            logger.error("Building count failed: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    def _geojson_to_gdf(self, geojson: Dict[str, Any]) -> Any:
        """Convert a GeoJSON dict to a GeoDataFrame in WGS84."""
        gdf = gpd.GeoDataFrame.from_features(
            geojson.get("features", []), crs="EPSG:4326"
        )
        gdf["geometry"] = gdf.geometry.apply(
            lambda g: make_valid(g) if not g.is_valid else g
        )
        return gdf

    @staticmethod
    def _find_name_column(gdf: Any) -> Optional[str]:
        """Find a plausible name column in a GeoDataFrame."""
        for col in ["name", "NAME", "village", "VILLAGE", "admin_name", "label", "ADM2_EN"]:
            if col in gdf.columns:
                return col
        return None
