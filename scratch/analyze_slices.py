import sys, json, rasterio
sys.path.insert(0, 'Backend')
from app.services.flood_detection import FloodDetectionService
from app.services.polygon_generation import PolygonGenerationService
from shapely.geometry import shape, box, Polygon, MultiPolygon
import numpy as np

det = FloodDetectionService().detect('data/test_images/kerala_before_flood.tif', 'data/test_images/kerala_after_flood.tif')
ds = rasterio.open('data/test_images/kerala_before_flood.tif')
poly = PolygonGenerationService().generate(det['mask_array'], ds.transform, ds.crs.to_wkt())
flood_geom = shape(poly['geojson']['features'][0]['geometry'])

# Let's inspect 5 latitude slices from South (9.626) to North (9.732)
lats = np.linspace(9.626, 9.732, 6)
for i in range(len(lats)-1):
    slice_box = box(76.40, lats[i], 76.52, lats[i+1])
    inter = flood_geom.intersection(slice_box)
    if not inter.is_empty:
        bounds = inter.bounds
        print(f"Lat slice {lats[i]:.3f} to {lats[i+1]:.3f}: Lon range [{bounds[0]:.4f}, {bounds[2]:.4f}], area deg2 {inter.area:.6f}")
