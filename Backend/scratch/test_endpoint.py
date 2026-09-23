import os
import sys
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app

client = TestClient(app)

root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
pre_path = os.path.join(root_dir, "data", "test_images", "before_flood.tif")
post_path = os.path.join(root_dir, "data", "test_images", "after_flood.tif")

print("Posting files to /api/v1/flood/image-study...")

with open(pre_path, "rb") as f_pre, open(post_path, "rb") as f_post:
    files = {
        "pre_flood": ("before_flood.tif", f_pre, "image/tiff"),
        "post_flood": ("after_flood.tif", f_post, "image/tiff"),
    }
    response = client.post("/api/v1/flood/image-study", files=files)

print("Response status code:", response.status_code)
assert response.status_code == 200, f"Error: {response.text}"

data = response.json()
print("Success:", data.get("success"))
print("Session ID:", data.get("session_id"))
print("Pre CRS:", data.get("pre_metadata", {}).get("crs"))
print("Post CRS:", data.get("post_metadata", {}).get("crs"))
print("Flood Area km2:", data.get("flood_area_km2"))
print("Polygon count:", data.get("polygon_count"))
print("Centroid:", data.get("centroid"))
print("Bounds:", data.get("bounds"))
print("GeoJSON feature count:", len(data.get("geojson", {}).get("features", [])))
print("First feature geometry type:", data.get("geojson", {}).get("features", [])[0].get("geometry", {}).get("type"))
print("First feature sample coordinate:", data.get("geojson", {}).get("features", [])[0].get("geometry", {}).get("coordinates", [])[0][0][:2])

print("\n--- API Endpoint End-to-End Verification Passed! ---")
