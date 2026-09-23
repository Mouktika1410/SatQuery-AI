import urllib.request
import json
import time

q = """[out:json][timeout:15];
(
  way["highway"~"primary|secondary|trunk"](9.62,76.42,9.72,76.50);
);
out geom;
"""

mirrors = [
    "https://overpass-api.de/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter"
]

for m in mirrors:
    try:
        req = urllib.request.Request(m, data=q.encode('utf-8'), headers={'User-Agent': 'SatQuery-AI/1.0'})
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            elements = data.get("elements", [])
            print(f"Success from {m} in {time.time()-t0:.2f}s! Found {len(elements)} real road ways with geometry.")
            for el in elements[:5]:
                tags = el.get("tags", {})
                print(" -", tags.get("name") or tags.get("ref"), "| highway:", tags.get("highway"), "| pts:", len(el.get("geometry", [])))
            break
    except Exception as e:
        print(f"Failed {m}: {e}")
