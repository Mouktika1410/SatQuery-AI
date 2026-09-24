import math
import urllib.request

lat, lon, z = 9.6791, 76.4624, 12
lat_rad = math.radians(lat)
n = 2.0 ** z
xtile = int((lon + 180.0) / 360.0 * n)
ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
url = f"https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{ytile}/{xtile}"
print("Testing Esri:", url)
try:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req, timeout=5)
    print("Esri Status:", resp.status, "Content-Type:", resp.headers.get("Content-Type"), "Size:", len(resp.read()))
except Exception as e:
    print("Esri Error:", e)

# Also test CartoDB / OSM / Google / other providers
g_url = f"https://mt1.google.com/vt/lyrs=s&x={xtile}&y={ytile}&z={z}"
print("Testing Google Satellite:", g_url)
try:
    req = urllib.request.Request(g_url, headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req, timeout=5)
    print("Google Status:", resp.status, "Content-Type:", resp.headers.get("Content-Type"), "Size:", len(resp.read()))
except Exception as e:
    print("Google Error:", e)
