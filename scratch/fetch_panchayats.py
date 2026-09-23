import urllib.request
import json

q = """[out:json][timeout:30];
(
  relation["name"~"Aimanam|Aymanam|Kumarakom|Arpookara|Thiruvarpu|Kottayam|Neendoor|Pulinkunnoo"](9.35,76.25,9.75,76.55);
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
        print("Count:", len(elements))
        for el in elements:
            tags = el.get('tags', {})
            print(" -", tags.get('name:en') or tags.get('name'), "| boundary:", tags.get('boundary'), "| admin_level:", tags.get('admin_level'), "| bb:", el.get('bounds'))
except Exception as e:
    print("Error:", e)
