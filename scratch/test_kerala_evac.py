import sys, json, rasterio
sys.path.insert(0, 'Backend')
from app.services.flood_detection import FloodDetectionService
from app.services.polygon_generation import PolygonGenerationService
from app.services.evacuation import EvacuationService
from shapely.geometry import shape, Point
import geopandas as gpd

det = FloodDetectionService().detect('data/test_images/kerala_before_flood.tif', 'data/test_images/kerala_after_flood.tif')
ds = rasterio.open('data/test_images/kerala_before_flood.tif')
poly = PolygonGenerationService().generate(det['mask_array'], ds.transform, ds.crs.to_wkt())
flood_geojson = poly['geojson']

facilities = [
    {
        "name": "Govt Higher Secondary School Kumarakom",
        "type": "school",
        "capacity": 500,
        "geometry": Point(76.415, 9.645)
    },
    {
        "name": "Aymanam Community Relief Hall",
        "type": "community_hall",
        "capacity": 350,
        "geometry": Point(76.418, 9.715)
    },
    {
        "name": "Kottayam District Civic Shelter",
        "type": "government",
        "capacity": 800,
        "geometry": Point(76.510, 9.640)
    },
    {
        "name": "Arpookara Medical College Primary Centre",
        "type": "clinic",
        "capacity": 250,
        "geometry": Point(76.485, 9.742)
    }
]

pois_gdf = gpd.GeoDataFrame(facilities, crs="EPSG:4326")

class MockRepo:
    def load_layer(self, layer_type):
        if layer_type in ("pois", "facilities"):
            return pois_gdf
        return None
    def get_dem_path(self):
        return None

evac_res = EvacuationService().find_candidates(flood_geojson, MockRepo(), buffer_m=100.0)
print("Total found:", evac_res["total_found"])
for c in evac_res["candidates"]:
    print(f" - {c['name']} ({c['type']}): distance={c['distance_to_flood_km']} km, lat={c['lat']}, lon={c['lon']}")
