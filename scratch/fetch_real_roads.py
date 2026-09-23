import urllib.request
import json

# Roads in the flood area
q_roads = """[out:json][timeout:25];
(
  way["highway"~"primary|secondary|tertiary|trunk"](9.60,76.40,9.75,76.52);
);
out body;
>;
out skel qt;
"""

req = urllib.request.Request(
    'https://overpass-api.de/api/interpreter',
    data=q_roads.encode('utf-8'),
    headers={'User-Agent': 'SatQuery-AI/1.0'}
)

try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        elements = data.get("elements", [])
        nodes = {e["id"]: (e["lon"], e["lat"]) for e in elements if e["type"] == "node"}
        ways = [e for e in elements if e["type"] == "way"]
        print(f"Road ways found: {len(ways)}, nodes: {len(nodes)}")
        for w in ways[:10]:
            tags = w.get("tags", {})
            print(" -", tags.get("name") or tags.get("ref", "unnamed road"), "| highway:", tags.get("highway"))
except Exception as e:
    print("Road fetch error:", e)
