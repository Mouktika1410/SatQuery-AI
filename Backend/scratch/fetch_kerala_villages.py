import urllib.request
import json
import os

# Query Overpass for relation geometries of the administrative divisions in our AOI
query = """[out:json][timeout:60];
(
  relation["boundary"="administrative"]["name"~"Kuttanad|Kottayam|Ambalappuzha|Vaikom|Changanassery|Thiruvalla|Kumarakom|Aimanam"](9.35,76.25,9.75,76.55);
);
out body geom;
"""

url = "https://overpass-api.de/api/interpreter"
req = urllib.request.Request(url, data=query.encode('utf-8'), headers={'User-Agent': 'SatQuery-AI/1.0'})

try:
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        elements = data.get("elements", [])
        print(f"Fetched {len(elements)} relations with geometry.")
        features = []
        for el in elements:
            tags = el.get("tags", {})
            name = tags.get("name") or tags.get("name:en")
            members = el.get("members", [])
            # Collect exterior outer ways to form polygon
            outer_coords = []
            for m in members:
                if m.get("role") == "outer" and "geometry" in m:
                    pts = [(pt["lon"], pt["lat"]) for pt in m["geometry"]]
                    if len(pts) >= 3:
                        outer_coords.append(pts)
            
            if not outer_coords:
                # fallback to element bounds center or combined pts
                all_pts = []
                for m in members:
                    if "geometry" in m:
                        all_pts.extend([(pt["lon"], pt["lat"]) for pt in m["geometry"]])
                if len(all_pts) >= 3:
                    outer_coords = [all_pts[:50]] # sample

            for i, ring in enumerate(outer_coords):
                if len(ring) < 3:
                    continue
                # ensure ring is closed
                if ring[0] != ring[-1]:
                    ring.append(ring[0])
                features.append({
                    "type": "Feature",
                    "properties": {
                        "name": f"{name}" if len(outer_coords) == 1 else f"{name} (Part {i+1})",
                        "admin_level": tags.get("admin_level"),
                        "type": "Administrative Boundary"
                    },
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [ring]
                    }
                })

        geojson = {
            "type": "FeatureCollection",
            "features": features
        }

        output_path = os.path.abspath("../data/boundaries/villages.geojson")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(geojson, f, indent=2)
        print(f"Successfully saved {len(features)} real Kerala administrative village boundaries to {output_path}")

        # Also write visual boundaries
        visual_path = os.path.abspath("../data/boundaries/villages_visual.geojson")
        with open(visual_path, "w", encoding="utf-8") as f:
            json.dump(geojson, f, indent=2)
        print(f"Saved visual copy to {visual_path}")

except Exception as e:
    print("Error:", e)
