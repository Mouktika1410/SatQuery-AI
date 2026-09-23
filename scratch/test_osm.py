import urllib.request
import json

q = """[out:json][timeout:25];
(
  node["amenity"~"school|hospital|community_centre|place_of_worship"](9.60,76.40,9.75,76.52);
);
out body 20;
"""
req = urllib.request.Request(
    'https://overpass-api.de/api/interpreter',
    data=q.encode(),
    headers={'User-Agent': 'SatQuery-AI/1.0'}
)
try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        d = json.loads(resp.read().decode())
        elements = d.get('elements', [])
        print('OSM Overpass test count:', len(elements))
        for el in elements[:5]:
            tags = el.get('tags', {})
            print(" -", tags.get('name', 'Unnamed'), tags.get('amenity'), el.get('lat'), el.get('lon'))
except Exception as e:
    print("Error querying Overpass:", e)
