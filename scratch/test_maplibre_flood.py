import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Backend'))

from app.services.flood_detection import FloodDetectionService
from app.services.polygon_generation import PolygonGenerationService
import rasterio

data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))
pre_path = os.path.join(data_dir, 'test_images', 'kerala_before_flood.tif')
post_path = os.path.join(data_dir, 'test_images', 'kerala_after_flood.tif')

det_svc = FloodDetectionService()
det_res = det_svc.detect(pre_path, post_path, {"method": "auto"})
mask_array = det_res.get("mask_array")

with rasterio.open(pre_path) as ds:
    transform = ds.transform
    crs_wkt = ds.crs.to_wkt() if ds.crs else "EPSG:4326"

poly_svc = PolygonGenerationService()
poly_res = poly_svc.generate(mask_array, transform, crs_wkt, 0.0001)
flood_geojson = poly_res.get("geojson")

print("Type of flood_geojson:", type(flood_geojson))
print("Keys:", flood_geojson.keys() if isinstance(flood_geojson, dict) else "not dict")
print("Features count:", len(flood_geojson.get("features", [])))
f0 = flood_geojson["features"][0]
print("Feature 0 geometry type:", f0.get("geometry", {}).get("type"))
coords = f0.get("geometry", {}).get("coordinates")
print("Coordinates depth:", len(coords))
if coords and len(coords) > 0:
    print("Ring 0 length:", len(coords[0]))
    print("Sample coord 0:", coords[0][0])
    print("Sample coord 1:", coords[0][1])
    print("Sample coord -1:", coords[0][-1])

with open("scratch/sample_flood.geojson", "w") as f:
    json.dump(flood_geojson, f)
print("Saved to scratch/sample_flood.geojson")
