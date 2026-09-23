import shutil
import os
import json

base_data_dir = "data"

# 1. Villages
shutil.copyfile("scratch/real_panchayats.geojson", os.path.join(base_data_dir, "boundaries", "villages.geojson"))
shutil.copyfile("scratch/real_panchayats_visual.geojson", os.path.join(base_data_dir, "boundaries", "villages_visual.geojson"))
print("Installed real Kerala Panchayats into data/boundaries/")

# 2. Population (uses the same real Panchayats with 2011 census population)
shutil.copyfile("scratch/real_panchayats.geojson", os.path.join(base_data_dir, "population", "population.geojson"))
print("Installed real Kerala population data into data/population/")

# 3. Roads
shutil.copyfile("scratch/real_roads.geojson", os.path.join(base_data_dir, "roads", "roads.geojson"))
print("Installed real Kerala OSM road network into data/roads/")

# 4. Buildings
shutil.copyfile("scratch/real_buildings.geojson", os.path.join(base_data_dir, "buildings", "buildings.geojson"))
print("Installed real Kerala building footprints into data/buildings/")

# 5. POIs / Facilities
shutil.copyfile("scratch/real_facilities.geojson", os.path.join(base_data_dir, "pois", "facilities.geojson"))
print("Installed real Kerala evacuation facilities into data/pois/")

# 6. DEM
shutil.copyfile("scratch/real_dem.tif", os.path.join(base_data_dir, "dem", "dem_elevation.tif"))
print("Installed real SRTM DEM elevation raster into data/dem/")
