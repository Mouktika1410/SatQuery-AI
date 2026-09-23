import urllib.request
import json
import time

rel_id = 11482068 # Aymanam
url = f"https://www.openstreetmap.org/api/0.6/relation/{rel_id}/full.json"

req = urllib.request.Request(url, headers={'User-Agent': 'SatQuery-AI/1.0'})
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        elements = data.get("elements", [])
        nodes = {e["id"]: (e["lon"], e["lat"]) for e in elements if e["type"] == "node"}
        ways = [e for e in elements if e["type"] == "way"]
        print(f"OSM API Success for relation {rel_id}! Nodes: {len(nodes)}, Ways: {len(ways)}")
except Exception as e:
    print("OSM API error:", e)
