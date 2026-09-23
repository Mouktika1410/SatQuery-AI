"""
Fetch real OpenStreetMap road network for Kerala 2018 flood AOI [76.25, 9.35, 76.55, 9.75].
"""

import json
import urllib.request
import os

overpass_url = "https://overpass-api.de/api/interpreter"
# Query all highways in Kerala AOI bounding box
query = """
[out:json][timeout:30];
(
  way["highway"](9.35, 76.25, 9.75, 76.55);
);
out body;
>;
out skel qt;
"""

req = urllib.request.Request(
    overpass_url,
    data=query.encode("utf-8"),
    headers={"User-Agent": "SatQuery-AI/1.0"}
)

print("Querying OpenStreetMap Overpass API for Kerala road network...")
with urllib.request.urlopen(req) as response:
    data = json.loads(response.read().decode("utf-8"))

elements = data.get("elements", [])
print(f"Downloaded {len(elements)} raw OSM nodes & ways.")

nodes = {e["id"]: (e["lon"], e["lat"]) for e in elements if e["type"] == "node"}
ways = [e for e in elements if e["type"] == "way"]

features = []
for w in ways:
    w_nodes = w.get("nodes", [])
    coords = [nodes[n] for n in w_nodes if n in nodes]
    if len(coords) >= 2:
        tags = w.get("tags", {})
        features.append({
            "type": "Feature",
            "properties": {
                "osm_id": w["id"],
                "name": tags.get("name", tags.get("ref", "Inundated Road Corridor")),
                "highway": tags.get("highway", "road"),
                "surface": tags.get("surface", "asphalt/unpaved")
            },
            "geometry": {
                "type": "LineString",
                "coordinates": coords
            }
        })

print(f"Constructed {len(features)} real OpenStreetMap road LineString features!")
fc = {"type": "FeatureCollection", "features": features}

base_data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data"))
kerala_roads_path = os.path.join(base_data_dir, "roads", "kerala_roads.geojson")
roads_path = os.path.join(base_data_dir, "roads", "roads.geojson")

with open(kerala_roads_path, "w") as f:
    json.dump(fc, f, indent=2)
with open(roads_path, "w") as f:
    json.dump(fc, f, indent=2)

print(f"Successfully saved real OSM road network dataset to {roads_path}!")
