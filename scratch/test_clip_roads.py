import geopandas as gpd
import rasterio
import sys
sys.path.insert(0, 'Backend')
from app.services.flood_detection import FloodDetectionService
from app.services.polygon_generation import PolygonGenerationService
from shapely.geometry import shape

det = FloodDetectionService().detect('data/test_images/kerala_before_flood.tif', 'data/test_images/kerala_after_flood.tif')
ds = rasterio.open('data/test_images/kerala_before_flood.tif')
poly = PolygonGenerationService().generate(det['mask_array'], ds.transform, ds.crs.to_wkt())
flood_gdf = gpd.GeoDataFrame([{'geometry': shape(poly['geojson']['features'][0]['geometry'])}], crs='EPSG:4326')

roads_gdf = gpd.read_file('scratch/real_roads.geojson')
clipped = gpd.clip(roads_gdf, flood_gdf)
print('Real roads clipped features count:', len(clipped))
metric_crs = flood_gdf.estimate_utm_crs()
clipped_m = clipped.to_crs(metric_crs)
total_km = clipped_m.geometry.length.sum() / 1000.0
print(f'Total inundated real road length: {total_km:.2f} km')
for idx, r in clipped.head(5).iterrows():
    print(f" - {r.get('name')}: highway={r.get('highway')}")
