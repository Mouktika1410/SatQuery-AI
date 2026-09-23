import urllib.request
import json
import geopandas as gpd
from shapely.geometry import Polygon, shape
import rasterio
import sys
sys.path.insert(0, 'Backend')
from app.services.flood_detection import FloodDetectionService
from app.services.polygon_generation import PolygonGenerationService

det = FloodDetectionService().detect('data/test_images/kerala_before_flood.tif', 'data/test_images/kerala_after_flood.tif')
ds = rasterio.open('data/test_images/kerala_before_flood.tif')
poly = PolygonGenerationService().generate(det['mask_array'], ds.transform, ds.crs.to_wkt())
flood_geom = shape(poly['geojson']['features'][0]['geometry'])

# Let's query OSM for ways with building in the southern wide flood zone (9.63 to 9.67, 76.43 to 76.49)
q = """[out:json][timeout:25];
(
  way["building"](9.63,76.43,9.67,76.49);
);
out geom 500;
"""

req = urllib.request.Request("https://overpass-api.de/api/interpreter", data=q.encode('utf-8'), headers={'User-Agent': 'SatQuery-AI/1.0'})
with urllib.request.urlopen(req, timeout=30) as resp:
    data = json.loads(resp.read().decode('utf-8'))

elements = data.get("elements", [])
print(f"Fetched {len(elements)} raw building elements from OSM.")

features = []
flooded_count = 0

for el in elements:
    pts = [(pt["lon"], pt["lat"]) for pt in el.get("geometry", [])]
    if len(pts) >= 3:
        if pts[0] != pts[-1]:
            pts.append(pts[0])
        p = Polygon(pts)
        if flood_geom.intersects(p):
            flooded_count += 1
        tags = el.get("tags", {})
        features.append({
            "type": "Feature",
            "properties": {
                "building_id": f"OSM_BLD_{el.get('id')}",
                "type": tags.get("building", "residential"),
                "name": tags.get("name", "Building")
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [pts]
            }
        })

print(f"Total features: {len(features)}, intersecting flood: {flooded_count}")
if flooded_count > 0:
    with open("data/buildings/buildings.geojson", "w", encoding="utf-8") as out_f:
        json.dump({"type": "FeatureCollection", "features": features}, out_f, indent=2)
    print("Updated data/buildings/buildings.geojson!")
