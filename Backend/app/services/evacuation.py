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
    from shapely.geometry import Point, LineString, MultiLineString
    from shapely.ops import nearest_points
    from shapely.validation import make_valid
    import networkx as nx
    from scipy.spatial import cKDTree
    import numpy as np
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
                        "route_geojson": None,
                        "route_distance_km": None,
                        "origin_name": None,
                    }
                )

            # Sort by distance to flood (nearest accessible first)
            candidates.sort(key=lambda x: x["distance_to_flood_km"] or 9999.0)

            # Determine route origin relevant to flood analysis
            origin_name = "Flood Boundary"
            try:
                villages_gdf = gis_repo.load_layer("villages") if hasattr(gis_repo, "load_layer") else None
                if villages_gdf is not None and len(villages_gdf) > 0:
                    v_reproj = villages_gdf.to_crs(flood_gdf.crs) if villages_gdf.crs != flood_gdf.crs else villages_gdf
                    inter = gpd.overlay(flood_gdf, v_reproj, how="intersection")
                    if len(inter) > 0:
                        inter["calc_area"] = inter.to_crs(metric_crs).geometry.area
                        best_row = inter.sort_values(by="calc_area", ascending=False).iloc[0]
                        v_name = best_row.get("name") or best_row.get("NAME")
                        if v_name and str(v_name) != "nan":
                            origin_name = f"Flood Boundary ({v_name})"
            except Exception as exc:
                logger.debug("Failed to detect primary affected village for route origin: %s", exc)

            # Compute road routing along real road network for candidates
            try:
                roads_gdf = gis_repo.load_layer("roads") if hasattr(gis_repo, "load_layer") else None
                road_graph, road_nodes, road_tree = self._get_or_build_road_graph(roads_gdf)

                if road_graph is not None and road_nodes and road_tree is not None:
                    for c in candidates:
                        try:
                            poi_geom = Point(c["lon"], c["lat"])
                            nearest_flood_pt, _ = nearest_points(flood_boundary_wgs84, poi_geom)

                            _, orig_idx = road_tree.query([nearest_flood_pt.x, nearest_flood_pt.y])
                            orig_node = road_nodes[orig_idx]

                            _, tgt_idx = road_tree.query([c["lon"], c["lat"]])
                            tgt_node = road_nodes[tgt_idx]

                            if nx.has_path(road_graph, orig_node, tgt_node):
                                path = nx.shortest_path(road_graph, orig_node, tgt_node, weight="weight")
                                dist_m = nx.shortest_path_length(road_graph, orig_node, tgt_node, weight="weight")
                                dist_km = round(dist_m / 1000.0, 2)

                                coords = [[round(float(nearest_flood_pt.x), 6), round(float(nearest_flood_pt.y), 6)]]
                                for n in path:
                                    coords.append([round(float(n[0]), 6), round(float(n[1]), 6)])
                                coords.append([round(float(c["lon"]), 6), round(float(c["lat"]), 6)])

                                c["route_geojson"] = {
                                    "type": "Feature",
                                    "properties": {
                                        "destination": c["name"],
                                        "destination_type": c["type"],
                                        "origin": origin_name,
                                        "distance_km": dist_km,
                                    },
                                    "geometry": {
                                        "type": "LineString",
                                        "coordinates": coords,
                                    },
                                }
                                c["route_distance_km"] = dist_km
                                c["origin_name"] = origin_name
                        except Exception as err:
                            logger.debug("Routing failed for %s: %s", c.get("name"), err)
            except Exception as exc:
                logger.error("Road network routing computation failed: %s", exc)

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

    # Cached road network spatial graph
    _cached_road_graph = None
    _cached_road_nodes = None
    _cached_road_tree = None
    _cached_roads_count = None

    def _get_or_build_road_graph(self, roads_gdf: Any):
        """
        Builds and caches a connected NetworkX spatial graph from the roads GeoDataFrame.
        Uses tolerance-based node snapping and bridging to guarantee network connectivity.
        """
        if roads_gdf is None or len(roads_gdf) == 0:
            return None, None, None

        if (
            EvacuationService._cached_road_graph is not None
            and EvacuationService._cached_roads_count == len(roads_gdf)
        ):
            return (
                EvacuationService._cached_road_graph,
                EvacuationService._cached_road_nodes,
                EvacuationService._cached_road_tree,
            )

        try:
            G_raw = nx.Graph()
            for _, row in roads_gdf.iterrows():
                geom = row.geometry
                if geom is None or geom.is_empty:
                    continue
                lines = []
                if geom.geom_type == "LineString":
                    lines = [geom]
                elif geom.geom_type == "MultiLineString":
                    lines = list(geom.geoms)

                for line in lines:
                    coords = list(line.coords)
                    for i in range(len(coords) - 1):
                        u = (round(coords[i][0], 6), round(coords[i][1], 6))
                        v = (round(coords[i + 1][0], 6), round(coords[i + 1][1], 6))
                        d_lon = (v[0] - u[0]) * 111320 * math.cos(math.radians((u[1] + v[1]) / 2))
                        d_lat = (v[1] - u[1]) * 110540
                        dist = math.hypot(d_lon, d_lat)
                        if dist > 0:
                            G_raw.add_edge(u, v, weight=dist)

            raw_nodes = list(G_raw.nodes())
            if not raw_nodes:
                return None, None, None

            raw_coords = np.array(raw_nodes)
            tree_raw = cKDTree(raw_coords)

            # Cluster nodes within 25 meters (0.00025 deg)
            node_map = {}
            for i, pt in enumerate(raw_coords):
                if i in node_map:
                    continue
                neighbors = tree_raw.query_ball_point(pt, 0.00025)
                for n_idx in neighbors:
                    if n_idx not in node_map:
                        node_map[n_idx] = tuple(pt)

            G_snapped = nx.Graph()
            for u, v, data in G_raw.edges(data=True):
                u_idx = tree_raw.query(u)[1]
                v_idx = tree_raw.query(v)[1]
                u_rep = node_map[u_idx]
                v_rep = node_map[v_idx]
                if u_rep != v_rep:
                    G_snapped.add_edge(u_rep, v_rep, weight=data["weight"])

            snapped_nodes = list(G_snapped.nodes())
            if not snapped_nodes:
                return None, None, None

            snapped_pts = np.array(snapped_nodes)
            tree_snapped = cKDTree(snapped_pts)

            # Bridge close road endpoints (<60m)
            pairs = tree_snapped.query_pairs(0.00055)
            for i, j in pairs:
                u = snapped_nodes[i]
                v = snapped_nodes[j]
                if not nx.has_path(G_snapped, u, v):
                    d_lon = (v[0] - u[0]) * 111320 * math.cos(math.radians((u[1] + v[1]) / 2))
                    d_lat = (v[1] - u[1]) * 110540
                    dist = math.hypot(d_lon, d_lat)
                    G_snapped.add_edge(u, v, weight=dist)

            # Connect any remaining disconnected components to the main network
            comps = list(nx.connected_components(G_snapped))
            if len(comps) > 1:
                main_comp = max(comps, key=len)
                main_nodes = np.array(list(main_comp))
                tree_main = cKDTree(main_nodes)
                for comp in comps:
                    if comp == main_comp:
                        continue
                    c_nodes = np.array(list(comp))
                    dists, indices = tree_main.query(c_nodes)
                    best_i = int(np.argmin(dists))
                    u = tuple(c_nodes[best_i])
                    v = tuple(main_nodes[indices[best_i]])
                    d_lon = (v[0] - u[0]) * 111320 * math.cos(math.radians((u[1] + v[1]) / 2))
                    d_lat = (v[1] - u[1]) * 110540
                    dist = math.hypot(d_lon, d_lat)
                    G_snapped.add_edge(u, v, weight=dist)

            final_nodes = list(G_snapped.nodes())
            final_tree = cKDTree(np.array(final_nodes))

            EvacuationService._cached_road_graph = G_snapped
            EvacuationService._cached_road_nodes = final_nodes
            EvacuationService._cached_road_tree = final_tree
            EvacuationService._cached_roads_count = len(roads_gdf)

            return G_snapped, final_nodes, final_tree
        except Exception as exc:
            logger.error("Failed to build road graph: %s", exc)
            return None, None, None

