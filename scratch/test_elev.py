import urllib.request
import json

url = 'https://api.open-elevation.com/api/v1/lookup?locations=9.67,76.46|9.70,76.48'
try:
    req = urllib.request.Request(url, headers={'User-Agent': 'SatQuery/1.0'})
    with urllib.request.urlopen(req, timeout=10) as resp:
        print(resp.read().decode())
except Exception as e:
    print("Open-elevation error:", e)
