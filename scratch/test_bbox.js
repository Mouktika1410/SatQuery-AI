import fs from 'fs';

const data = JSON.parse(fs.readFileSync('scratch/sample_flood.geojson'));

function getGeoJSONBBox(geojson) {
  let minLon = Infinity;
  let minLat = Infinity;
  let maxLon = -Infinity;
  let maxLat = -Infinity;

  function traverse(coords) {
    if (!Array.isArray(coords)) return;
    if (typeof coords[0] === 'number' && typeof coords[1] === 'number') {
      const lon = coords[0];
      const lat = coords[1];
      if (lon < minLon) minLon = lon;
      if (lon > maxLon) maxLon = lon;
      if (lat < minLat) minLat = lat;
      if (lat > maxLat) maxLat = lat;
    } else {
      coords.forEach(traverse);
    }
  }

  if (geojson?.type === 'FeatureCollection' && Array.isArray(geojson.features)) {
    geojson.features.forEach((f) => {
      if (f.geometry?.coordinates) traverse(f.geometry.coordinates);
    });
  } else if (geojson?.type === 'Feature' && geojson.geometry?.coordinates) {
    traverse(geojson.geometry.coordinates);
  } else if (geojson?.coordinates) {
    traverse(geojson.coordinates);
  }

  if (!isFinite(minLon) || !isFinite(minLat)) {
    return null;
  }

  return {
    minLon,
    minLat,
    maxLon,
    maxLat,
    centerLon: (minLon + maxLon) / 2,
    centerLat: (minLat + maxLat) / 2,
    spanLon: Math.max(maxLon - minLon, 0.01),
    spanLat: Math.max(maxLat - minLat, 0.01),
  };
}

console.log('Result bbox:', getGeoJSONBBox(data));
