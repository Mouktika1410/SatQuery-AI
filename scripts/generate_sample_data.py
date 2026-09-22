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

    # 1. Generate Village Boundaries GeoJSON (Analytical closed polygons for GIS calculations)
    villages_analytical_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "Navapur Village", "population": 4200, "zone": "North-West"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [72.840, 19.018], [72.892, 19.018], [72.892, 19.058], [72.840, 19.058], [72.840, 19.018]
                    ]]
                }
            },
            {
                "type": "Feature",
                "properties": {"name": "Shivaji Nagar", "population": 3100, "zone": "North-East"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [72.892, 19.018], [72.942, 19.018], [72.942, 19.055], [72.892, 19.055], [72.892, 19.018]
                    ]]
                }
            },
            {
                "type": "Feature",
                "properties": {"name": "Kalyanpur Settlement", "population": 6800, "zone": "South-Central"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [72.882, 18.960], [72.942, 18.960], [72.942, 19.018], [72.882, 19.018], [72.882, 18.960]
                    ]]
                }
            }
        ]
    }
    with open(os.path.join(base_data_dir, "boundaries", "villages.geojson"), "w") as f:
        json.dump(villages_analytical_geojson, f, indent=2)
    print(" - Created data/boundaries/villages.geojson (analytical closed polygons)")

    # Visual village boundary overlay GeoJSON (Open dashed reference lines for map display)
    villages_visual_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "Navapur Village", "population": 4200, "zone": "North-West"},
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [72.840, 19.018], [72.892, 19.018], [72.892, 19.058]
                    ]
                }
            },
            {
                "type": "Feature",
                "properties": {"name": "Shivaji Nagar", "population": 3100, "zone": "North-East"},
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [72.892, 19.018], [72.942, 19.018], [72.942, 19.055]
                    ]
                }
            },
            {
                "type": "Feature",
                "properties": {"name": "Kalyanpur Settlement", "population": 6800, "zone": "South-Central"},
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [72.882, 19.018], [72.882, 18.960], [72.942, 18.960], [72.942, 19.018]
                    ]
                }
            }
        ]
    }
    with open(os.path.join(base_data_dir, "boundaries", "villages_visual.geojson"), "w") as f:
        json.dump(villages_visual_geojson, f, indent=2)
    print(" - Created data/boundaries/villages_visual.geojson (open dashed reference overlay)")

    # 2. Generate Population GeoJSON
    with open(os.path.join(base_data_dir, "population", "population.geojson"), "w") as f:
        json.dump(villages_analytical_geojson, f, indent=2)
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

    # 4. Generate Road Network GeoJSON (Exact 2 road corridors matching 2nd reference image)
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
        from rasterio.enums import ColorInterp

        transform = from_bounds(MIN_LON, MIN_LAT, MAX_LON, MAX_LAT, WIDTH, HEIGHT)
        crs = CRS.from_epsg(4326)

        np.random.seed(42)

        grid_y, grid_x = np.ogrid[:HEIGHT, :WIDTH]
        norm_x = grid_x / float(WIDTH - 1)
        norm_y = grid_y / float(HEIGHT - 1)

        # Central centroid of the main inundation region (matching reference image)
        cx, cy = 0.50, 0.48
        r_dist = np.sqrt((norm_x - cx)**2 + (norm_y - cy)**2)

        # Multi-scale smooth Gaussian Random Field (uneven lobes, branching extensions & micro-edges)
        r1 = np.random.randn(HEIGHT, WIDTH)
        r2 = np.random.randn(HEIGHT, WIDTH)
        r3 = np.random.randn(HEIGHT, WIDTH)

        try:
            from scipy import ndimage as ndi
            g1 = ndi.gaussian_filter(r1, sigma=20.0)
            g2 = ndi.gaussian_filter(r2, sigma=8.0)
            g3 = ndi.gaussian_filter(r3, sigma=3.0)
        except ImportError:
            g1, g2, g3 = r1, r2, r3

        noise_field = g1 * 0.50 + g2 * 0.35 + g3 * 0.15
        n_min, n_max = noise_field.min(), noise_field.max()
        noise_norm = (noise_field - n_min) / (n_max - n_min + 1e-10)

        # Dynamic Organic Coastal Bay Inundation Radius Field (matching exact reference silhouette)
        organic_radius = 0.22 + 0.22 * noise_norm

        # Single dominant, broad, continuous, organic flood region matching reference silhouette
        raw_flood_mask = r_dist < organic_radius
        raw_flood_mask[0, :] = False
        raw_flood_mask[-1, :] = False
        raw_flood_mask[:, 0] = False
        raw_flood_mask[:, -1] = False

        # Fill internal holes to guarantee 0 holes
        clean_flood_mask = ndi.binary_fill_holes(raw_flood_mask)

        # Retain single largest connected component (guarantees 0 disconnected fragments)
        lbl, num = ndi.label(clean_flood_mask)
        if num > 1:
            sizes = ndi.sum(clean_flood_mask, lbl, range(1, num + 1))
            largest_label = np.argmax(sizes) + 1
            flood_mask = (lbl == largest_label)
        else:
            flood_mask = clean_flood_mask

        dem_data = (10.0 + 65.0 * r_dist - 15.0 * noise_norm).astype(np.float32)

        dem_path = os.path.join(base_data_dir, "dem", "dem_elevation.tif")
        with rasterio.open(
            dem_path, "w", driver="GTiff", height=HEIGHT, width=WIDTH,
            count=1, dtype=rasterio.float32, crs=crs, transform=transform, nodata=-9999.0
        ) as dst:
            dst.write(dem_data, 1)
        print(" - Created data/dem/dem_elevation.tif")

        # Synthetic Sentinel Multi-band (uint8 RGB + NIR for Windows Explorer thumbnail compatibility)
        # Band 1=Red, Band 2=Green, Band 3=Blue, Band 4=NIR
        pre_raster = np.zeros((4, HEIGHT, WIDTH), dtype=np.uint8)
        pre_raster[0] = 70   # Red
        pre_raster[1] = 110  # Green
        pre_raster[2] = 65   # Blue
        pre_raster[3] = 180  # NIR

        pre_path = os.path.join(base_data_dir, "input", "sample_pre_flood_sentinel.tif")
        with rasterio.open(
            pre_path, "w", driver="GTiff", height=HEIGHT, width=WIDTH,
            count=4, dtype=rasterio.uint8, crs=crs, transform=transform,
            photometric="RGB"
        ) as dst:
            dst.colorinterp = [ColorInterp.red, ColorInterp.green, ColorInterp.blue, ColorInterp.nir]
            dst.write(pre_raster)
        print(" - Created data/input/sample_pre_flood_sentinel.tif")

        # Post-flood: organic flood plume matching reference image
        post_raster = np.copy(pre_raster)
        post_raster[0, flood_mask] = 30   # Red
        post_raster[1, flood_mask] = 80   # Green
        post_raster[2, flood_mask] = 180  # High Blue
        post_raster[3, flood_mask] = 10   # Low NIR -> strong water NDWI signature

        post_path = os.path.join(base_data_dir, "input", "sample_post_flood_sentinel.tif")
        with rasterio.open(
            post_path, "w", driver="GTiff", height=HEIGHT, width=WIDTH,
            count=4, dtype=rasterio.uint8, crs=crs, transform=transform,
            photometric="RGB"
        ) as dst:
            dst.colorinterp = [ColorInterp.red, ColorInterp.green, ColorInterp.blue, ColorInterp.nir]
            dst.write(post_raster)
        print(" - Created data/input/sample_post_flood_sentinel.tif")

    except ImportError:
        print(" (rasterio not installed yet — synthetic GeoTIFF generation skipped; vector GeoJSON layers created.)")

    print("\nScenario dataset generation complete.")


if __name__ == "__main__":
    import sys
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "data"
    generate_scenario(data_dir)
