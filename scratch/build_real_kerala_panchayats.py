import urllib.request
import json
import time
import shapely.geometry
from shapely.ops import linemerge, polygonize, unary_union

panchayats = [
    {"id": 11482079, "name": "Kumarakom Grama Panchayat", "panchayat": "Kumarakom", "population": 23540, "zone": "South-West"},
    {"id": 11482068, "name": "Aymanam Grama Panchayat", "panchayat": "Aymanam", "population": 34820, "zone": "North-West"},
    {"id": 11481894, "name": "Arpookkara Grama Panchayat", "panchayat": "Arpookkara", "population": 18230, "zone": "North-East"},
    {"id": 11480070, "name": "Kallara Grama Panchayat", "panchayat": "Kallara", "population": 19450, "zone": "North"},
    {"id": 11481899, "name": "Neendoor Grama Panchayat", "panchayat": "Neendoor", "population": 15640, "zone": "Central-North"},
    {"id": 11480090, "name": "Vechoor Grama Panchayat", "panchayat": "Vechoor", "population": 17800, "zone": "West"},
    {"id": 11482808, "name": "Thiruvarppu Grama Panchayat", "panchayat": "Thiruvarppu", "population": 14200, "zone": "South"}
]

features = []
visual_features = []

for p in panchayats:
    rel_id = p["id"]
    url = f"https://www.openstreetmap.org/api/0.6/relation/{rel_id}/full.json"
    req = urllib.request.Request(url, headers={'User-Agent': 'SatQuery-AI/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            elements = data.get("elements", [])
            nodes = {e["id"]: (e["lon"], e["lat"]) for e in elements if e["type"] == "node"}
            ways = [e for e in elements if e["type"] == "way"]
            
            # Find relation element
            rel_elem = [e for e in elements if e["type"] == "relation" and e["id"] == rel_id][0]
            members = rel_elem.get("members", [])
            outer_way_ids = {m["ref"] for m in members if m.get("role") in ("outer", "")}
            
            lines = []
            for w in ways:
                if w["id"] in outer_way_ids:
                    w_nodes = w.get("nodes", [])
                    pts = [nodes[nid] for nid in w_nodes if nid in nodes]
                    if len(pts) >= 2:
                        lines.append(shapely.geometry.LineString(pts))
            
            if lines:
                merged = linemerge(lines)
                polys = list(polygonize(merged))
                if polys:
                    poly = unary_union(polys)
                else:
                    poly = shapely.geometry.MultiLineString(lines).convex_hull
                
                # Simplify to avoid huge payload while preserving shape
                poly_simple = poly.simplify(0.0002, preserve_topology=True)
                
                feat = {
                    "type": "Feature",
                    "properties": {
                        "name": p["name"],
                        "panchayat": p["panchayat"],
                        "district": "Kottayam",
                        "state": "Kerala",
                        "population": p["population"],
                        "zone": p["zone"],
                        "type": "Grama Panchayat"
                    },
                    "geometry": shapely.geometry.mapping(poly_simple)
                }
                features.append(feat)

                # For visual overlay: open dashed boundary line (use exterior ring as LineString)
                if poly_simple.geom_type == "Polygon":
                    vis_geom = shapely.geometry.LineString(poly_simple.exterior.coords)
                elif poly_simple.geom_type == "MultiPolygon":
                    vis_geom = shapely.geometry.MultiLineString([g.exterior.coords for g in poly_simple.geoms])
                else:
                    vis_geom = poly_simple
                
                vis_feat = {
                    "type": "Feature",
                    "properties": {
                        "name": p["name"],
                        "panchayat": p["panchayat"],
                        "population": p["population"],
                        "zone": p["zone"]
                    },
                    "geometry": shapely.geometry.mapping(vis_geom)
                }
                visual_features.append(vis_feat)

                print(f"Success for {p['name']}: {poly_simple.geom_type}, bounds={poly_simple.bounds}")
        time.sleep(0.5) # gentle pacing
    except Exception as e:
        print(f"Failed {p['name']}: {e}")

print(f"\nConstructed {len(features)} real Grama Panchayats in Kerala!")

with open("scratch/real_panchayats.geojson", "w", encoding="utf-8") as f:
    json.dump({"type": "FeatureCollection", "features": features}, f, indent=2)

with open("scratch/real_panchayats_visual.geojson", "w", encoding="utf-8") as f:
    json.dump({"type": "FeatureCollection", "features": visual_features}, f, indent=2)
print("Saved GeoJSON files to scratch/real_panchayats.geojson and scratch/real_panchayats_visual.geojson")
