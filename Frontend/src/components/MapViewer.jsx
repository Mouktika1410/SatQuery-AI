import React, { useEffect, useRef, useState, useCallback } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

export default function MapViewer({
  floodGeoJSON,
  floodMetrics,
  evacuationCandidates,
  affectedVillages,
  affectedVillagesGeoJSON,
  affectedRoadsGeoJSON,
  priorityScores,
  selectedFeature,
  onSelectFeature,
}) {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const floodLayerRef = useRef(null);
  const villagesLayerRef = useRef(null);
  const roadsLayerRef = useRef(null);
  const evacuLayerRef = useRef(null);
  const layerControlRef = useRef(null);
  const baseLayersRef = useRef({});
  const overlayLayersRef = useRef({});
  const lastAnalysisBoundsRef = useRef(null);

  // Active layer visibility state for custom legend toggles if needed
  const [activeLayers, setActiveLayers] = useState({
    flood: true,
    villages: true,
    roads: true,
    evac: true,
  });

  // Track fullscreen state safely
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Initialize Leaflet map once
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    const map = L.map(mapContainerRef.current, {
      center: [20.5937, 78.9629], // Center over India as broad neutral baseline
      zoom: 5,
      zoomControl: false, // We will add a custom zoom control with clean position
      attributionControl: true,
    });

    // Custom Zoom control top-left
    L.control.zoom({ position: 'topleft' }).addTo(map);

    // Base tile layers: Esri World Imagery Satellite & OpenStreetMap
    const osm = L.tileLayer(
      'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
      {
        attribution: '© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a>',
        maxZoom: 19,
      }
    );

    const satellite = L.tileLayer(
      'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      {
        attribution: '© <a href="https://www.esri.com" target="_blank" rel="noreferrer">Esri Satellite</a>',
        maxZoom: 18,
      }
    );

    // Default to Satellite basemap
    satellite.addTo(map);

    const baseMaps = {
      '🛰️ Satellite': satellite,
      '🗺️ Street Map': osm,
    };
    baseLayersRef.current = baseMaps;

    const overlayMaps = {};
    overlayLayersRef.current = overlayMaps;

    const layerControl = L.control.layers(baseMaps, overlayMaps, {
      position: 'topright',
      collapsed: false,
    });
    layerControl.addTo(map);
    layerControlRef.current = layerControl;

    // Track layer add/remove to keep legend synced
    map.on('overlayadd', (e) => {
      if (e.name.includes('Flood')) setActiveLayers((prev) => ({ ...prev, flood: true }));
      if (e.name.includes('Villages')) setActiveLayers((prev) => ({ ...prev, villages: true }));
      if (e.name.includes('Roads')) setActiveLayers((prev) => ({ ...prev, roads: true }));
      if (e.name.includes('Candidate')) setActiveLayers((prev) => ({ ...prev, evac: true }));
    });

    map.on('overlayremove', (e) => {
      if (e.name.includes('Flood')) setActiveLayers((prev) => ({ ...prev, flood: false }));
      if (e.name.includes('Villages')) setActiveLayers((prev) => ({ ...prev, villages: false }));
      if (e.name.includes('Roads')) setActiveLayers((prev) => ({ ...prev, roads: false }));
      if (e.name.includes('Candidate')) setActiveLayers((prev) => ({ ...prev, evac: false }));
    });

    mapInstanceRef.current = map;

    // Trigger map size recalculation
    setTimeout(() => {
      map.invalidateSize();
    }, 250);

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  // Reset / Fit to Analysis Extent handler
  const handleResetBounds = useCallback(() => {
    const map = mapInstanceRef.current;
    if (map && lastAnalysisBoundsRef.current && lastAnalysisBoundsRef.current.isValid()) {
      map.fitBounds(lastAnalysisBoundsRef.current, { padding: [45, 45], maxZoom: 13, animate: true });
    }
  }, []);

  // Toggle Fullscreen safely
  const handleToggleFullscreen = useCallback(() => {
    const el = mapContainerRef.current?.parentElement;
    if (!el) return;

    if (!document.fullscreenElement) {
      el.requestFullscreen?.().then(() => {
        setIsFullscreen(true);
        setTimeout(() => mapInstanceRef.current?.invalidateSize(), 200);
      }).catch(() => {});
    } else {
      document.exitFullscreen?.().then(() => {
        setIsFullscreen(false);
        setTimeout(() => mapInstanceRef.current?.invalidateSize(), 200);
      }).catch(() => {});
    }
  }, []);

  // Build lookups for fast access
  const priorityLookup = useRef({});
  useEffect(() => {
    const lookup = {};
    if (priorityScores && Array.isArray(priorityScores)) {
      priorityScores.forEach((p) => {
        if (p.village_name) {
          lookup[p.village_name.toLowerCase().trim()] = p;
        }
      });
    }
    priorityLookup.current = lookup;
  }, [priorityScores]);

  const villageLookup = useRef({});
  useEffect(() => {
    const lookup = {};
    if (affectedVillages && Array.isArray(affectedVillages)) {
      affectedVillages.forEach((v) => {
        if (v.name) {
          lookup[v.name.toLowerCase().trim()] = v;
        }
      });
    }
    villageLookup.current = lookup;
  }, [affectedVillages]);

  // Update layers and fit bounds whenever pipeline results update
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    let combinedBounds = null;

    // -------------------------------------------------------------------------
    // 1. FLOOD EXTENT LAYER
    // -------------------------------------------------------------------------
    if (floodLayerRef.current) {
      try {
        layerControlRef.current?.removeLayer(floodLayerRef.current);
        map.removeLayer(floodLayerRef.current);
      } catch (_) {}
      floodLayerRef.current = null;
    }

    if (floodGeoJSON && floodGeoJSON.features && floodGeoJSON.features.length > 0) {
      const areaVal = floodMetrics?.areaKm2 != null ? Number(floodMetrics.areaKm2).toFixed(2) : null;
      const areaStr = areaVal ? `${areaVal} km²` : 'Calculated Extent';
      const pctStr = floodMetrics?.floodPercentage != null ? `${Number(floodMetrics.floodPercentage).toFixed(2)}%` : null;
      const countStr = floodMetrics?.polygonCount != null ? floodMetrics.polygonCount : floodGeoJSON.features.length;

      const floodLayer = L.geoJSON(floodGeoJSON, {
        style: {
          color: '#1e40af', // Deep blue border
          weight: 2.5,
          opacity: 0.95,
          fillColor: '#3b82f6', // Vivid blue flood fill
          fillOpacity: 0.52,
        },
        onEachFeature: (feature, lyr) => {
          // Hover highlighting
          lyr.on({
            mouseover: (e) => {
              const layer = e.target;
              layer.setStyle({
                fillColor: '#60a5fa',
                fillOpacity: 0.70,
                weight: 3.5,
                color: '#1d4ed8',
              });
            },
            mouseout: (e) => {
              floodLayer.resetStyle(e.target);
            },
          });

          // Informative popup
          lyr.bindPopup(
            '<div class="gis-popup flood-popup">' +
              '<div class="gis-popup-header">' +
                '<span class="gis-popup-icon">🌊</span>' +
                '<div class="gis-popup-title">Detected Flood Extent</div>' +
              '</div>' +
              '<div class="gis-popup-body">' +
                '<div class="gis-popup-row">' +
                  '<span class="gis-popup-label">Flooded Area:</span>' +
                  `<span class="gis-popup-val highlight-blue">${areaStr}</span>` +
                '</div>' +
                (pctStr
                  ? '<div class="gis-popup-row">' +
                      '<span class="gis-popup-label">Image Coverage:</span>' +
                      `<span class="gis-popup-val">${pctStr}</span>` +
                    '</div>'
                  : '') +
                '<div class="gis-popup-row">' +
                  '<span class="gis-popup-label">Polygons Count:</span>' +
                  `<span class="gis-popup-val">${countStr}</span>` +
                '</div>' +
                '<div class="gis-popup-footnote">Generated via satellite water-detection and vector simplification</div>' +
              '</div>' +
            '</div>',
            { maxWidth: 260 }
          );
        },
      });

      floodLayer.addTo(map);
      floodLayerRef.current = floodLayer;
      layerControlRef.current?.addOverlay(floodLayer, '🌊 Flood Extent');

      try {
        const b = floodLayer.getBounds();
        if (b && b.isValid()) {
          combinedBounds = combinedBounds ? combinedBounds.extend(b) : b;
        }
      } catch (_) {}
    }

    // -------------------------------------------------------------------------
    // 2. INTERACTIVE VILLAGES LAYER
    // -------------------------------------------------------------------------
    if (villagesLayerRef.current) {
      try {
        layerControlRef.current?.removeLayer(villagesLayerRef.current);
        map.removeLayer(villagesLayerRef.current);
      } catch (_) {}
      villagesLayerRef.current = null;
    }

    if (affectedVillagesGeoJSON && affectedVillagesGeoJSON.features && affectedVillagesGeoJSON.features.length > 0) {
      const villagesLayer = L.geoJSON(affectedVillagesGeoJSON, {
        style: (feature) => {
          const vName = (feature?.properties?.name || feature?.properties?.NAME || '').toLowerCase().trim();
          const isSelected = selectedFeature?.type === 'village' && selectedFeature?.name?.toLowerCase().trim() === vName;

          return {
            color: isSelected ? '#ef4444' : '#d97706', // Red highlight if selected, else amber
            weight: isSelected ? 4 : 2.5,
            opacity: 0.95,
            fillColor: isSelected ? '#f87171' : '#fef3c7',
            fillOpacity: isSelected ? 0.45 : 0.22,
            dashArray: isSelected ? undefined : '5, 5',
          };
        },
        onEachFeature: (feature, lyr) => {
          const rawName = feature.properties?.name || feature.properties?.NAME || 'Affected Village';
          const cleanKey = rawName.toLowerCase().trim();
          const vData = villageLookup.current[cleanKey];
          const pData = priorityLookup.current[cleanKey];

          const floodedKm2 = vData?.area_flooded_km2 != null ? `${vData.area_flooded_km2.toFixed(2)} km²` : null;
          const popEst = vData?.population_affected != null ? vData.population_affected.toLocaleString() : null;
          const rank = pData?.rank != null ? `#${pData.rank}` : null;
          const score = pData?.priority_score != null ? pData.priority_score.toFixed(3) : null;

          // Interactive Hover & Click
          lyr.on({
            mouseover: (e) => {
              const layer = e.target;
              layer.setStyle({
                fillOpacity: 0.40,
                weight: 3.5,
                color: '#b45309',
              });
            },
            mouseout: (e) => {
              villagesLayer.resetStyle(e.target);
            },
            click: () => {
              if (onSelectFeature) {
                onSelectFeature({ type: 'village', name: rawName, data: { ...vData, ...pData } });
              }
            },
          });

          // Detailed Grounded Popup
          lyr.bindPopup(
            '<div class="gis-popup village-popup">' +
              '<div class="gis-popup-header">' +
                '<span class="gis-popup-icon">🏘️</span>' +
                `<div class="gis-popup-title">${rawName}</div>` +
                (rank ? `<span class="gis-popup-badge badge-amber">Rank ${rank}</span>` : '') +
              '</div>' +
              '<div class="gis-popup-body">' +
                (floodedKm2
                  ? '<div class="gis-popup-row">' +
                      '<span class="gis-popup-label">Flooded Inundation:</span>' +
                      `<span class="gis-popup-val highlight-amber">${floodedKm2}</span>` +
                    '</div>'
                  : '') +
                (score
                  ? '<div class="gis-popup-row">' +
                      '<span class="gis-popup-label">Urgency Score:</span>' +
                      `<span class="gis-popup-val font-mono">${score}</span>` +
                    '</div>'
                  : '') +
                (popEst
                  ? '<div class="gis-popup-row">' +
                      '<span class="gis-popup-label">Estimated Pop Affected:</span>' +
                      `<span class="gis-popup-val">${popEst}</span>` +
                    '</div>'
                  : '') +
                '<div class="gis-popup-footnote alert-box">' +
                  '⚠️ Heuristic decision-support score from spatial overlay. Field verification advised.' +
                '</div>' +
              '</div>' +
            '</div>',
            { maxWidth: 280 }
          );
        },
      });

      villagesLayer.addTo(map);
      villagesLayerRef.current = villagesLayer;
      layerControlRef.current?.addOverlay(villagesLayer, '🏘️ Affected Villages');

      try {
        const b = villagesLayer.getBounds();
        if (b && b.isValid()) {
          combinedBounds = combinedBounds ? combinedBounds.extend(b) : b;
        }
      } catch (_) {}
    }

    // -------------------------------------------------------------------------
    // 3. AFFECTED ROADS LAYER
    // -------------------------------------------------------------------------
    if (roadsLayerRef.current) {
      try {
        layerControlRef.current?.removeLayer(roadsLayerRef.current);
        map.removeLayer(roadsLayerRef.current);
      } catch (_) {}
      roadsLayerRef.current = null;
    }

    if (affectedRoadsGeoJSON && affectedRoadsGeoJSON.features && affectedRoadsGeoJSON.features.length > 0) {
      const roadsLayer = L.geoJSON(affectedRoadsGeoJSON, {
        style: {
          color: '#dc2626', // Bright high-contrast red
          weight: 4.5,
          opacity: 0.95,
          dashArray: '5, 4',
        },
        onEachFeature: (feature, lyr) => {
          const roadName = feature.properties?.name || 'Inundated Road Corridor';
          const highwayType = feature.properties?.highway || feature.properties?.type || 'Road Network';

          lyr.on({
            mouseover: (e) => {
              e.target.setStyle({ weight: 6.5, color: '#b91c1c' });
            },
            mouseout: (e) => {
              roadsLayer.resetStyle(e.target);
            },
          });

          lyr.bindPopup(
            '<div class="gis-popup road-popup">' +
              '<div class="gis-popup-header">' +
                '<span class="gis-popup-icon">🛣️</span>' +
                `<div class="gis-popup-title">${roadName}</div>` +
              '</div>' +
              '<div class="gis-popup-body">' +
                '<div class="gis-popup-row">' +
                  '<span class="gis-popup-label">Corridor Classification:</span>' +
                  `<span class="gis-popup-val font-mono">${highwayType}</span>` +
                '</div>' +
                '<div class="gis-popup-status-badge road-status-badge">' +
                  '⚠️ Inundated / Submerged Segment — Impassable' +
                '</div>' +
                '<div class="gis-popup-footnote">Road vector geometry intersected with detected flood boundary</div>' +
              '</div>' +
            '</div>',
            { maxWidth: 260 }
          );
        },
      });

      roadsLayer.addTo(map);
      roadsLayerRef.current = roadsLayer;
      layerControlRef.current?.addOverlay(roadsLayer, '🛣️ Inundated Roads');

      try {
        const b = roadsLayer.getBounds();
        if (b && b.isValid()) {
          combinedBounds = combinedBounds ? combinedBounds.extend(b) : b;
        }
      } catch (_) {}
    }

    // -------------------------------------------------------------------------
    // 4. EVACUATION CANDIDATE SITES LAYER
    // -------------------------------------------------------------------------
    if (evacuLayerRef.current) {
      try {
        layerControlRef.current?.removeLayer(evacuLayerRef.current);
        map.removeLayer(evacuLayerRef.current);
      } catch (_) {}
      evacuLayerRef.current = null;
    }

    if (evacuationCandidates && evacuationCandidates.length > 0) {
      const group = L.layerGroup();

      evacuationCandidates.forEach((c) => {
        if (c.lat == null || c.lon == null) return;

        const isSelected = selectedFeature?.type === 'evac' && selectedFeature?.name?.toLowerCase().trim() === c.name?.toLowerCase().trim();

        // High-visibility green pin with shadow
        const icon = L.divIcon({
          className: 'custom-evac-marker-wrapper',
          html: (
            `<div class="custom-evac-pin ${isSelected ? 'selected-pin' : ''}">` +
              '<span>✓</span>' +
            '</div>'
          ),
          iconSize: [22, 22],
          iconAnchor: [11, 11],
          popupAnchor: [0, -10],
        });

        const marker = L.marker([c.lat, c.lon], { icon });

        marker.on('click', () => {
          if (onSelectFeature) {
            onSelectFeature({ type: 'evac', name: c.name, data: c });
          }
        });

        const distStr = c.distance_to_flood_km != null ? `${c.distance_to_flood_km.toFixed(2)} km` : 'Outside Flood Zone';
        const elevStr = c.elevation_m != null ? `${c.elevation_m.toFixed(1)} m (DEM)` : null;
        const coordsStr = `${c.lat.toFixed(4)}°N, ${c.lon.toFixed(4)}°E`;

        marker.bindPopup(
          '<div class="gis-popup evac-popup">' +
            '<div class="gis-popup-header">' +
              '<span class="gis-popup-icon">🏫</span>' +
              `<div class="gis-popup-title">${c.name}</div>` +
              `<span class="gis-popup-badge badge-green">${c.type}</span>` +
            '</div>' +
            '<div class="gis-popup-body">' +
              '<div class="gis-popup-row">' +
                '<span class="gis-popup-label">Distance to Flood:</span>' +
                `<span class="gis-popup-val highlight-green">${distStr}</span>` +
              '</div>' +
              (elevStr
                ? '<div class="gis-popup-row">' +
                    '<span class="gis-popup-label">Elevation:</span>' +
                    `<span class="gis-popup-val">${elevStr}</span>` +
                  '</div>'
                : '') +
              '<div class="gis-popup-row">' +
                '<span class="gis-popup-label">Coordinates:</span>' +
                `<span class="gis-popup-val font-mono" style="font-size:11px">${coordsStr}</span>` +
              '</div>' +
              '<div class="gis-popup-footnote alert-box-warning">' +
                '⚠️ <b>CANDIDATE SITE ONLY:</b> Requires on-ground physical inspection. NOT a verified shelter.' +
              '</div>' +
            '</div>' +
          '</div>',
          { maxWidth: 280 }
        );

        group.addLayer(marker);

        const pointBounds = L.latLngBounds([L.latLng(c.lat, c.lon), L.latLng(c.lat, c.lon)]);
        combinedBounds = combinedBounds ? combinedBounds.extend(pointBounds) : pointBounds;
      });

      group.addTo(map);
      evacuLayerRef.current = group;
      layerControlRef.current?.addOverlay(group, '🏫 Evacuation Sites');
    }

    // -------------------------------------------------------------------------
    // 5. FIT BOUNDS SMOOTHLY TO DETECTED EXTENT
    // -------------------------------------------------------------------------
    if (combinedBounds && combinedBounds.isValid()) {
      lastAnalysisBoundsRef.current = combinedBounds;
      try {
        map.fitBounds(combinedBounds, { padding: [40, 40], maxZoom: 13, animate: true });
      } catch (_) {}
    }

    map.invalidateSize();
  }, [
    floodGeoJSON,
    floodMetrics,
    affectedVillagesGeoJSON,
    affectedRoadsGeoJSON,
    evacuationCandidates,
    selectedFeature,
    onSelectFeature,
  ]);

  const hasData =
    (floodGeoJSON && floodGeoJSON.features && floodGeoJSON.features.length > 0) ||
    (affectedVillagesGeoJSON && affectedVillagesGeoJSON.features && affectedVillagesGeoJSON.features.length > 0) ||
    (affectedRoadsGeoJSON && affectedRoadsGeoJSON.features && affectedRoadsGeoJSON.features.length > 0) ||
    (evacuationCandidates && evacuationCandidates.length > 0);

  return (
    <div className={`map-wrapper ${isFullscreen ? 'fullscreen' : ''}`}>
      {!hasData && (
        <div className="map-no-data">
          <span className="map-no-data-icon">🛰️</span>
          <div style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '0.95rem' }}>
            Interactive GIS Flood Analysis Map
          </div>
          <span>Upload pre & post satellite GeoTIFFs and click Run Flood Analysis to inspect spatial results.</span>
        </div>
      )}

      {/* Main Map Container */}
      <div ref={mapContainerRef} className="leaflet-map-container" />

      {/* Floating Map Toolbar Controls (Zoom, Fit Bounds, Fullscreen) */}
      <div className="map-action-toolbar">
        {hasData && (
          <button
            className="map-tool-btn"
            onClick={handleResetBounds}
            title="Fit to analysis extent"
            aria-label="Fit to analysis extent"
          >
            🎯 <span className="btn-text">Reset Extent</span>
          </button>
        )}
        <button
          className="map-tool-btn"
          onClick={handleToggleFullscreen}
          title={isFullscreen ? 'Exit Fullscreen' : 'View Fullscreen'}
          aria-label="Toggle Fullscreen"
        >
          {isFullscreen ? '✕ Exit' : '⛶ Fullscreen'}
        </button>
      </div>

      {/* Active Selection Indicator */}
      {selectedFeature && (
        <div className="map-selection-banner">
          <span>Selected {selectedFeature.type === 'village' ? '🏘️ Village' : '🏫 Site'}: <b>{selectedFeature.name}</b></span>
          <button
            className="banner-close-btn"
            onClick={() => onSelectFeature && onSelectFeature(null)}
            title="Clear selection"
          >
            ✕
          </button>
        </div>
      )}

      {/* Structured GIS Map Legend */}
      {hasData && (
        <div className="map-legend">
          <div className="legend-title-row">
            <span>🗺️ GIS Layers</span>
            <span className="legend-indicator">EPSG:4326</span>
          </div>

          <div className={`legend-item ${activeLayers.flood ? '' : 'layer-off'}`}>
            <div className="legend-swatch swatch-flood" />
            <div className="legend-label-col">
              <span className="layer-name">Flood Extent</span>
              {floodMetrics?.areaKm2 != null && (
                <span className="layer-subtext">{Number(floodMetrics.areaKm2).toFixed(1)} km²</span>
              )}
            </div>
          </div>

          {affectedVillagesGeoJSON?.features?.length > 0 && (
            <div className={`legend-item ${activeLayers.villages ? '' : 'layer-off'}`}>
              <div className="legend-swatch swatch-village" />
              <div className="legend-label-col">
                <span className="layer-name">Affected Villages</span>
                <span className="layer-subtext">{affectedVillagesGeoJSON.features.length} zones</span>
              </div>
            </div>
          )}

          {affectedRoadsGeoJSON?.features?.length > 0 && (
            <div className={`legend-item ${activeLayers.roads ? '' : 'layer-off'}`}>
              <div className="legend-swatch swatch-road" />
              <div className="legend-label-col">
                <span className="layer-name">Inundated Roads</span>
                <span className="layer-subtext">Impassable segments</span>
              </div>
            </div>
          )}

          {evacuationCandidates?.length > 0 && (
            <div className={`legend-item ${activeLayers.evac ? '' : 'layer-off'}`}>
              <div className="legend-swatch swatch-evac" />
              <div className="legend-label-col">
                <span className="layer-name">Candidate Evac Sites</span>
                <span className="layer-subtext">{evacuationCandidates.length} unverified</span>
              </div>
            </div>
          )}

          <div className="legend-footer">
            Click features for metrics · Top-right to toggle
          </div>
        </div>
      )}
    </div>
  );
}

