import urllib.request
import json
import shapely.geometry
from shapely.ops import linemerge, polygonize, unary_union

rel_ids = "11482079,11482068,11481894,11480090,11480070,11481899,11482808"
q = f"""[out:json][timeout:20];
relation(id:{rel_ids});
out geom;
"""

req = urllib.request.Request("https://overpass-api.de/api/interpreter", data=q.encode('utf-8'), headers={'User-Agent': 'SatQuery-AI/1.0'})
with urllib.request.urlopen(req, timeout=20) as resp:
    data = json.loads(resp.read().decode('utf-8'))
    elements = data.get("elements", [])
    print(f"Fetched {len(elements)} relations.")
    for el in elements:
        name = el.get("tags", {}).get("name:en") or el.get("tags", {}).get("name")
        outer_lines = []
        for m in el.get("members", []):
            if m.get("role") in ("outer", "") and "geometry" in m:
                pts = [(pt["lon"], pt["lat"]) for pt in m["geometry"]]
                if len(pts) >= 2:
                    outer_lines.append(shapely.geometry.LineString(pts))
        if outer_lines:
            merged = linemerge(outer_lines)
            polys = list(polygonize(merged))
            if polys:
                poly = unary_union(polys)
                print(f" - {name}: valid {poly.is_valid}, type {poly.geom_type}, bounds {poly.bounds}")
            else:
                print(f" - {name}: outer lines {len(outer_lines)}, could not polygonize cleanly")
