import urllib.request
import json

mirrors = [
    "https://overpass.private.coffee/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter"
]

q = """[out:json][timeout:15];
(
  node["amenity"~"school|hospital|community_centre"](9.62,76.41,9.74,76.51);
);
out body 10;
"""

for m in mirrors:
    try:
        req = urllib.request.Request(m, data=q.encode('utf-8'), headers={'User-Agent': 'SatQuery-AI/1.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            elements = data.get("elements", [])
            print(f"Mirror {m} works! Returned {len(elements)} elements.")
            for el in elements[:3]:
                print(" -", el.get("tags", {}).get("name"), el.get("lat"), el.get("lon"))
            break
    except Exception as e:
        print(f"Mirror {m} failed: {e}")
