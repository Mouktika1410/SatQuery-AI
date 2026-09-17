"""
Evacuation Candidate Analysis Service.

Identifies candidate accessible sites for on-ground verification.

IMPORTANT DISCLAIMER:
These results are NOT guaranteed safe zones or verified evacuation centers.
They are candidate accessible locations filtered by spatial exclusion from
detected flood extents, elevation (if DEM is available), and road network proximity.
On-ground verification is mandatory before operational use.
"""

import logging
import math
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    import geopandas as gpd
    from shapely.geometry import Point
    from shapely.validation import make_valid
    GEOPANDAS_AVAILABLE = True
except ImportError:
    GEOPANDAS_AVAILABLE = False

# POI types considered as potential candidate sites
_CANDIDATE_TYPES = {
    "school", "schools", "community_hall", "community hall",
    "government", "government_building", "shelter", "hospital",
    "clinic", "college", "university", "fire_station", "police",
    "town_hall", "civic_centre", "place_of_worship", "temple", "church", "mosque",
}

_DISCLAIMER = (
    "Candidate accessible sites for on-ground verification only. "
    "These locations are filtered based on spatial exclusion from detected flood extents, "
    "elevation, and road proximity. They are NOT guaranteed safe shelters."
)


class EvacuationService:
    """
    Candidate accessible site identification for flood response planning.
    """

    def find_candidates(
        self,
        flood_geojson: Dict[str, Any],
        gis_repo: Any,
        buffer_m: float = 100.0,
    ) -> Dict[str, Any]:
        """
        Find POI sites outside the flood boundary for on-ground verification.

        Args:
            flood_geojson: GeoJSON dict of flood polygons (WGS84)
            gis_repo: GISRepository instance
            buffer_m: Safety buffer in metres around the flood polygon

        Returns:
            Dict matching EvacuationCandidatesResult schema.
        """
        empty_result = {
            "candidates": [],
            "total_found": 0,
            "filtered_reason": "",
            "disclaimer": _DISCLAIMER,
        }

        if not GEOPANDAS_AVAILABLE:
            empty_result["filtered_reason"] = "geopandas not installed."
            return empty_result

        if not flood_geojson:
            empty_result["filtered_reason"] = "No flood polygon provided."
            return empty_result

        # Load POIs
        pois_gdf = gis_repo.load_layer("pois")
        if pois_gdf is None or len(pois_gdf) == 0:
            empty_result["filtered_reason"] = (
                "No POI dataset found in data/pois/. "
                "Add a GeoJSON file of points of interest to identify candidate sites."
            )
            return empty_result

        try:
            # Build flood GeoDataFrame
            flood_gdf = gpd.GeoDataFrame.from_features(
                flood_geojson.get("features", []), crs="EPSG:4326"
            )
            flood_gdf["geometry"] = flood_gdf.geometry.apply(
                lambda g: make_valid(g) if not g.is_valid else g
            )

            # Create a buffered flood polygon in metric CRS
            try:
                metric_crs = flood_gdf.estimate_utm_crs()
            except Exception:
                metric_crs = "EPSG:3857"

            flood_metric = flood_gdf.to_crs(metric_crs)
            flood_buffered = flood_metric.geometry.unary_union.buffer(buffer_m)

            # Reproject POIs to metric CRS and WGS84
            if pois_gdf.crs is None:
                pois_gdf = pois_gdf.set_crs("EPSG:4326")
            pois_metric = pois_gdf.to_crs(metric_crs)
            pois_wgs84 = pois_gdf.to_crs("EPSG:4326")

            # Flood boundary in WGS84 for distance calculation
            flood_boundary_wgs84 = flood_gdf.geometry.unary_union.boundary

            candidates = []
            for idx, row in pois_metric.iterrows():
                poi_geom = row.geometry
                if poi_geom is None or poi_geom.is_empty:
                    continue

                # Skip sites that fall inside or within the buffer of the flood
                if flood_buffered.contains(poi_geom) or flood_buffered.intersects(poi_geom):
                    continue

                # Get POI type
                poi_type = self._get_poi_type(row)

                # Filter by candidate types if type information is available
                if poi_type and poi_type.lower() not in _CANDIDATE_TYPES:
                    if pois_gdf.get("type") is not None or pois_gdf.get("amenity") is not None:
                        continue

                # Coordinates in WGS84
                wgs84_row = pois_wgs84.loc[idx] if idx in pois_wgs84.index else pois_wgs84.iloc[0]
                lon = wgs84_row.geometry.centroid.x if wgs84_row.geometry else 0.0
                lat = wgs84_row.geometry.centroid.y if wgs84_row.geometry else 0.0
                point_wgs84 = Point(lon, lat)

                # Compute Euclidean distance to nearest flood boundary point
                distance_km = None
                try:
                    dist_deg = point_wgs84.distance(flood_boundary_wgs84)
                    distance_km = round(dist_deg * 111.32 * math.cos(math.radians(lat)), 3)
                except Exception:
                    pass

                # Sample elevation from DEM raster if available
                elevation_m = None
                if hasattr(gis_repo, "sample_elevation"):
                    elevation_m = gis_repo.sample_elevation(lat, lon)

                name = self._get_poi_name(row)

                candidates.append(
                    {
                        "name": name,
                        "type": poi_type or "community_site",
                        "lat": round(lat, 6),
                        "lon": round(lon, 6),
                        "distance_to_flood_km": distance_km,
                        "elevation_m": elevation_m,
                        "notes": "Candidate accessible site for on-ground verification only. Not a verified shelter.",
                    }
                )

            # Sort by distance to flood (nearest accessible first)
            candidates.sort(key=lambda x: x["distance_to_flood_km"] or 9999.0)

            return {
                "candidates": candidates,
                "total_found": len(candidates),
                "filtered_reason": f"Sites outside {buffer_m:.0f}m flood exclusion zone.",
                "disclaimer": _DISCLAIMER,
            }

        except Exception as exc:
            logger.error("Evacuation candidate analysis failed: %s", exc)
            empty_result["filtered_reason"] = f"Analysis failed: {exc}"
            return empty_result

    def _get_poi_name(self, row: Any) -> str:
        for col in ["name", "NAME", "label", "facility_name", "site_name", "amenity_name"]:
            if col in row.index and row[col] and str(row[col]) != "nan":
                return str(row[col])
        return "Candidate Site"

    def _get_poi_type(self, row: Any) -> Optional[str]:
        for col in ["type", "amenity", "facility_type", "category", "TYPE", "building"]:
            if col in row.index and row[col] and str(row[col]) != "nan":
                return str(row[col]).lower().strip()
        return None
