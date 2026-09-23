import urllib.request
import json
import shapely.geometry
from shapely.ops import linemerge

q = """[out:json][timeout:25];
(
  way["highway"~"primary|secondary|tertiary|trunk|unclassified|residential"](9.61,76.41,9.74,76.51);
);
out geom 500;
"""

print("Fetching real OpenStreetMap roads in Kerala flood zone...")
req = urllib.request.Request("https://overpass-api.de/api/interpreter", data=q.encode('utf-8'), headers={'User-Agent': 'SatQuery-AI/1.0'})
with urllib.request.urlopen(req, timeout=30) as resp:
    data = json.loads(resp.read().decode('utf-8'))

elements = data.get("elements", [])
print(f"Fetched {len(elements)} real road elements.")

features = []
for el in elements:
    pts = [(pt["lon"], pt["lat"]) for pt in el.get("geometry", [])]
    if len(pts) >= 2:
        tags = el.get("tags", {})
        name = tags.get("name") or tags.get("ref") or f"{tags.get('highway', 'Corridor').capitalize()} Road"
        features.append({
            "type": "Feature",
            "properties": {
                "name": name,
                "highway": tags.get("highway", "secondary"),
                "surface": tags.get("surface", "asphalt"),
                "osm_id": el.get("id")
            },
            "geometry": {
                "type": "LineString",
                "coordinates": pts
            }
        })

print(f"Constructed {len(features)} road LineString features.")
with open("scratch/real_roads.geojson", "w", encoding="utf-8") as f:
    json.dump({"type": "FeatureCollection", "features": features}, f, indent=2)

print("Saved scratch/real_roads.geojson!")
