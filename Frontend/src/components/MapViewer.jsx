import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

export default function MapViewer({
  floodGeoJSON,
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
      center: [19.0, 72.9], // Default center around Maharashtra/Gujarat flood zone
      zoom: 11,
      zoomControl: true,
    });

    // Base tile layers
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

    osm.addTo(map);

    const baseMaps = {
      'Street Map': osm,
      'Satellite': satellite,
    };

    const overlayMaps = {};
    layerControlRef.current = L.control.layers(baseMaps, overlayMaps, { position: 'topright' });
    layerControlRef.current.addTo(map);

    mapInstanceRef.current = map;

    // Trigger map resize after initial render
    setTimeout(() => {
      map.invalidateSize();
    }, 200);

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  // Update layers and fit bounds whenever pipeline results update
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    const boundsToFit = [];

    // 1. Update flood polygon layer
    if (floodLayerRef.current) {
      layerControlRef.current?.removeLayer(floodLayerRef.current);
      map.removeLayer(floodLayerRef.current);
      floodLayerRef.current = null;
    }

    if (floodGeoJSON && floodGeoJSON.features && floodGeoJSON.features.length > 0) {
      const floodLayer = L.geoJSON(floodGeoJSON, {
        style: {
          color: '#1d4ed8',
          weight: 2,
          opacity: 0.95,
          fillColor: '#3b82f6',
          fillOpacity: 0.55,
        },
        onEachFeature: (feature, lyr) => {
          lyr.bindPopup(
            '<div style="font-family:sans-serif;font-size:13px">' +
            '<b style="color:#1d4ed8">🌊 Inundated Flood Extent</b><br/>' +
            '<span style="color:#64748b">Detected via Sentinel satellite change analysis</span>' +
            '</div>'
          );
        },
      });

      floodLayer.addTo(map);
      floodLayerRef.current = floodLayer;
      layerControlRef.current?.addOverlay(floodLayer, '🌊 Flood Extent');

      try {
        const b = floodLayer.getBounds();
        if (b.isValid()) boundsToFit.push(b);
      } catch (_) {}
    }

    // 2. Update affected villages layer
    if (villagesLayerRef.current) {
      layerControlRef.current?.removeLayer(villagesLayerRef.current);
      map.removeLayer(villagesLayerRef.current);
      villagesLayerRef.current = null;
    }

    if (affectedVillagesGeoJSON && affectedVillagesGeoJSON.features && affectedVillagesGeoJSON.features.length > 0) {
      const villagesLayer = L.geoJSON(affectedVillagesGeoJSON, {
        style: {
          color: '#f59e0b',
          weight: 2.5,
          opacity: 0.9,
          fillColor: '#fef3c7',
          fillOpacity: 0.25,
          dashArray: '5, 5',
        },
        onEachFeature: (feature, lyr) => {
          const name = feature.properties?.name || feature.properties?.NAME || 'Affected Village';
          lyr.bindPopup(
            '<div style="font-family:sans-serif;font-size:13px">' +
            `<b style="color:#d97706">🏘️ ${name}</b><br/>` +
            '<span style="color:#64748b">Village boundary intersected by flood</span>' +
            '</div>'
          );
        },
      });

      villagesLayer.addTo(map);
      villagesLayerRef.current = villagesLayer;
      layerControlRef.current?.addOverlay(villagesLayer, '🏘️ Affected Villages');

      try {
        const b = villagesLayer.getBounds();
        if (b.isValid()) boundsToFit.push(b);
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
          color: '#ef4444',
          weight: 4,
          opacity: 0.9,
          dashArray: '4, 4',
        },
        onEachFeature: (feature, lyr) => {
          const name = feature.properties?.name || 'Road Segment';
          lyr.bindPopup(
            '<div style="font-family:sans-serif;font-size:13px">' +
            `<b style="color:#dc2626">🛣️ ${name}</b><br/>` +
            '<span style="color:#dc2626;font-weight:600">Flooded / Impassable</span>' +
            '</div>'
          );
        },
      });

      roadsLayer.addTo(map);
      roadsLayerRef.current = roadsLayer;
      layerControlRef.current?.addOverlay(roadsLayer, '🛣️ Inundated Roads');

      try {
        const b = roadsLayer.getBounds();
        if (b.isValid()) boundsToFit.push(b);
      } catch (_) {}
    }

    // 4. Update candidate evacuation sites markers
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
          html: '<div style="background:#10b981;border:2.5px solid white;border-radius:50%;width:16px;height:16px;box-shadow:0 0 6px rgba(0,0,0,0.6);cursor:pointer"></div>',
          iconSize: [16, 16],
          iconAnchor: [8, 8],
        });

        const marker = L.marker([c.lat, c.lon], { icon });
        marker.bindPopup(
          '<div style="font-family:sans-serif;font-size:13px;max-width:240px">' +
          `<b style="color:#059669;font-size:14px">🏫 ${c.name}</b><br/>` +
          `<b>Facility:</b> ${c.type}<br/>` +
          (c.distance_to_flood_km != null
            ? `<b>Distance to Flood:</b> ${c.distance_to_flood_km.toFixed(2)} km<br/>`
            : '') +
          (c.elevation_m != null
            ? `<b>DEM Elevation:</b> ${c.elevation_m.toFixed(1)} m<br/>`
            : '') +
          '<div style="font-size:11px;color:#d97706;margin-top:6px;line-height:1.3;border-top:1px solid #e2e8f0;padding-top:4px">' +
          '⚠️ <em>Candidate accessible site for on-ground verification. Not a verified safe shelter.</em>' +
          '</div>' +
          '</div>'
        );
        group.addLayer(marker);

        boundsToFit.push(L.latLngBounds([c.lat, c.lon], [c.lat, c.lon]));
      });

      group.addTo(map);
      evacuLayerRef.current = group;
      layerControlRef.current?.addOverlay(group, '🏫 Candidate Sites');
    }

    // 5. Fit bounds to combined extent of all active layers
    if (boundsToFit.length > 0) {
      let combined = boundsToFit[0];
      for (let i = 1; i < boundsToFit.length; i++) {
        combined = combined.extend(boundsToFit[i]);
      }
      if (combined.isValid()) {
        map.fitBounds(combined, { padding: [50, 50], maxZoom: 13 });
      }
    }

    map.invalidateSize();
  }, [floodGeoJSON, affectedVillagesGeoJSON, affectedRoadsGeoJSON, evacuationCandidates]);

  const hasData =
    (floodGeoJSON && floodGeoJSON.features && floodGeoJSON.features.length > 0) ||
    (affectedVillagesGeoJSON && affectedVillagesGeoJSON.features && affectedVillagesGeoJSON.features.length > 0) ||
    (evacuationCandidates && evacuationCandidates.length > 0);

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      {!hasData && (
        <div className="map-no-data">
          <span className="map-no-data-icon">🗺️</span>
          <span>Upload pre & post satellite GeoTIFFs and run analysis to view geospatial results</span>
        </div>
      )}

      <div ref={mapContainerRef} style={{ width: '100%', height: '100%' }} />

      {/* Map Legend */}
      {hasData && (
        <div className="map-legend">
          <div className="legend-item">
            <div className="legend-swatch" style={{ background: 'rgba(59,130,246,0.6)', border: '1.5px solid #1d4ed8' }} />
            <span>Flood Extent</span>
          </div>
          {affectedVillagesGeoJSON?.features?.length > 0 && (
            <div className="legend-item">
              <div className="legend-swatch" style={{ background: 'rgba(245,158,11,0.25)', border: '1.5px dashed #f59e0b' }} />
              <span>Affected Villages</span>
            </div>
          )}
          {affectedRoadsGeoJSON?.features?.length > 0 && (
            <div className="legend-item">
              <div className="legend-swatch" style={{ background: '#ef4444', height: '3px', marginTop: '5px' }} />
              <span>Inundated Roads</span>
            </div>
          )}
          {evacuationCandidates?.length > 0 && (
            <div className="legend-item">
              <div className="legend-swatch" style={{ background: '#10b981', borderRadius: '50%', border: '2px solid white' }} />
              <span>Candidate Site (Unverified)</span>
            </div>
          )}
          <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginTop: 5, borderTop: '1px solid var(--border)', paddingTop: 4 }}>
            Toggle layers via top-right control
          </div>
        </div>
      )}
    </div>
  );
}
