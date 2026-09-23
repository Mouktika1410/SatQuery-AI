import urllib.request
import json
import urllib.parse

headers = {'User-Agent': 'SatQuery-Disaster-Response/1.0 (contact: support@satquery.org)'}

queries = [
    "Kottayam Taluk",
    "Kuttanad Taluk",
    "Vaikom Taluk",
    "Meenachil Taluk",
    "Changanassery Taluk",
    "Aymanam, Kottayam",
    "Kumarakom Grama Panchayat",
    "Kallara, Kottayam"
]

for q in queries:
    url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(q)}&format=geojson&polygon_geojson=1"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            features = data.get("features", [])
            print(f"Query '{q}': found {len(features)} features.")
            for f in features:
                if f["geometry"]["type"] in ("Polygon", "MultiPolygon"):
                    print("  -> POLYGON found:", f["properties"].get("display_name"))
    except Exception as e:
        print(f"Query '{q}' failed: {e}")
