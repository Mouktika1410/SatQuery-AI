import urllib.request
import json
import time

q = """[out:json][timeout:20];
(
  relation["boundary"="local_authority"]["name"~"Kallara|Neendoor|Aymanam|Kumarakom"](9.50,76.35,9.76,76.55);
);
out geom;
"""

req = urllib.request.Request("https://overpass-api.de/api/interpreter", data=q.encode('utf-8'), headers={'User-Agent': 'SatQuery-AI/1.0'})
t0 = time.time()
with urllib.request.urlopen(req, timeout=20) as resp:
    data = json.loads(resp.read().decode('utf-8'))
    elements = data.get("elements", [])
    print(f"Success in {time.time()-t0:.2f}s! Found {len(elements)} relations with geometry.")
    for el in elements:
        tags = el.get("tags", {})
        print(" -", tags.get("name:en") or tags.get("name"), "| members:", len(el.get("members", [])))
