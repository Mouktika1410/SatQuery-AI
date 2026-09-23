import sys, json, rasterio
sys.path.insert(0, 'Backend')
from app.services.flood_detection import FloodDetectionService
from app.services.polygon_generation import PolygonGenerationService
from shapely.geometry import shape, LineString
import geopandas as gpd

det = FloodDetectionService().detect('data/test_images/kerala_before_flood.tif', 'data/test_images/kerala_after_flood.tif')
ds = rasterio.open('data/test_images/kerala_before_flood.tif')
poly = PolygonGenerationService().generate(det['mask_array'], ds.transform, ds.crs.to_wkt())
flood_geom = shape(poly['geojson']['features'][0]['geometry'])
flood_gdf = gpd.GeoDataFrame([{'geometry': flood_geom}], crs="EPSG:4326")

roads = [
    {
        "name": "State Highway 52 (Kumarakom - Kottayam Road)",
        "highway": "primary",
        "geometry": LineString([
            [76.400, 9.635], [76.440, 9.650], [76.475, 9.665], [76.515, 9.680]
        ])
    },
    {
        "name": "Meenachil River Basin Corridor",
        "highway": "secondary",
        "geometry": LineString([
            [76.435, 9.730], [76.450, 9.690], [76.465, 9.655], [76.495, 9.625]
        ])
    }
]

roads_gdf = gpd.GeoDataFrame(roads, crs="EPSG:4326")
clipped = gpd.clip(roads_gdf, flood_gdf)
print("Clipped features count:", len(clipped))
metric_crs = flood_gdf.estimate_utm_crs()
clipped_m = clipped.to_crs(metric_crs)
total_km = clipped_m.geometry.length.sum() / 1000.0
print(f"Total inundated road length: {total_km:.2f} km")
for idx, row in clipped_m.iterrows():
    print(f" - {row['name']}: {row.geometry.length / 1000.0:.2f} km")
