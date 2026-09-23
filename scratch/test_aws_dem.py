import math
import urllib.request

# Latitude 9.67, Longitude 76.46
# Mapzen terrain tiles zoom 10:
lat, lon = 9.67, 76.46
z = 10
lat_rad = math.radians(lat)
n = 2.0 ** z
x = int((lon + 180.0) / 360.0 * n)
y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)

url = f"https://elevation-tiles-prod.s3.amazonaws.com/geotiff/{z}/{x}/{y}.tif"
print("Testing URL:", url)
try:
    req = urllib.request.Request(url, headers={'User-Agent': 'SatQuery/1.0'})
    with urllib.request.urlopen(req, timeout=10) as resp:
        content = resp.read()
        print("Success! Downloaded GeoTIFF bytes:", len(content))
except Exception as e:
    print("AWS terrain error:", e)
