import ee

ee.Initialize(project="satquery-flood-detection")

roi = ee.Geometry.Rectangle([-1.25, 53.50, -0.90, 53.65])

pre_coll = (
    ee.ImageCollection("COPERNICUS/S1_GRD")
    .filterBounds(roi)
    .filterDate("2019-10-15", "2019-11-04")
    .filter(ee.Filter.eq("instrumentMode", "IW"))
    .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
    .filter(ee.Filter.eq("orbitProperties_pass", "ASCENDING"))
)

post_coll = (
    ee.ImageCollection("COPERNICUS/S1_GRD")
    .filterBounds(roi)
    .filterDate("2019-11-05", "2019-11-15")
    .filter(ee.Filter.eq("instrumentMode", "IW"))
    .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
    .filter(ee.Filter.eq("orbitProperties_pass", "ASCENDING"))
)

print("Pre scenes count:", pre_coll.size().getInfo())
print("Post scenes count:", post_coll.size().getInfo())

# Get acquisition metadata
pre_feats = pre_coll.getInfo()["features"]
post_feats = post_coll.getInfo()["features"]

pre_dates = [f["properties"]["system:index"] for f in pre_feats]
post_dates = [f["properties"]["system:index"] for f in post_feats]

print("Pre scene IDs:", pre_dates[:3])
print("Post scene IDs:", post_dates[:3])

# Calculate backscatter median
pre_img = pre_coll.select("VV").median()
post_img = post_coll.select("VV").median()

# Speckle filtering (focal mean)
smoothing_radius = 50
pre_smoothed = pre_img.focal_mean(smoothing_radius, "circle", "meters")
post_smoothed = post_img.focal_mean(smoothing_radius, "circle", "meters")

# Log ratio / dB difference (post - pre)
diff = post_smoothed.subtract(pre_smoothed)

# Flood threshold: drop in VV backscatter by > 2.0 dB
flood_mask = diff.lt(-2.0)

# Permanent water mask (JRC)
gsw = ee.Image("JRC/GSW1_4/GlobalSurfaceWater")
perm_water = gsw.select("occurrence").gt(50)

# Apply slope threshold using SRTM DEM
dem = ee.Image("USGS/SRTMGL1_003")
slope = ee.Terrain.slope(dem)

# Final flood mask: drop in backscatter AND not permanent water AND slope < 5 degrees
flood_mask = flood_mask.And(perm_water.Not()).And(slope.lt(5)).rename("flood")

# Mask raster to keep only 1s
flood_mask_only = flood_mask.selfMask()

# Reduce to vectors
vectors = flood_mask_only.reduceToVectors(
    geometry=roi,
    scale=30,
    geometryType="polygon",
    eightConnected=True,
    maxPixels=1e8
)

geojson = vectors.getInfo()
features = geojson.get("features", [])
print("Extracted feature count:", len(features))

# Calculate total area
area_img = flood_mask_only.multiply(ee.Image.pixelArea())
total_area_m2 = area_img.reduceRegion(
    reducer=ee.Reducer.sum(),
    geometry=roi,
    scale=30,
    maxPixels=1e8
).get("flood").getInfo()

print("Total flood area m2:", total_area_m2)
print("Total flood area km2:", (total_area_m2 or 0) / 1e6)
