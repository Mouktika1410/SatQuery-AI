import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

export default function MapViewer({
  floodGeoJSON,
  floodMetrics,
  evacuationCandidates,
  affectedVillages,
  affectedVillagesGeoJSON,
  affectedRoadsGeoJSON,
}) {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const floodLayerRef = useRef(null);
  const villagesLayerRef = useRef(null);
  const roadsLayerRef = useRef(null);
  const evacuLayerRef = useRef(null);
  const layerControlRef = useRef(null);

  // Initialize Leaflet map once
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    const map = L.map(mapContainerRef.current, {
      center: [19.0, 72.9], // Default center around Maharashtra/Gujarat flood plain
      zoom: 11,
      zoomControl: true,
    });

    // Base tile layers: Esri World Imagery Satellite & OpenStreetMap
    const osm = L.tileLayer(
      'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
      {
        attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
        maxZoom: 19,
      }
    );

    const satellite = L.tileLayer(
      'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      {
        attribution: '© Esri World Imagery',
        maxZoom: 18,
      }
    );

    // Default to Satellite basemap for remote sensing imagery display
    satellite.addTo(map);

    const baseMaps = {
      'Satellite': satellite,
      'Street Map': osm,
    };

    const overlayMaps = {};
    layerControlRef.current = L.control.layers(baseMaps, overlayMaps, { position: 'topright' });
    layerControlRef.current.addTo(map);

    mapInstanceRef.current = map;

    // Trigger map size recalculation after layout render
    setTimeout(() => {
      map.invalidateSize();
    }, 250);

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  // Update layers and fit bounds whenever pipeline results update
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    let combinedBounds = null;

    // 1. Update flood polygon layer
    if (floodLayerRef.current) {
      layerControlRef.current?.removeLayer(floodLayerRef.current);
      map.removeLayer(floodLayerRef.current);
      floodLayerRef.current = null;
    }

    if (floodGeoJSON && floodGeoJSON.features && floodGeoJSON.features.length > 0) {
      const areaStr = floodMetrics?.areaKm2 != null ? `${Number(floodMetrics.areaKm2).toFixed(2)} km²` : 'N/A';
      const pctStr = floodMetrics?.floodPercentage != null ? `${Number(floodMetrics.floodPercentage).toFixed(2)}%` : 'N/A';
      const countStr = floodMetrics?.polygonCount != null ? floodMetrics.polygonCount : floodGeoJSON.features.length;

      const floodLayer = L.geoJSON(floodGeoJSON, {
        style: {
          color: '#1d4ed8',
          weight: 2.5,
          opacity: 0.95,
          fillColor: '#3b82f6',
          fillOpacity: 0.50,
        },
        onEachFeature: (feature, lyr) => {
          // Highlight on hover
          lyr.on({
            mouseover: (e) => {
              const layer = e.target;
              layer.setStyle({ fillOpacity: 0.70, weight: 3 });
            },
            mouseout: (e) => {
              floodLayer.resetStyle(e.target);
            },
          });

          lyr.bindPopup(
            '<div style="font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;font-size:13px;line-height:1.5;padding:2px;min-width:200px">' +
            '<div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;border-bottom:1px solid #e2e8f0;padding-bottom:4px">' +
            '<span style="font-size:16px">🌊</span><b style="color:#1d4ed8;font-size:14px">Detected Flood Extent</b>' +
            '</div>' +
            `<div style="display:flex;justify-space-between;margin-bottom:3px"><span><b>Flooded Area:</b></span><span style="color:#1d4ed8;font-weight:600;margin-left:auto">${areaStr}</span></div>` +
            `<div style="display:flex;justify-space-between;margin-bottom:3px"><span><b>Image Coverage:</b></span><span style="color:#2563eb;font-weight:600;margin-left:auto">${pctStr}</span></div>` +
            `<div style="display:flex;justify-space-between;margin-bottom:4px"><span><b>Polygon Count:</b></span><span style="color:#475569;font-weight:600;margin-left:auto">${countStr}</span></div>` +
            '<div style="color:#64748b;font-size:11px;margin-top:6px;background:#f1f5f9;padding:4px 6px;border-radius:4px">Derived from satellite change detection analysis</div>' +
            '</div>'
          );
        },
      });

      floodLayer.addTo(map);
      floodLayerRef.current = floodLayer;
      layerControlRef.current?.addOverlay(floodLayer, '🌊 Flood Extent');

      try {
        const b = floodLayer.getBounds();
        if (b.isValid()) {
          combinedBounds = combinedBounds ? combinedBounds.extend(b) : b;
        }
      } catch (_) {}
    }

    // 2. Update affected villages layer
    if (villagesLayerRef.current) {
      layerControlRef.current?.removeLayer(villagesLayerRef.current);
      map.removeLayer(villagesLayerRef.current);
      villagesLayerRef.current = null;
    }

    if (affectedVillagesGeoJSON && affectedVillagesGeoJSON.features && affectedVillagesGeoJSON.features.length > 0) {
      // Build lookup for village details from affectedVillages array if available
      const villageLookup = {};
      if (affectedVillages && Array.isArray(affectedVillages)) {
        affectedVillages.forEach((v) => {
          if (v.name) villageLookup[v.name.toLowerCase()] = v;
        });
      }

      const villagesLayer = L.geoJSON(affectedVillagesGeoJSON, {
        style: {
          color: '#d97706',
          weight: 2.5,
          opacity: 0.95,
          fillColor: '#fef3c7',
          fillOpacity: 0.20,
          dashArray: '6, 6',
        },
        onEachFeature: (feature, lyr) => {
          const name = feature.properties?.name || feature.properties?.NAME || 'Affected Village';
          const match = villageLookup[name.toLowerCase()];
          const floodedKm2 = match?.area_flooded_km2 != null ? `${match.area_flooded_km2.toFixed(2)} km²` : null;
          const popEst = match?.population_affected != null ? match.population_affected.toLocaleString() : null;

          lyr.on({
            mouseover: (e) => {
              e.target.setStyle({ fillOpacity: 0.40, weight: 3.5 });
            },
            mouseout: (e) => {
              villagesLayer.resetStyle(e.target);
            },
          });

          lyr.bindPopup(
            '<div style="font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;font-size:13px;line-height:1.5;padding:2px;min-width:190px">' +
            '<div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;border-bottom:1px solid #fef3c7;padding-bottom:4px">' +
            '<span style="font-size:16px">🏘️</span><b style="color:#d97706;font-size:14px">' + name + '</b>' +
            '</div>' +
            (floodedKm2 ? `<div style="margin-bottom:3px"><b>Inundated Area:</b> <span style="color:#d97706;font-weight:600">${floodedKm2}</span></div>` : '') +
            (popEst ? `<div style="margin-bottom:3px"><b>Est. Affected Pop:</b> <span style="color:#475569;font-weight:600">${popEst}</span></div>` : '') +
            '<div style="color:#78350f;font-size:11px;margin-top:6px;background:#fffbeb;padding:4px 6px;border-radius:4px;border:1px solid #fef3c7">' +
            'Village administrative boundary intersected by detected flood polygon' +
            '</div>' +
            '</div>'
          );
        },
      });

      villagesLayer.addTo(map);
      villagesLayerRef.current = villagesLayer;
      layerControlRef.current?.addOverlay(villagesLayer, '🏘️ Affected Villages');

      try {
        const b = villagesLayer.getBounds();
        if (b.isValid()) {
          combinedBounds = combinedBounds ? combinedBounds.extend(b) : b;
        }
      } catch (_) {}
    }

    // 3. Update affected roads layer
    if (roadsLayerRef.current) {
      layerControlRef.current?.removeLayer(roadsLayerRef.current);
      map.removeLayer(roadsLayerRef.current);
      roadsLayerRef.current = null;
    }

    if (affectedRoadsGeoJSON && affectedRoadsGeoJSON.features && affectedRoadsGeoJSON.features.length > 0) {
      const roadsLayer = L.geoJSON(affectedRoadsGeoJSON, {
        style: {
          color: '#dc2626',
          weight: 4,
          opacity: 0.90,
          dashArray: '4, 4',
        },
        onEachFeature: (feature, lyr) => {
          const name = feature.properties?.name || 'Inundated Road Segment';
          const type = feature.properties?.highway || 'road';

          lyr.bindPopup(
            '<div style="font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;font-size:13px;line-height:1.5;padding:2px;min-width:180px">' +
            '<div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;border-bottom:1px solid #fee2e2;padding-bottom:4px">' +
            '<span style="font-size:16px">🛣️</span><b style="color:#dc2626;font-size:14px">' + name + '</b>' +
            '</div>' +
            `<div style="margin-bottom:3px"><b>Highway Type:</b> ${type}</div>` +
            '<div style="color:#991b1b;font-weight:600;font-size:12px;margin-top:4px;background:#fef2f2;padding:4px 6px;border-radius:4px;border:1px solid #fee2e2">' +
            '⚠️ Submerged / Impassable Road Network Segment' +
            '</div>' +
            '</div>'
          );
        },
      });

      roadsLayer.addTo(map);
      roadsLayerRef.current = roadsLayer;
      layerControlRef.current?.addOverlay(roadsLayer, '🛣️ Inundated Roads');

      try {
        const b = roadsLayer.getBounds();
        if (b.isValid()) {
          combinedBounds = combinedBounds ? combinedBounds.extend(b) : b;
        }
      } catch (_) {}
    }

    // 4. Update candidate accessible sites markers
    if (evacuLayerRef.current) {
      layerControlRef.current?.removeLayer(evacuLayerRef.current);
      map.removeLayer(evacuLayerRef.current);
      evacuLayerRef.current = null;
    }

    if (evacuationCandidates && evacuationCandidates.length > 0) {
      const group = L.layerGroup();
      evacuationCandidates.forEach((c) => {
        if (c.lat == null || c.lon == null) return;

        const icon = L.divIcon({
          className: 'custom-evac-pin',
          html: (
            '<div style="background:#10b981;border:2.5px solid white;border-radius:50%;width:18px;height:18px;box-shadow:0 0 6px rgba(0,0,0,0.6);display:flex;align-items:center;justify-content:center;color:white;font-size:10px;font-weight:bold">' +
            '✓' +
            '</div>'
          ),
          iconSize: [18, 18],
          iconAnchor: [9, 9],
        });

        const marker = L.marker([c.lat, c.lon], { icon });
        marker.bindPopup(
          '<div style="font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;font-size:13px;line-height:1.5;padding:2px;max-width:240px">' +
          '<div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;border-bottom:1px solid #d1fae5;padding-bottom:4px">' +
          '<span style="font-size:16px">🏫</span><b style="color:#059669;font-size:14px">' + c.name + '</b>' +
          '</div>' +
          `<div style="margin-bottom:2px"><b>Facility Type:</b> ${c.type}</div>` +
          (c.distance_to_flood_km != null
            ? `<div style="margin-bottom:2px"><b>Proximity to Flood:</b> <span style="color:#059669;font-weight:600">${c.distance_to_flood_km.toFixed(2)} km</span></div>`
            : '') +
          (c.elevation_m != null
            ? `<div style="margin-bottom:4px"><b>DEM Elevation:</b> ${c.elevation_m.toFixed(1)} m</div>`
            : '') +
          '<div style="font-size:11px;color:#d97706;margin-top:6px;line-height:1.35;background:#fffbeb;padding:5px 7px;border-radius:4px;border:1px solid #fef3c7">' +
          '⚠️ <b>Disclaimer:</b> Candidate accessible site for on-ground verification only. Not a verified shelter.' +
          '</div>' +
          '</div>'
        );
        group.addLayer(marker);

        const pointBounds = L.latLngBounds([L.latLng(c.lat, c.lon), L.latLng(c.lat, c.lon)]);
        combinedBounds = combinedBounds ? combinedBounds.extend(pointBounds) : pointBounds;
      });

      group.addTo(map);
      evacuLayerRef.current = group;
      layerControlRef.current?.addOverlay(group, '🏫 Candidate Sites');
    }

    // 5. Fit bounds smoothly to combined extent of all active layers
    if (combinedBounds && combinedBounds.isValid()) {
      map.fitBounds(combinedBounds, { padding: [40, 40], maxZoom: 13 });
    }

    map.invalidateSize();
  }, [floodGeoJSON, floodMetrics, affectedVillagesGeoJSON, affectedRoadsGeoJSON, evacuationCandidates]);

  const hasData =
    (floodGeoJSON && floodGeoJSON.features && floodGeoJSON.features.length > 0) ||
    (affectedVillagesGeoJSON && affectedVillagesGeoJSON.features && affectedVillagesGeoJSON.features.length > 0) ||
    (evacuationCandidates && evacuationCandidates.length > 0);

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', minHeight: '400px' }}>
      {!hasData && (
        <div className="map-no-data">
          <span className="map-no-data-icon">🗺️</span>
          <span>Upload pre & post satellite GeoTIFFs and run analysis to view geospatial results</span>
        </div>
      )}

      <div ref={mapContainerRef} style={{ width: '100%', height: '100%', minHeight: '400px' }} />

      {/* Structured Map Legend */}
      {hasData && (
        <div className="map-legend">
          <div style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: 6, letterSpacing: '0.04em', textTransform: 'uppercase' }}>
            Map Layers
          </div>
          <div className="legend-item">
            <div className="legend-swatch" style={{ background: 'rgba(59,130,246,0.5)', border: '1.5px solid #1d4ed8' }} />
            <span>Flood Extent</span>
          </div>
          {affectedVillagesGeoJSON?.features?.length > 0 && (
            <div className="legend-item">
              <div className="legend-swatch" style={{ background: 'rgba(254,243,199,0.4)', border: '1.5px dashed #d97706' }} />
              <span>Affected Villages</span>
            </div>
          )}
          {affectedRoadsGeoJSON?.features?.length > 0 && (
            <div className="legend-item">
              <div className="legend-swatch" style={{ background: '#dc2626', height: '3px', marginTop: '5px' }} />
              <span>Inundated Roads</span>
            </div>
          )}
          {evacuationCandidates?.length > 0 && (
            <div className="legend-item">
              <div className="legend-swatch" style={{ background: '#10b981', borderRadius: '50%', border: '2px solid white' }} />
              <span>Candidate Site (Unverified)</span>
            </div>
          )}
          <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginTop: 6, borderTop: '1px solid var(--border)', paddingTop: 4 }}>
            Toggle layers via top-right control
          </div>
        </div>
      )}
    </div>
  );
}
