import urllib.request
import json

overpass_url = "https://lz4.overpass-api.de/api/interpreter"

# 1. Fetch real roads
q_roads = """[out:json][timeout:30];
(
  way["highway"~"primary|secondary|tertiary|trunk|motorway"](9.60,76.40,9.75,76.52);
);
out body;
>;
out skel qt;
"""

print("Fetching real Kerala roads...")
req = urllib.request.Request(overpass_url, data=q_roads.encode(), headers={'User-Agent': 'SatQuery-AI/1.0'})
with urllib.request.urlopen(req, timeout=30) as resp:
    data = json.loads(resp.read().decode('utf-8'))
    elements = data.get("elements", [])
    nodes = {e["id"]: (e["lon"], e["lat"]) for e in elements if e["type"] == "node"}
    ways = [e for e in elements if e["type"] == "way"]
    print(f"Success! {len(ways)} real roads and {len(nodes)} nodes.")

# 2. Fetch real facilities
q_pois = """[out:json][timeout:30];
(
  node["amenity"~"school|hospital|clinic|community_centre|place_of_worship|college|townhall"](9.60,76.40,9.75,76.52);
);
out body;
"""
print("Fetching real Kerala POIs/facilities...")
req2 = urllib.request.Request(overpass_url, data=q_pois.encode(), headers={'User-Agent': 'SatQuery-AI/1.0'})
with urllib.request.urlopen(req2, timeout=30) as resp:
    data2 = json.loads(resp.read().decode('utf-8'))
    pois = data2.get("elements", [])
    print(f"Success! {len(pois)} real Kerala POIs/facilities found.")

# 3. Fetch real buildings
q_bld = """[out:json][timeout:30];
(
  way["building"](9.66,76.44,9.70,76.49);
);
out body;
>;
out skel qt;
"""
print("Fetching real Kerala buildings...")
req3 = urllib.request.Request(overpass_url, data=q_bld.encode(), headers={'User-Agent': 'SatQuery-AI/1.0'})
with urllib.request.urlopen(req3, timeout=30) as resp:
    data3 = json.loads(resp.read().decode('utf-8'))
    bld_elements = data3.get("elements", [])
    bld_ways = [e for e in bld_elements if e["type"] == "way"]
    print(f"Success! {len(bld_ways)} real Kerala building footprints found.")
