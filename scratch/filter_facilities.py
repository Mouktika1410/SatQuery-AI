import json

with open("scratch/real_facilities.geojson", "r", encoding="utf-8") as f:
    fc = json.load(f)

# Sort features by distance to flood
features = fc.get("features", [])
features.sort(key=lambda x: x["properties"].get("distance_km", 999.0))

# Filter to distinct high-capacity amenities (schools, colleges, hospitals, community centres)
selected = []
seen_names = set()

for feat in features:
    name = feat["properties"].get("name", "")
    p_type = feat["properties"].get("type", "")
    dist = feat["properties"].get("distance_km", 999.0)
    
    # Exclude internal hospital lab wards/blocks to keep distinct public facilities
    if any(b in name.upper() for b in ["BLOCK", "LAB", "PHARMACY", "OP", "CASUALITY", "HOSTEL", "WARD"]):
        continue
    
    clean_key = name.lower()[:15]
    if clean_key in seen_names:
        continue
    seen_names.add(clean_key)
    
    selected.append(feat)
    if len(selected) >= 15:
        break

print(f"Selected {len(selected)} prominent real facilities around Kerala flood perimeter:")
for s in selected:
    p = s["properties"]
    print(f" - {p['name']} ({p['type']}): {p['distance_km']} km away")

with open("data/pois/facilities.geojson", "w", encoding="utf-8") as out_f:
    json.dump({"type": "FeatureCollection", "features": selected}, out_f, indent=2)

print("Saved to data/pois/facilities.geojson!")
