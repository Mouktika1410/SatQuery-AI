import sys, os, json, rasterio
import numpy as np
import geopandas as gpd
from shapely.geometry import shape, box, Polygon, LineString, Point

sys.path.insert(0, 'Backend')
from app.services.flood_detection import FloodDetectionService
from app.services.polygon_generation import PolygonGenerationService
from app.services.exposure_analysis import ExposureAnalysisService
from app.services.impact_scoring import ImpactScoringService
from app.services.evacuation import EvacuationService
from app.services.gis_repository import GISRepository

# 1. Detect flood from real Kerala images
det = FloodDetectionService().detect('data/test_images/kerala_before_flood.tif', 'data/test_images/kerala_after_flood.tif')
ds = rasterio.open('data/test_images/kerala_before_flood.tif')
poly = PolygonGenerationService().generate(det['mask_array'], ds.transform, ds.crs.to_wkt())
flood_geojson = poly['geojson']
flood_geom = shape(flood_geojson['features'][0]['geometry'])

print(f"Detected flood polygon: {poly['total_area_km2']:.2f} km2, bounds={flood_geom.bounds}")

# 2. Build Kerala Village boundaries (analytical)
villages_analytical = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"name": "Aymanam Village", "population": 4200, "zone": "North-West"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [76.420, 9.670], [76.455, 9.670], [76.455, 9.735], [76.420, 9.735], [76.420, 9.670]
                ]]
            }
        },
        {
            "type": "Feature",
            "properties": {"name": "Arpookara Village", "population": 3100, "zone": "North-East"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [76.455, 9.670], [76.505, 9.670], [76.505, 9.735], [76.455, 9.735], [76.455, 9.670]
                ]]
            }
        },
        {
            "type": "Feature",
            "properties": {"name": "Kumarakom Settlement", "population": 6800, "zone": "South-Central"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [76.420, 9.620], [76.505, 9.620], [76.505, 9.670], [76.420, 9.670], [76.420, 9.620]
                ]]
            }
        }
    ]
}

# 3. Build Kerala Visual Village boundary overlay (open dashed lines)
villages_visual = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"name": "Aymanam Village", "population": 4200, "zone": "North-West"},
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [76.420, 9.670], [76.455, 9.670], [76.455, 9.735]
                ]
            }
        },
        {
            "type": "Feature",
            "properties": {"name": "Arpookara Village", "population": 3100, "zone": "North-East"},
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [76.455, 9.670], [76.505, 9.670], [76.505, 9.735]
                ]
            }
        },
        {
            "type": "Feature",
            "properties": {"name": "Kumarakom Settlement", "population": 6800, "zone": "South-Central"},
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [76.420, 9.670], [76.420, 9.620], [76.505, 9.620], [76.505, 9.670]
                ]
            }
        }
    ]
}

# 4. Roads GeoJSON
roads_geojson = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"name": "State Highway 52 (Kumarakom - Kottayam Road)", "highway": "primary"},
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [76.400, 9.635], [76.440, 9.650], [76.475, 9.665], [76.515, 9.680]
                ]
            }
        },
        {
            "type": "Feature",
            "properties": {"name": "Meenachil River Basin Corridor", "highway": "secondary"},
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [76.435, 9.730], [76.450, 9.690], [76.465, 9.655], [76.495, 9.625]
                ]
            }
        }
    ]
}

# 5. POIs / Facilities GeoJSON
pois_geojson = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"name": "Govt Higher Secondary School Kumarakom", "type": "school", "capacity": 500},
            "geometry": {"type": "Point", "coordinates": [76.415, 9.645]}
        },
        {
            "type": "Feature",
            "properties": {"name": "Aymanam Community Relief Hall", "type": "community_hall", "capacity": 350},
            "geometry": {"type": "Point", "coordinates": [76.418, 9.715]}
        },
        {
            "type": "Feature",
            "properties": {"name": "Kottayam District Civic Shelter", "type": "government", "capacity": 800},
            "geometry": {"type": "Point", "coordinates": [76.510, 9.640]}
        },
        {
            "type": "Feature",
            "properties": {"name": "Arpookara Medical College Primary Centre", "type": "clinic", "capacity": 250},
            "geometry": {"type": "Point", "coordinates": [76.485, 9.742]}
        }
    ]
}

# 6. Buildings GeoJSON (40 residential footprints in the Kerala region)
buildings_features = []
np.random.seed(42)
for i in range(40):
    bx = float(np.random.uniform(76.430, 76.490))
    by = float(np.random.uniform(9.630, 9.720))
    size = 0.002
    buildings_features.append({
        "type": "Feature",
        "properties": {"building_id": f"BLD_{i+1:03d}", "type": "residential"},
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [bx, by], [bx + size, by], [bx + size, by + size], [bx, by + size], [bx, by]
            ]]
        }
    })
buildings_geojson = {"type": "FeatureCollection", "features": buildings_features}

# Test GIS Repo
class KeralaGISRepo:
    def load_layer(self, layer_type):
        if layer_type == "villages":
            return gpd.GeoDataFrame.from_features(villages_analytical["features"], crs="EPSG:4326")
        if layer_type == "villages_visual":
            return gpd.GeoDataFrame.from_features(villages_visual["features"], crs="EPSG:4326")
        if layer_type == "population":
            return gpd.GeoDataFrame.from_features(villages_analytical["features"], crs="EPSG:4326")
        if layer_type == "roads":
            return gpd.GeoDataFrame.from_features(roads_geojson["features"], crs="EPSG:4326")
        if layer_type in ("pois", "facilities"):
            return gpd.GeoDataFrame.from_features(pois_geojson["features"], crs="EPSG:4326")
        if layer_type == "buildings":
            return gpd.GeoDataFrame.from_features(buildings_geojson["features"], crs="EPSG:4326")
        return None
    def get_dem_path(self):
        return None

repo = KeralaGISRepo()
exposure = ExposureAnalysisService().calculate_exposure(flood_geojson, "test_session", repo)
print("\n--- EXPOSURE ANALYSIS ---")
print("Affected population:", exposure.get("affected_population"))
print("Affected buildings:", exposure.get("affected_buildings"))
print("Affected road length km:", exposure.get("affected_road_length_km"))
print("Affected villages count:", len(exposure.get("affected_villages", [])))
for v in exposure.get("affected_villages", []):
    print(f" - {v['name']}: {v['area_flooded_km2']} km2")

print("\n--- PRIORITY SCORES ---")
priority = ImpactScoringService().compute_priority_scores(exposure)
for p in priority:
    print(f" - Rank #{p['rank']}: {p['village_name']} (score={p['priority_score']:.4f})")

print("\n--- EVACUATION CANDIDATES ---")
evac = EvacuationService().find_candidates(flood_geojson, repo, buffer_m=100.0)
print(f"Candidates found: {evac['total_found']}")
for c in evac["candidates"]:
    print(f" - {c['name']} ({c['type']}): distance={c['distance_to_flood_km']} km, lat={c['lat']}, lon={c['lon']}")
