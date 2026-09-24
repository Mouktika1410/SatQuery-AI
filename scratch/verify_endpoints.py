import urllib.request

endpoints = [
    'https://mt1.google.com/vt/lyrs=s&x=2917&y=1937&z=12',
    'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/12/1937/2917',
    'http://localhost:5173'
]

for url in endpoints:
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=5)
        print(url[:50], '->', resp.status, resp.headers.get('Content-Type'))
    except Exception as e:
        print(url[:50], '-> ERROR:', e)
