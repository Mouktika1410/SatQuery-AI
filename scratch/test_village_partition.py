import sys, json, rasterio
sys.path.insert(0, 'Backend')
from app.services.flood_detection import FloodDetectionService
from app.services.polygon_generation import PolygonGenerationService
from shapely.geometry import shape, Polygon, LineString
import geopandas as gpd

det = FloodDetectionService().detect('data/test_images/kerala_before_flood.tif', 'data/test_images/kerala_after_flood.tif')
ds = rasterio.open('data/test_images/kerala_before_flood.tif')
poly = PolygonGenerationService().generate(det['mask_array'], ds.transform, ds.crs.to_wkt())
flood_geom = shape(poly['geojson']['features'][0]['geometry'])
flood_gdf = gpd.GeoDataFrame([{'geometry': flood_geom}], crs="EPSG:4326")

# Let's test a partition:
# Mid lat = 9.670
# For North (above 9.670): split at lon 76.455 into Aymanam (West) and Arpookara (East)
# For South (below 9.670): Kumarakom Settlement from 76.420 to 76.505, lat 9.620 to 9.670

# Let's test analytical polygons:
aymanam_poly = Polygon([
    [76.420, 9.670], [76.455, 9.670], [76.455, 9.735], [76.420, 9.735], [76.420, 9.670]
])

arpookara_poly = Polygon([
    [76.455, 9.670], [76.505, 9.670], [76.505, 9.735], [76.455, 9.735], [76.455, 9.670]
])

kumarakom_poly = Polygon([
    [76.420, 9.620], [76.505, 9.620], [76.505, 9.670], [76.420, 9.670], [76.420, 9.620]
])

villages = [
    {"name": "Aymanam Village", "population": 4200, "zone": "North-West", "geometry": aymanam_poly},
    {"name": "Arpookara Village", "population": 3100, "zone": "North-East", "geometry": arpookara_poly},
    {"name": "Kumarakom Settlement", "population": 6800, "zone": "South-Central", "geometry": kumarakom_poly}
]

v_gdf = gpd.GeoDataFrame(villages, crs="EPSG:4326")
metric_crs = flood_gdf.estimate_utm_crs()

for v in villages:
    inter = flood_geom.intersection(v["geometry"])
    g_m = gpd.GeoSeries([inter], crs="EPSG:4326").to_crs(metric_crs)
    area_km2 = g_m.iloc[0].area / 1e6
    print(f"{v['name']}: {area_km2:.2f} km2 flooded")
