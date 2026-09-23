import urllib.request
import json

q = """[out:json][timeout:25];
(
  relation["boundary"="local_authority"]["name"~"Kallara|Neendoor|Aymanam|Kumarakom"](9.50,76.35,9.76,76.55);
);
out ids tags;
"""

for base_url in ["https://overpass.kumi.systems/api/interpreter", "https://overpass-api.de/api/interpreter"]:
    try:
        req = urllib.request.Request(base_url, data=q.encode('utf-8'), headers={'User-Agent': 'SatQuery-AI/1.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            print(f"Success from {base_url}!")
            for el in data.get("elements", []):
                print("ID:", el["id"], "Tags:", el.get("tags", {}).get("name:en") or el.get("tags", {}).get("name"))
            break
    except Exception as e:
        print(f"Failed {base_url}: {e}")
