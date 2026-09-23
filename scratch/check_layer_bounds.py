import geopandas as gpd
import rasterio

v_gdf = gpd.read_file('data/boundaries/villages_visual.geojson')
print('Villages bounds:', v_gdf.total_bounds)

r_gdf = gpd.read_file('data/roads/roads.geojson')
print('Roads bounds:', r_gdf.total_bounds)

e_gdf = gpd.read_file('data/pois/facilities.geojson')
print('Facilities bounds:', e_gdf.total_bounds)

with rasterio.open('data/test_images/kerala_before_flood.tif') as ds:
    print('Raster bounds:', ds.bounds)
