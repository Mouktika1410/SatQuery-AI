import sys, json, rasterio
sys.path.insert(0, 'Backend')
from app.services.flood_detection import FloodDetectionService
from app.services.polygon_generation import PolygonGenerationService
from shapely.geometry import shape, Polygon
import geopandas as gpd

det = FloodDetectionService().detect('data/test_images/kerala_before_flood.tif', 'data/test_images/kerala_after_flood.tif')
ds = rasterio.open('data/test_images/kerala_before_flood.tif')
poly = PolygonGenerationService().generate(det['mask_array'], ds.transform, ds.crs.to_wkt())
flood_geom = shape(poly['geojson']['features'][0]['geometry'])
flood_gdf = gpd.GeoDataFrame([{'geometry': flood_geom}], crs="EPSG:4326")

with open('scratch/build_real_kerala_panchayats.py') as f:
    # let's run the builder to get features
    pass

import scratch.build_real_kerala_panchayats as builder

v_gdf = gpd.GeoDataFrame.from_features(builder.features, crs="EPSG:4326")
metric_crs = flood_gdf.estimate_utm_crs()
flood_m = flood_gdf.to_crs(metric_crs)
v_m = v_gdf.to_crs(metric_crs)

print(f"Total flood area: {flood_m.geometry.iloc[0].area / 1e6:.2f} km2\n")

for idx, row in v_m.iterrows():
    inter = flood_m.geometry.iloc[0].intersection(row.geometry)
    if not inter.is_empty:
        area_km2 = inter.area / 1e6
        print(f" - {row['name']} ({row['zone']}): {area_km2:.2f} km2 flooded")
