import sys
import rasterio
sys.path.insert(0, 'Backend')
from app.services.flood_detection import FloodDetectionService
from app.services.polygon_generation import PolygonGenerationService
from shapely.geometry import shape

det = FloodDetectionService().detect('data/test_images/kerala_before_flood.tif', 'data/test_images/kerala_after_flood.tif')
ds = rasterio.open('data/test_images/kerala_before_flood.tif')
poly = PolygonGenerationService().generate(det['mask_array'], ds.transform, ds.crs.to_wkt())
geom = shape(poly['geojson']['features'][0]['geometry'])
print('Flood bounds:', geom.bounds)
print('Centroid:', geom.centroid.x, geom.centroid.y)
print('Area (deg^2):', geom.area)
print('Area (km2):', poly['total_area_km2'])

minx, miny, maxx, maxy = geom.bounds
midx, midy = (minx + maxx) / 2, (miny + maxy) / 2
print(f'West-East: {minx:.4f} -> {midx:.4f} -> {maxx:.4f}')
print(f'South-North: {miny:.4f} -> {midy:.4f} -> {maxy:.4f}')
