import urllib.request
import json
import time

q = """[out:json][timeout:15];
(
  way["building"](9.64,76.43,9.71,76.49);
);
out geom 100;
"""

req = urllib.request.Request("https://overpass-api.de/api/interpreter", data=q.encode('utf-8'), headers={'User-Agent': 'SatQuery-AI/1.0'})
t0 = time.time()
with urllib.request.urlopen(req, timeout=15) as resp:
    data = json.loads(resp.read().decode('utf-8'))
    elements = data.get("elements", [])
    print(f"Success in {time.time()-t0:.2f}s! Found {len(elements)} real building footprints with geometry.")
