import os, sys, json
sys.path.insert(0, 'Backend')

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

pre_path = "data/test_images/kerala_before_flood.tif"
post_path = "data/test_images/kerala_after_flood.tif"

assert os.path.exists(pre_path), f"Missing {pre_path}"
assert os.path.exists(post_path), f"Missing {post_path}"

with open(pre_path, "rb") as f_pre, open(post_path, "rb") as f_post:
    files = {
        "pre_flood": ("kerala_before_flood.tif", f_pre, "image/tiff"),
        "post_flood": ("kerala_after_flood.tif", f_post, "image/tiff"),
    }
    data = {
        "method": "auto",
        "sar_polarization": "auto",
        "simplify_tolerance": 0.0001,
        "buffer_m": 100.0,
    }
    response = client.post("/api/v1/flood/pipeline", files=files, data=data)

print(f"Status Code: {response.status_code}")
if response.status_code != 200:
    print("Error:", response.text)
    sys.exit(1)

res = response.json()

print("\n--- VALIDATION ---")
val = res.get("validation", {})
print("Compatible:", val.get("compatible"))
print("Pre dimensions:", val.get("pre_flood", {}).get("width"), "x", val.get("pre_flood", {}).get("height"))

print("\n--- DETECTION ---")
det = res.get("detection", {})
print("Success:", det.get("success"))
print("Method used:", det.get("method_used"))
print("Flooded area (km2):", det.get("flood_area_km2"))
print("Flood percentage:", det.get("flood_percentage"))

print("\n--- POLYGONS ---")
poly = res.get("polygons", {})
print("Success:", poly.get("success"))
print("Polygon count:", poly.get("polygon_count"))
print("Total polygon area (km2):", poly.get("total_area_km2"))
geo = poly.get("geojson", {})
print("GeoJSON features count:", len(geo.get("features", [])))
if geo.get("features"):
    feat0 = geo["features"][0]
    coords = feat0["geometry"]["coordinates"][0]
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    print(f"Flood bounds: Lon [{min(lons):.4f}, {max(lons):.4f}], Lat [{min(lats):.4f}, {max(lats):.4f}]")

print("\n--- IMPACT ANALYSIS ---")
impact = res.get("impact", {})
print("Affected population:", impact.get("affected_population"))
print("Affected buildings:", impact.get("affected_buildings"))
print("Affected road length (km):", impact.get("affected_road_length_km"))
print("Affected villages count:", len(impact.get("affected_villages", [])))
for v in impact.get("affected_villages", []):
    print(f" - {v.get('name')}: {v.get('area_flooded_km2')} km2, pop={v.get('population_affected')}")

print("\n--- AFFECTED VILLAGES GEOJSON ---")
v_geo = impact.get("affected_villages_geojson")
if v_geo and v_geo.get("features"):
    print(f"Villages GeoJSON has {len(v_geo['features'])} features (visual overlay ready!)")
    for vf in v_geo["features"]:
        print(f" - {vf['properties'].get('name')}: geom type = {vf['geometry']['type']}")
else:
    print("WARNING: affected_villages_geojson is empty or None!")

print("\n--- AFFECTED ROADS GEOJSON ---")
r_geo = impact.get("affected_roads_geojson")
if r_geo and r_geo.get("features"):
    print(f"Roads GeoJSON has {len(r_geo['features'])} features (corridors ready!)")
    for rf in r_geo["features"]:
        print(f" - {rf['properties'].get('name')}: geom type = {rf['geometry']['type']}")
else:
    print("WARNING: affected_roads_geojson is empty or None!")

print("\n--- PRIORITY SCORES ---")
priority = res.get("priority_scores", [])
print(f"Priority scores count: {len(priority)}")
for p in priority:
    print(f" - Rank #{p.get('rank')}: {p.get('village_name')} (score={p.get('priority_score')})")

print("\n--- EVACUATION CANDIDATES & ROUTES ---")
evac = res.get("evacuation", {})
candidates = evac.get("candidates", [])
print(f"Evacuation candidates found: {len(candidates)}")
for c in candidates:
    has_route = c.get("route_geojson") is not None
    pts = len(c["route_geojson"]["geometry"]["coordinates"]) if has_route else 0
    print(f" - {c.get('name')} ({c.get('type')}): dist={c.get('distance_to_flood_km')} km, route_km={c.get('route_distance_km')}, origin={c.get('origin_name')}, route_pts={pts}")

# Check bounding box of all layers together
all_lats = []
all_lons = []
if geo.get("features"):
    for pt in coords:
        all_lons.append(pt[0])
        all_lats.append(pt[1])
for c in candidates:
    if c.get("lat") and c.get("lon"):
        all_lats.append(c["lat"])
        all_lons.append(c["lon"])

print(f"\n--- COMBINED BOUNDS SPAN ---")
print(f"Lat: {min(all_lats):.4f} to {max(all_lats):.4f} (span: {max(all_lats) - min(all_lats):.4f} deg = {(max(all_lats) - min(all_lats))*111:.1f} km)")
print(f"Lon: {min(all_lons):.4f} to {max(all_lons):.4f} (span: {max(all_lons) - min(all_lons):.4f} deg = {(max(all_lons) - min(all_lons))*111*0.98:.1f} km)")
