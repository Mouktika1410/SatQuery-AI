import urllib.request
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.merge import merge
import numpy as np
import io

print("Downloading real SRTM/Mapzen elevation tiles from AWS Open Data...")
url1 = "https://elevation-tiles-prod.s3.amazonaws.com/geotiff/10/729/484.tif"
url2 = "https://elevation-tiles-prod.s3.amazonaws.com/geotiff/10/729/485.tif"

req1 = urllib.request.Request(url1, headers={'User-Agent': 'SatQuery/1.0'})
req2 = urllib.request.Request(url2, headers={'User-Agent': 'SatQuery/1.0'})

with urllib.request.urlopen(req1) as r1, urllib.request.urlopen(req2) as r2:
    ds1 = rasterio.open(io.BytesIO(r1.read()))
    ds2 = rasterio.open(io.BytesIO(r2.read()))

mosaic, out_trans = merge([ds1, ds2])
print("Mosaic shape:", mosaic.shape, "CRS:", ds1.crs)

# Reproject to EPSG:4326 covering exact Kerala before_flood bounds
with rasterio.open("data/test_images/kerala_before_flood.tif") as ref:
    dst_crs = ref.crs
    dst_transform = ref.transform
    dst_width = ref.width
    dst_height = ref.height

destination = np.zeros((1, dst_height, dst_width), dtype=np.float32)

reproject(
    source=mosaic,
    destination=destination,
    src_transform=out_trans,
    src_crs=ds1.crs,
    dst_transform=dst_transform,
    dst_crs=dst_crs,
    resampling=Resampling.bilinear
)

# Replace negative ocean/lake values with near-surface 1.0m
destination[destination < 0] = 1.0

print(f"Reprojected DEM! Min: {destination.min():.1f}m, Max: {destination.max():.1f}m, Mean: {destination.mean():.1f}m")

# Write to scratch/real_dem.tif
profile = {
    'driver': 'GTiff',
    'dtype': 'float32',
    'nodata': -9999.0,
    'width': dst_width,
    'height': dst_height,
    'count': 1,
    'crs': dst_crs,
    'transform': dst_transform
}

with rasterio.open("scratch/real_dem.tif", "w", **profile) as dst:
    dst.write(destination[0], 1)

print("Saved scratch/real_dem.tif!")
