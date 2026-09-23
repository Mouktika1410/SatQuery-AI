import os
import json
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon
from shapely.validation import make_valid
from shapely.ops import unary_union, polygonize

input_path = os.path.abspath("../data/boundaries/villages.geojson")
gdf = gpd.read_file(input_path)
print("Initial feature count:", len(gdf))

clean_features = []

for name, group in gdf.groupby("name"):
    base_name = name.split(" (")[0]
    valid_geoms = []
    for g in group.geometry.values:
        if g is None or g.is_empty:
            continue
        try:
            vg = make_valid(g)
            if not vg.is_empty:
                valid_geoms.append(vg)
        except Exception:
            pass
    
    if not valid_geoms:
        continue

    try:
        union_geom = unary_union(valid_geoms)
    except Exception:
        union_geom = valid_geoms[0]

    if not isinstance(union_geom, (Polygon, MultiPolygon)):
        try:
            polys = list(polygonize(union_geom))
            if polys:
                union_geom = unary_union(polys)
        except Exception:
            pass

    if union_geom.is_empty:
        continue

    clean_features.append({
        "type": "Feature",
        "properties": {
            "name": base_name,
            "type": "Administrative Village Division",
            "state": "Kerala"
        },
        "geometry": union_geom.__geo_interface__
    })

clean_gdf = gpd.GeoDataFrame.from_features(clean_features, crs="EPSG:4326")
print("Cleaned administrative village divisions count:", len(clean_gdf))

for idx, row in clean_gdf.iterrows():
    print(f" - {row['name']}: {row.geometry.geom_type}")

out_path = os.path.abspath("../data/boundaries/villages.geojson")
clean_gdf.to_file(out_path, driver="GeoJSON")
clean_gdf.to_file(os.path.abspath("../data/boundaries/villages_visual.geojson"), driver="GeoJSON")
print("Saved clean polygon GeoJSON to data/boundaries/villages.geojson")
