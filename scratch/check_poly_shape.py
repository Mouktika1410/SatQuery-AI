import sys, rasterio
sys.path.insert(0, 'Backend')
from app.services.flood_detection import FloodDetectionService
from app.services.polygon_generation import PolygonGenerationService
from shapely.geometry import shape

det = FloodDetectionService().detect('data/test_images/kerala_before_flood.tif', 'data/test_images/kerala_after_flood.tif')
ds = rasterio.open('data/test_images/kerala_before_flood.tif')
poly = PolygonGenerationService().generate(det['mask_array'], ds.transform, ds.crs.to_wkt(), simplify_tolerance=0.0001)
feat = poly['geojson']['features'][0]
geom = shape(feat['geometry'])
print('Type:', geom.geom_type)
print('Is valid:', geom.is_valid)
print('Interiors (holes) count:', len(geom.interiors) if geom.geom_type == 'Polygon' else 'N/A')
print('Exterior points count:', len(geom.exterior.coords) if geom.geom_type == 'Polygon' else 'N/A')
print('Bounds:', geom.bounds)
