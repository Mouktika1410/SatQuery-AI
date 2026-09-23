import urllib.request
import json

headers = {'User-Agent': 'SatQuery-Disaster-Response/1.0 (contact: support@satquery.org)'}

queries = [
    "Aymanam Grama Panchayat, Kerala",
    "Kumarakom, Kerala",
    "Arpookara, Kerala",
    "Neendoor, Kerala",
    "Kottayam, Kerala"
]

for q in queries:
    url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(q)}&format=geojson&polygon_geojson=1"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            features = data.get("features", [])
            print(f"Query '{q}': found {len(features)} features.")
            if features:
                f0 = features[0]
                print("  Type:", f0["geometry"]["type"], "Props:", f0["properties"].get("display_name"))
    except Exception as e:
        print(f"Query '{q}' failed: {e}")
