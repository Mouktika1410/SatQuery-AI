import urllib.request
import json

# Query admin boundaries in the Kerala AOI
q = """[out:json][timeout:30];
(
  relation["boundary"="administrative"]["admin_level"~"6|7|8"](9.60,76.40,9.75,76.52);
);
out tags bb;
"""

req = urllib.request.Request(
    'https://overpass-api.de/api/interpreter',
    data=q.encode(),
    headers={'User-Agent': 'SatQuery-AI/1.0'}
)
try:
    with urllib.request.urlopen(req, timeout=35) as resp:
        d = json.loads(resp.read().decode())
        elements = d.get('elements', [])
        print("Admin boundaries count:", len(elements))
        for el in elements:
            tags = el.get('tags', {})
            print(" -", tags.get('name:en') or tags.get('name'), "| admin_level:", tags.get('admin_level'), "| bb:", el.get('bounds'))
except Exception as e:
    print("Error:", e)
