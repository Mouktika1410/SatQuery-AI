"""
Scenario Data Generator for SatQuery — Aligned with Kerala Flood Extent.

Generates supporting GIS datasets
(village boundaries, population polygons, buildings, roads, POIs/facilities, and DEM)
geographically aligned with the Kerala flood detection extent and CRS (EPSG:4326).
"""

import os
import json
import math
import numpy as np

# Bounding box coordinates matching Kerala Sentinel-1 test imagery
# Center approx: 76.46° E, 9.68° N (Kottayam / Vembanad / Kuttanad, Kerala)
MIN_LON, MAX_LON = 76.24989963134911, 76.55083525152915
MIN_LAT, MAX_LAT = 9.34966547711598, 9.750314093833287
WIDTH, HEIGHT = 335, 446


def generate_scenario(base_data_dir: str = "data") -> None:
    """Generate Kerala GIS layers and supporting DEM raster."""
    os.makedirs(base_data_dir, exist_ok=True)
    for sub in ["boundaries", "population", "buildings", "roads", "pois", "dem", "input", "output"]:
        os.makedirs(os.path.join(base_data_dir, sub), exist_ok=True)

    print(f"Generating Kerala scenario datasets into '{base_data_dir}'...")

    # 1. Village Boundaries GeoJSON (Analytical closed polygons for GIS calculations)
    # Covering North-West (Aymanam), North-East (Arpookara), and South-Central (Kumarakom)
    villages_analytical_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "Aymanam Village", "population": 4200, "zone": "North-West"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [76.420, 9.670], [76.455, 9.670], [76.455, 9.735], [76.420, 9.735], [76.420, 9.670]
                    ]]
                }
            },
            {
                "type": "Feature",
                "properties": {"name": "Arpookara Village", "population": 3100, "zone": "North-East"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [76.455, 9.670], [76.505, 9.670], [76.505, 9.735], [76.455, 9.735], [76.455, 9.670]
                    ]]
                }
            },
            {
                "type": "Feature",
                "properties": {"name": "Kumarakom Settlement", "population": 6800, "zone": "South-Central"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [76.420, 9.620], [76.505, 9.620], [76.505, 9.670], [76.420, 9.670], [76.420, 9.620]
                    ]]
                }
            }
        ]
    }
    villages_file = os.path.join(base_data_dir, "boundaries", "villages.geojson")
    if os.path.exists(villages_file) and os.path.getsize(villages_file) > 2000:
        print(" - Preserved real Kerala data/boundaries/villages.geojson")
        return

    # Visual village boundary overlay GeoJSON (Open dashed reference lines for map display)
    villages_visual_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "Aymanam Village", "population": 4200, "zone": "North-West"},
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [76.420, 9.670], [76.455, 9.670], [76.455, 9.735]
                    ]
                }
            },
            {
                "type": "Feature",
                "properties": {"name": "Arpookara Village", "population": 3100, "zone": "North-East"},
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [76.455, 9.670], [76.505, 9.670], [76.505, 9.735]
                    ]
                }
            },
            {
                "type": "Feature",
                "properties": {"name": "Kumarakom Settlement", "population": 6800, "zone": "South-Central"},
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [76.420, 9.670], [76.420, 9.620], [76.505, 9.620], [76.505, 9.670]
                    ]
                }
            }
        ]
    }
    with open(os.path.join(base_data_dir, "boundaries", "villages_visual.geojson"), "w") as f:
        json.dump(villages_visual_geojson, f, indent=2)
    print(" - Created data/boundaries/villages_visual.geojson (open dashed reference overlay)")

    # 2. Population GeoJSON
    pop_file = os.path.join(base_data_dir, "population", "population.geojson")
    with open(pop_file, "w") as f:
        json.dump(villages_analytical_geojson, f, indent=2)
    print(" - Created data/population/population.geojson")

    # 3. Building Footprints GeoJSON (distributed across settlements in the Kerala flood plain)
    buildings_features = []
    np.random.seed(42)
    for i in range(40):
        bx = float(np.random.uniform(76.430, 76.490))
        by = float(np.random.uniform(9.630, 9.720))
        size = 0.002
        buildings_features.append({
            "type": "Feature",
            "properties": {"building_id": f"BLD_{i+1:03d}", "type": "residential"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [bx, by], [bx + size, by], [bx + size, by + size], [bx, by + size], [bx, by]
                ]]
            }
        })
    bld_file = os.path.join(base_data_dir, "buildings", "buildings.geojson")
    with open(bld_file, "w") as f:
        json.dump({"type": "FeatureCollection", "features": buildings_features}, f, indent=2)
    print(f" - Created data/buildings/buildings.geojson ({len(buildings_features)} footprints)")

    # 4. Road Network GeoJSON (Intersects the Kerala flood plain)
    roads_file = os.path.join(base_data_dir, "roads", "roads.geojson")
    roads_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "State Highway 52 (Kumarakom - Kottayam Road)", "highway": "primary"},
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [76.400, 9.635], [76.440, 9.650], [76.475, 9.665], [76.515, 9.680]
                    ]
                }
            },
            {
                "type": "Feature",
                "properties": {"name": "Meenachil River Basin Corridor", "highway": "secondary"},
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [76.435, 9.730], [76.450, 9.690], [76.465, 9.655], [76.495, 9.625]
                    ]
                }
            }
        ]
    }
    with open(roads_file, "w") as f:
        json.dump(roads_geojson, f, indent=2)
    print(" - Created data/roads/roads.geojson")

    # 5. POIs / Candidate Evacuation Facilities (Located on safe, dry ground surrounding Kerala flood zone)
    pois_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "Govt Higher Secondary School Kumarakom", "type": "school", "capacity": 500},
                "geometry": {"type": "Point", "coordinates": [76.415, 9.645]}
            },
            {
                "type": "Feature",
                "properties": {"name": "Aymanam Community Relief Hall", "type": "community_hall", "capacity": 350},
                "geometry": {"type": "Point", "coordinates": [76.418, 9.715]}
            },
            {
                "type": "Feature",
                "properties": {"name": "Kottayam District Civic Shelter", "type": "government", "capacity": 800},
                "geometry": {"type": "Point", "coordinates": [76.510, 9.640]}
            },
            {
                "type": "Feature",
                "properties": {"name": "Arpookara Medical College Primary Centre", "type": "clinic", "capacity": 250},
                "geometry": {"type": "Point", "coordinates": [76.485, 9.742]}
            }
        ]
    }
    pois_file = os.path.join(base_data_dir, "pois", "facilities.geojson")
    with open(pois_file, "w") as f:
        json.dump(pois_geojson, f, indent=2)
    print(" - Created data/pois/facilities.geojson")

    # 6. Generate Synthetic DEM GeoTIFF & Satellite GeoTIFFs (if rasterio is available)
    try:
        import rasterio
        from rasterio.transform import from_bounds
        from rasterio.crs import CRS
        from rasterio.enums import ColorInterp

        transform = from_bounds(MIN_LON, MIN_LAT, MAX_LON, MAX_LAT, WIDTH, HEIGHT)
        crs = CRS.from_epsg(4326)

        grid_y, grid_x = np.ogrid[:HEIGHT, :WIDTH]
        norm_x = grid_x / float(WIDTH - 1)
        norm_y = grid_y / float(HEIGHT - 1)

        # Elevation varies from low near lake/plain (3-8m) rising toward east (25-45m)
        dem_data = (4.0 + 35.0 * norm_x + 8.0 * (1.0 - norm_y)).astype(np.float32)

        dem_path = os.path.join(base_data_dir, "dem", "dem_elevation.tif")
        with rasterio.open(
            dem_path, "w", driver="GTiff", height=HEIGHT, width=WIDTH,
            count=1, dtype=rasterio.float32, crs=crs, transform=transform, nodata=-9999.0
        ) as dst:
            dst.write(dem_data, 1)
        print(" - Created data/dem/dem_elevation.tif")

    except ImportError:
        print(" (rasterio not installed yet — synthetic GeoTIFF generation skipped; vector GeoJSON layers created.)")

    print("\nKerala scenario dataset generation complete.")


if __name__ == "__main__":
    import sys
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "data"
    generate_scenario(data_dir)
