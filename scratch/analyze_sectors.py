import sys, json, rasterio
sys.path.insert(0, 'Backend')
from app.services.flood_detection import FloodDetectionService
from app.services.polygon_generation import PolygonGenerationService
from shapely.geometry import shape, box, Polygon, MultiPolygon
from shapely.ops import unary_union
import geopandas as gpd

det = FloodDetectionService().detect('data/test_images/kerala_before_flood.tif', 'data/test_images/kerala_after_flood.tif')
ds = rasterio.open('data/test_images/kerala_before_flood.tif')
poly = PolygonGenerationService().generate(det['mask_array'], ds.transform, ds.crs.to_wkt())
flood_geom = shape(poly['geojson']['features'][0]['geometry'])

print("Flood bounds:", flood_geom.bounds)
# (76.42687004137478, 9.625946627137905, 76.4978346498, 9.732345445174762)

# Let's inspect 3 zones of the flood:
# North-West, North-East, South-Central
# Dividing line around Lat 9.68, and Lon 76.46
minx, miny, maxx, maxy = flood_geom.bounds
midx = 76.462
midy = 9.680

# NW box
nw_box = box(minx - 0.02, midy, midx, maxy + 0.02)
# NE box
ne_box = box(midx, midy, maxx + 0.02, maxy + 0.02)
# South box
s_box = box(minx - 0.02, miny - 0.02, maxx + 0.02, midy)

nw_flood = flood_geom.intersection(nw_box)
ne_flood = flood_geom.intersection(ne_box)
s_flood = flood_geom.intersection(s_box)

# Areas in metric UTM
gdf = gpd.GeoDataFrame([{'geometry': g} for g in [nw_flood, ne_flood, s_flood]], crs="EPSG:4326")
gdf_m = gdf.to_crs(gdf.estimate_utm_crs())
print("NW flood area km2:", gdf_m.geometry.iloc[0].area / 1e6)
print("NE flood area km2:", gdf_m.geometry.iloc[1].area / 1e6)
print("South flood area km2:", gdf_m.geometry.iloc[2].area / 1e6)
print("Total flood area km2:", gdf_m.geometry.area.sum() / 1e6)
