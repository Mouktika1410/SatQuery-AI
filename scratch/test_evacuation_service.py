import json
import sys
import os
sys.path.insert(0, os.path.abspath('Backend'))
import geopandas as gpd
from shapely.geometry import Point, Polygon
from app.services.evacuation import EvacuationService
from app.services.gis_repository import GISRepository

repo = GISRepository("data")

# Load real Kerala flood sample
with open("data/boundaries/villages.geojson") as f:
    v_data = json.load(f)

# Use Kallara geometry as simulated flood polygon
kallara_feat = [f for f in v_data["features"] if "Kallara" in f["properties"].get("name", "")][0]
sim_flood_geojson = {
    "type": "FeatureCollection",
    "features": [kallara_feat]
}

svc = EvacuationService()
res = svc.find_candidates(sim_flood_geojson, repo, buffer_m=100.0)

print(f"Total candidates found: {res['total_found']}")
for c in res['candidates'][:5]:
    print(f"Candidate: {c['name']}")
    print(f"  Type: {c['type']}")
    print(f"  Distance to flood: {c['distance_to_flood_km']} km")
    print(f"  Route distance: {c.get('route_distance_km')} km")
    print(f"  Origin: {c.get('origin_name')}")
    print(f"  Route GeoJSON present: {c.get('route_geojson') is not None}")
    if c.get('route_geojson'):
        coords = c['route_geojson']['geometry']['coordinates']
        print(f"  Route points count: {len(coords)}")
