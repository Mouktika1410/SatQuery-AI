"""
Sample Scenario Data Generator for SatQuery.

Generates synthetic georeferenced Sentinel-like imagery and supporting GIS datasets
(village boundaries, population grid/polygons, buildings, roads, POIs, and DEM)
for testing the end-to-end flood disaster analysis workflow.

All generated coordinates are centered around a sample flood plain in Maharashtra/Gujarat, India.
"""

import os
import json
import math
import numpy as np

# Bounding box coordinates (WGS84)
# Center approx: 72.9° E, 19.0° N
MIN_LON, MAX_LON = 72.80, 73.00
MIN_LAT, MAX_LAT = 18.90, 19.10
WIDTH, HEIGHT = 200, 200


def generate_scenario(base_data_dir: str = "data") -> None:
    """Generate sample GIS layers and synthetic pre/post GeoTIFFs."""
    os.makedirs(base_data_dir, exist_ok=True)
    for sub in ["boundaries", "population", "buildings", "roads", "pois", "dem", "input", "output"]:
        os.makedirs(os.path.join(base_data_dir, sub), exist_ok=True)

    print(f"Generating synthetic scenario datasets into '{base_data_dir}'...")

    # 1. Generate Village Boundaries GeoJSON
    villages_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "Navapur Village", "population": 4200, "zone": "North"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [72.82, 19.02], [72.90, 19.02], [72.90, 19.08], [72.82, 19.08], [72.82, 19.02]
                    ]]
                }
            },
            {
                "type": "Feature",
                "properties": {"name": "Kalyanpur Settlement", "population": 6800, "zone": "Central"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [72.88, 18.94], [72.96, 18.94], [72.96, 19.02], [72.88, 19.02], [72.88, 18.94]
                    ]]
                }
            },
            {
                "type": "Feature",
                "properties": {"name": "Shivaji Nagar", "population": 3100, "zone": "East"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [72.92, 19.02], [72.98, 19.02], [72.98, 19.08], [72.92, 19.08], [72.92, 19.02]
                    ]]
                }
            }
        ]
    }
    with open(os.path.join(base_data_dir, "boundaries", "villages.geojson"), "w") as f:
        json.dump(villages_geojson, f, indent=2)
    print(" - Created data/boundaries/villages.geojson")

    # 2. Generate Population GeoJSON
    with open(os.path.join(base_data_dir, "population", "population.geojson"), "w") as f:
        json.dump(villages_geojson, f, indent=2)
    print(" - Created data/population/population.geojson")

    # 3. Generate Building Footprints GeoJSON
    buildings_features = []
    np.random.seed(42)
    for i in range(40):
        bx = np.random.uniform(72.84, 72.96)
        by = np.random.uniform(18.94, 19.06)
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
    with open(os.path.join(base_data_dir, "buildings", "buildings.geojson"), "w") as f:
        json.dump({"type": "FeatureCollection", "features": buildings_features}, f, indent=2)
    print(f" - Created data/buildings/buildings.geojson ({len(buildings_features)} footprints)")

    # 4. Generate Road Network GeoJSON
    roads_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "National Highway 48 Bypass", "highway": "primary"},
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [72.81, 18.92], [72.86, 18.97], [72.91, 19.02], [72.97, 19.07]
                    ]
                }
            },
            {
                "type": "Feature",
                "properties": {"name": "River Coastal Link Road", "highway": "secondary"},
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [72.84, 19.07], [72.88, 19.01], [72.93, 18.96], [72.98, 18.93]
                    ]
                }
            }
        ]
    }
    with open(os.path.join(base_data_dir, "roads", "roads.geojson"), "w") as f:
        json.dump(roads_geojson, f, indent=2)
    print(" - Created data/roads/roads.geojson")

    # 5. Generate POIs / Candidate Evacuation Facilities
    pois_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "Govt High School Navapur", "type": "school", "capacity": 500},
                "geometry": {"type": "Point", "coordinates": [72.835, 19.075]}
            },
            {
                "type": "Feature",
                "properties": {"name": "Community Hall Kalyanpur", "type": "community_hall", "capacity": 300},
                "geometry": {"type": "Point", "coordinates": [72.975, 18.935]}
            },
            {
                "type": "Feature",
                "properties": {"name": "District Civic Center", "type": "government", "capacity": 800},
                "geometry": {"type": "Point", "coordinates": [72.825, 18.925]}
            },
            {
                "type": "Feature",
                "properties": {"name": "East Hill Primary Health Centre", "type": "clinic", "capacity": 150},
                "geometry": {"type": "Point", "coordinates": [72.985, 19.085]}
            }
        ]
    }
    with open(os.path.join(base_data_dir, "pois", "facilities.geojson"), "w") as f:
        json.dump(pois_geojson, f, indent=2)
    print(" - Created data/pois/facilities.geojson")

    # 6. Generate Synthetic DEM GeoTIFF & Satellite GeoTIFFs (if rasterio is available)
    try:
        import rasterio
        from rasterio.transform import from_bounds
        from rasterio.crs import CRS

        transform = from_bounds(MIN_LON, MIN_LAT, MAX_LON, MAX_LAT, WIDTH, HEIGHT)
        crs = CRS.from_epsg(4326)

        # Elevation DEM: Hill gradient from 5m (west) to 85m (east)
        x_coords = np.linspace(0, 1, WIDTH)
        y_coords = np.linspace(0, 1, HEIGHT)
        xx, yy = np.meshgrid(x_coords, y_coords)
        dem_data = (5.0 + 80.0 * xx + 15.0 * yy).astype(np.float32)

        dem_path = os.path.join(base_data_dir, "dem", "dem_elevation.tif")
        with rasterio.open(
            dem_path, "w", driver="GTiff", height=HEIGHT, width=WIDTH,
            count=1, dtype=rasterio.float32, crs=crs, transform=transform, nodata=-9999.0
        ) as dst:
            dst.write(dem_data, 1)
        print(" - Created data/dem/dem_elevation.tif")

        # Synthetic Sentinel Multi-band: Band 1=Blue, Band 2=Green, Band 3=Red, Band 4=NIR
        # Pre-flood: dry baseline with a small river channel
        pre_raster = np.full((4, HEIGHT, WIDTH), 80.0, dtype=np.float32)
        # Small permanent water channel in center
        pre_raster[1, 95:105, :] = 120.0  # Green
        pre_raster[3, 95:105, :] = 20.0   # NIR (low for water)

        pre_path = os.path.join(base_data_dir, "input", "sample_pre_flood_sentinel.tif")
        with rasterio.open(
            pre_path, "w", driver="GTiff", height=HEIGHT, width=WIDTH,
            count=4, dtype=rasterio.float32, crs=crs, transform=transform
        ) as dst:
            dst.write(pre_raster)
        print(" - Created data/input/sample_pre_flood_sentinel.tif")

        # Post-flood: widespread flood plume in the central plain
        post_raster = np.copy(pre_raster)
        # Inundate rows 70:140, cols 40:160
        post_raster[1, 70:140, 40:160] = 140.0  # High green
        post_raster[3, 70:140, 40:160] = 15.0   # Low NIR -> positive NDWI water signature
        # Single-band differencing signal:
        post_raster[0, 70:140, 40:160] = 220.0

        post_path = os.path.join(base_data_dir, "input", "sample_post_flood_sentinel.tif")
        with rasterio.open(
            post_path, "w", driver="GTiff", height=HEIGHT, width=WIDTH,
            count=4, dtype=rasterio.float32, crs=crs, transform=transform
        ) as dst:
            dst.write(post_raster)
        print(" - Created data/input/sample_post_flood_sentinel.tif")

    except ImportError:
        print(" (rasterio not installed yet — synthetic GeoTIFF generation skipped; vector GeoJSON layers created.)")

    print("\nScenario dataset generation complete.")


if __name__ == "__main__":
    import sys
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "data"
    generate_scenario(data_dir)
