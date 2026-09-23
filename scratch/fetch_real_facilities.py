import urllib.request
import json
import geopandas as gpd
from shapely.geometry import Point, shape
import rasterio
import sys
sys.path.insert(0, 'Backend')
from app.services.flood_detection import FloodDetectionService
from app.services.polygon_generation import PolygonGenerationService

# First detect flood polygon so we know which facilities are outside the flood
det = FloodDetectionService().detect('data/test_images/kerala_before_flood.tif', 'data/test_images/kerala_after_flood.tif')
ds = rasterio.open('data/test_images/kerala_before_flood.tif')
poly = PolygonGenerationService().generate(det['mask_array'], ds.transform, ds.crs.to_wkt())
flood_geom = shape(poly['geojson']['features'][0]['geometry'])

q = """[out:json][timeout:25];
(
  node["amenity"~"school|college|hospital|clinic|community_centre|townhall"](9.58,76.38,9.76,76.53);
);
out body;
"""

print("Fetching real educational, health, and community facilities from OSM...")
req = urllib.request.Request("https://overpass-api.de/api/interpreter", data=q.encode('utf-8'), headers={'User-Agent': 'SatQuery-AI/1.0'})
with urllib.request.urlopen(req, timeout=30) as resp:
    data = json.loads(resp.read().decode('utf-8'))

elements = data.get("elements", [])
print(f"Fetched {len(elements)} raw facility nodes.")

features = []
for el in elements:
    tags = el.get("tags", {})
    name = tags.get("name") or tags.get("name:en")
    if not name:
        continue
    lat, lon = el["lat"], el["lon"]
    amenity = tags.get("amenity", "community_centre")
    pt = Point(lon, lat)
    # Check if point is outside flood polygon (not flooded)
    dist_deg = pt.distance(flood_geom)
    dist_km = dist_deg * 111.0 # approx
    
    # We want facilities within reasonable proximity (e.g. 0.3 km to 6 km outside the flood)
    if not flood_geom.contains(pt) and dist_km <= 6.0:
        # standard evacuation capacity estimate based on amenity type
        capacity = 500 if amenity in ("school", "college") else (250 if amenity == "hospital" else 350)
        features.append({
            "type": "Feature",
            "properties": {
                "name": name,
                "type": amenity,
                "capacity": capacity,
                "osm_id": el["id"],
                "amenity": amenity,
                "distance_km": round(dist_km, 2)
            },
            "geometry": {
                "type": "Point",
                "coordinates": [lon, lat]
            }
        })

print(f"Selected {len(features)} real suitable safe facilities around the Kerala flood zone.")
for f in features[:8]:
    p = f["properties"]
    print(f" - {p['name']} ({p['type']}): {p['distance_km']} km away")

with open("scratch/real_facilities.geojson", "w", encoding="utf-8") as out_f:
    json.dump({"type": "FeatureCollection", "features": features}, out_f, indent=2)

print("Saved scratch/real_facilities.geojson!")
