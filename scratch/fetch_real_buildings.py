import urllib.request
import json
import shapely.geometry

q = """[out:json][timeout:25];
(
  way["building"](9.64,76.42,9.72,76.50);
);
out geom 300;
"""

print("Fetching real building footprints from OpenStreetMap...")
req = urllib.request.Request("https://overpass-api.de/api/interpreter", data=q.encode('utf-8'), headers={'User-Agent': 'SatQuery-AI/1.0'})
with urllib.request.urlopen(req, timeout=30) as resp:
    data = json.loads(resp.read().decode('utf-8'))

elements = data.get("elements", [])
print(f"Fetched {len(elements)} real building footprints.")

features = []
for idx, el in enumerate(elements):
    pts = [(pt["lon"], pt["lat"]) for pt in el.get("geometry", [])]
    if len(pts) >= 3:
        if pts[0] != pts[-1]:
            pts.append(pts[0])
        tags = el.get("tags", {})
        b_type = tags.get("building", "residential")
        features.append({
            "type": "Feature",
            "properties": {
                "building_id": f"OSM_BLD_{el.get('id', idx+1)}",
                "type": b_type,
                "name": tags.get("name", "Building")
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [pts]
            }
        })

print(f"Constructed {len(features)} real building Polygon features.")
with open("scratch/real_buildings.geojson", "w", encoding="utf-8") as out_f:
    json.dump({"type": "FeatureCollection", "features": features}, out_f, indent=2)

print("Saved scratch/real_buildings.geojson!")
