"""
Verification test for PolygonGenerationService smooth organic output.
"""
import sys
import os
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.polygon_generation import PolygonGenerationService
from rasterio.transform import from_bounds

def test_smooth_polygon_generation():
    # Create a synthetic binary mask with stair-step raster pixels
    height, width = 100, 100
    grid_y, grid_x = np.ogrid[:height, :width]
    r = np.sqrt((grid_x - 50)**2 + (grid_y - 50)**2)
    mask = (r < 30).astype(np.uint8)

    transform = from_bounds(72.8, 18.9, 73.0, 19.1, width, height)

    poly_svc = PolygonGenerationService()
    res = poly_svc.generate(mask, transform, "EPSG:4326", simplify_tolerance=0.0001)

    print("Success:", res["success"])
    print("Polygon count:", res["polygon_count"])
    print("Total area km2:", res["total_area_km2"])
    print("GeoJSON feature type:", res["geojson"]["features"][0]["geometry"]["type"])

if __name__ == "__main__":
    test_smooth_polygon_generation()
