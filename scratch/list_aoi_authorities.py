import urllib.request
import json

q = """[out:json][timeout:20];
(
  relation["boundary"="local_authority"](9.55,76.38,9.75,76.53);
);
out geom;
"""

req = urllib.request.Request("https://overpass-api.de/api/interpreter", data=q.encode('utf-8'), headers={'User-Agent': 'SatQuery-AI/1.0'})
with urllib.request.urlopen(req, timeout=20) as resp:
    data = json.loads(resp.read().decode('utf-8'))
    elements = data.get("elements", [])
    print(f"Total local authorities in AOI: {len(elements)}")
    for el in elements:
        tags = el.get("tags", {})
        print(" -", tags.get("name:en") or tags.get("name"), "| admin_level:", tags.get("admin_level"), "| members:", len(el.get("members", [])))
