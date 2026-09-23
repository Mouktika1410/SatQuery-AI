import React, { useEffect, useRef, useState, useCallback } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

export default function MapViewer({
  mode = 'overview', // 'overview' | 'impact'
  floodGeoJSON,
  floodMetrics,
  centroid,
  populationGeoJSON,
  exposedPopulation,
  buildingsGeoJSON,
  affectedBuildings,
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
  const popLayerRef = useRef(null);
  const bldLayerRef = useRef(null);
  const villagesLayerRef = useRef(null);
  const roadsLayerRef = useRef(null);
  const evacuLayerRef = useRef(null);
  const centMarkerRef = useRef(null);
  const layerControlRef = useRef(null);
  const baseLayersRef = useRef({});
  const overlayLayersRef = useRef({});
  const lastAnalysisBoundsRef = useRef(null);

  const [isFullscreen, setIsFullscreen] = useState(false);

  // Initialize Leaflet map once
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    const map = L.map(mapContainerRef.current, {
      center: [20.5937, 78.9629],
      zoom: 5,
      zoomControl: false,
      attributionControl: true,
    });

    L.control.zoom({ position: 'topleft' }).addTo(map);

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

    satellite.addTo(map);

    const baseMaps = {
      'Satellite': satellite,
      'Street Map': osm,
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

    mapInstanceRef.current = map;

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
      map.fitBounds(lastAnalysisBoundsRef.current, { padding: [35, 35], maxZoom: 15, animate: true });
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

  // Update GIS Layers whenever props change
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    let floodBounds = null;
    let fallbackBounds = null;

    // -------------------------------------------------------------------------
    // 1. FLOOD EXTENT LAYER (ONE MAIN VISUAL FOCUS)
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
      const countStr = floodMetrics?.polygonCount != null ? floodMetrics.polygonCount : floodGeoJSON.features.length;

      const floodLayer = L.geoJSON(floodGeoJSON, {
        style: {
          color: '#00e5ff', // Vivid cyan border
          weight: 2.5,
          opacity: 0.95,
          fillColor: '#0284c7', // Translucent blue/cyan fill
          fillOpacity: 0.55,
        },
        onEachFeature: (feature, lyr) => {
          lyr.on({
            mouseover: (e) => {
              e.target.setStyle({
                fillColor: '#38bdf8',
                fillOpacity: 0.75,
                weight: 3.5,
                color: '#00ffff',
              });
            },
            mouseout: (e) => {
              floodLayer.resetStyle(e.target);
            },
          });

          lyr.bindPopup(
            '<div class="gis-popup flood-popup">' +
              '<div class="gis-popup-header">' +
                '<div class="gis-popup-title">Detected Flood Extent</div>' +
                '<span class="gis-popup-badge" style="background:#0284c7; color:#fff;">SATELLITE DETECTED</span>' +
              '</div>' +
              '<div class="gis-popup-body">' +
                '<div class="gis-popup-row">' +
                  '<span class="gis-popup-label">Flooded Area:</span>' +
                  `<span class="gis-popup-val" style="color:#0284c7; font-weight:700;">${areaStr}</span>` +
                '</div>' +
                '<div class="gis-popup-row">' +
                  '<span class="gis-popup-label">Polygon Count:</span>' +
                  `<span class="gis-popup-val">${countStr}</span>` +
                '</div>' +
                '<div class="gis-popup-footnote">Generated via GEE Sentinel-1 SAR change detection</div>' +
              '</div>' +
            '</div>',
            { maxWidth: 260 }
          );
        },
      });

      floodLayer.addTo(map);
      floodLayerRef.current = floodLayer;
      layerControlRef.current?.addOverlay(floodLayer, '🌊 Flooded Area');

      try {
        const b = floodLayer.getBounds();
        if (b && b.isValid()) {
          floodBounds = b;
        }
      } catch (_) {}
    }

    // -------------------------------------------------------------------------
    // 2. CENTROID MARKER
    // -------------------------------------------------------------------------
    if (centMarkerRef.current) {
      try {
        map.removeLayer(centMarkerRef.current);
      } catch (_) {}
      centMarkerRef.current = null;
    }

    if (centroid && centroid.latitude != null && centroid.longitude != null) {
      const centIcon = L.divIcon({
        className: 'custom-centroid-marker-wrapper',
        html: (
          '<div class="custom-centroid-pin" title="Flood Centroid" style="background:#475569; width:20px; height:20px; border-radius:50%; border:2px solid #ffffff; box-shadow:0 0 8px rgba(0,0,0,0.5); display:flex; align-items:center; justify-content:center; color:#fff; font-size:10px;">' +
            '📍' +
          '</div>'
        ),
        iconSize: [20, 20],
        iconAnchor: [10, 10],
        popupAnchor: [0, -10],
      });

      const centMarker = L.marker([centroid.latitude, centroid.longitude], { icon: centIcon });
      centMarker.bindPopup(
        '<div class="gis-popup centroid-popup">' +
          '<div class="gis-popup-header">' +
            '<div class="gis-popup-title">Flood Extent Centroid</div>' +
          '</div>' +
          '<div class="gis-popup-body">' +
            '<div class="gis-popup-row">' +
              '<span class="gis-popup-label">Latitude:</span>' +
              `<span class="gis-popup-val">${centroid.latitude.toFixed(6)}° N</span>` +
            '</div>' +
            '<div class="gis-popup-row">' +
              '<span class="gis-popup-label">Longitude:</span>' +
              `<span class="gis-popup-val">${centroid.longitude.toFixed(6)}° E</span>` +
            '</div>' +
            '<div class="gis-popup-footnote">Geographic centroid of detected flood polygon</div>' +
          '</div>' +
        '</div>',
        { maxWidth: 240 }
      );

      centMarker.addTo(map);
      centMarkerRef.current = centMarker;

      const pBounds = L.latLngBounds([
        L.latLng(centroid.latitude, centroid.longitude),
        L.latLng(centroid.latitude, centroid.longitude)
      ]);
      fallbackBounds = fallbackBounds ? fallbackBounds.extend(pBounds) : pBounds;
    }

    // -------------------------------------------------------------------------
    // 3. REAL AFFECTED VILLAGE/ADMINISTRATIVE BOUNDARIES WITH LABELS
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
            color: isSelected ? '#ef4444' : '#f59e0b', // Amber boundary stroke
            weight: isSelected ? 3.5 : 2.2,
            opacity: 0.95,
            fillColor: '#fbbf24',
            fillOpacity: 0.18,
            dashArray: '5, 5',
          };
        },
        onEachFeature: (feature, lyr) => {
          const rawName = feature.properties?.name || feature.properties?.NAME || 'Affected Village';
          const cleanKey = rawName.toLowerCase().trim();
          const vData = villageLookup.current[cleanKey];

          // Permanent clear label over village center on map
          lyr.bindTooltip(
            `<div class="village-map-label">🏘️ ${rawName}</div>`,
            {
              permanent: true,
              direction: 'center',
              className: 'custom-village-label',
            }
          );

          lyr.on({
            mouseover: (e) => {
              e.target.setStyle({ weight: 3.5, fillOpacity: 0.35, color: '#d97706' });
            },
            mouseout: (e) => {
              villagesLayer.resetStyle(e.target);
            },
            click: () => {
              if (onSelectFeature) {
                onSelectFeature({ type: 'village', name: rawName, data: vData });
              }
            },
          });

          lyr.bindPopup(
            '<div class="gis-popup village-popup">' +
              '<div class="gis-popup-header">' +
                `<div class="gis-popup-title">${rawName}</div>` +
                '<span class="gis-popup-badge" style="background:#f59e0b; color:#fff;">AFFECTED DIVISION</span>' +
              '</div>' +
              '<div class="gis-popup-body">' +
                '<div class="gis-popup-row">' +
                  '<span class="gis-popup-label">District / Taluk:</span>' +
                  `<span class="gis-popup-val">${feature.properties?.district || 'Kottayam'} / ${feature.properties?.taluk || 'Kottayam'}</span>` +
                '</div>' +
                '<div class="gis-popup-row">' +
                  '<span class="gis-popup-label">Boundary Status:</span>' +
                  '<span class="gis-popup-val" style="color:#d97706; font-weight:700;">Intersecting Flood Extent</span>' +
                '</div>' +
              '</div>' +
            '</div>',
            { maxWidth: 260 }
          );
        },
      });

      villagesLayer.addTo(map);
      villagesLayerRef.current = villagesLayer;
      layerControlRef.current?.addOverlay(villagesLayer, '🏘️ Affected Villages');
    }

    // -------------------------------------------------------------------------
    // 4. IMPACT ANALYSIS LAYERS (PEOPLE, BUILDINGS, ROADS) - ONLY IN IMPACT MODE
    // -------------------------------------------------------------------------
    if (popLayerRef.current) {
      try {
        layerControlRef.current?.removeLayer(popLayerRef.current);
        map.removeLayer(popLayerRef.current);
      } catch (_) {}
      popLayerRef.current = null;
    }

    if (bldLayerRef.current) {
      try {
        layerControlRef.current?.removeLayer(bldLayerRef.current);
        map.removeLayer(bldLayerRef.current);
      } catch (_) {}
      bldLayerRef.current = null;
    }

    if (roadsLayerRef.current) {
      try {
        layerControlRef.current?.removeLayer(roadsLayerRef.current);
        map.removeLayer(roadsLayerRef.current);
      } catch (_) {}
      roadsLayerRef.current = null;
    }

    if (mode === 'impact') {
      // Population
      if (populationGeoJSON && populationGeoJSON.features && populationGeoJSON.features.length > 0) {
        const exposedPopFeatures = populationGeoJSON.features.filter((f) => f.properties?.is_exposed === true);
        const popGroup = L.layerGroup();
        exposedPopFeatures.forEach((feature) => {
          const popVal = feature.properties?.population != null ? Number(feature.properties.population) : 0;
          if (popVal <= 0) return;
          let cLat = null, cLng = null;
          try {
            const b = L.geoJSON(feature).getBounds();
            if (b && b.isValid()) {
              const c = b.getCenter();
              cLat = c.lat; cLng = c.lng;
            }
          } catch (_) {}
          if (cLat == null || cLng == null) return;
          const formattedPop = popVal >= 1000 ? `${(popVal / 1000).toFixed(1)}k` : popVal.toLocaleString();
          const personIcon = L.divIcon({
            className: 'custom-pop-marker-wrapper',
            html: `<div class="custom-pop-badge" title="${popVal.toLocaleString()} exposed people"><span class="pop-icon">👥</span><span class="pop-count">${formattedPop}</span></div>`,
            iconSize: [52, 22],
            iconAnchor: [26, 11],
            popupAnchor: [0, -10],
          });
          const marker = L.marker([cLat, cLng], { icon: personIcon });
          marker.bindPopup(`<div class="gis-popup pop-popup"><div class="gis-popup-header"><div class="gis-popup-title">Exposed Population</div></div><div class="gis-popup-body"><div class="gis-popup-row"><span class="gis-popup-label">Exposed People:</span><span class="gis-popup-val" style="color:#e11d48; font-weight:700;">${popVal.toLocaleString()} people</span></div></div></div>`, { maxWidth: 260 });
          popGroup.addLayer(marker);
        });
        popGroup.addTo(map);
        popLayerRef.current = popGroup;
        layerControlRef.current?.addOverlay(popGroup, '👥 People Exposed');
      }

      // Buildings
      if (buildingsGeoJSON && buildingsGeoJSON.features && buildingsGeoJSON.features.length > 0) {
        const exposedBldFeatures = buildingsGeoJSON.features.filter((f) => f.properties?.is_exposed === true);
        const bldGeoJSONToRender = exposedBldFeatures.length > 0 ? { ...buildingsGeoJSON, features: exposedBldFeatures } : buildingsGeoJSON;
        const bldLayer = L.geoJSON(bldGeoJSONToRender, {
          style: { color: '#d97706', weight: 1.6, opacity: 0.95, fillColor: '#f59e0b', fillOpacity: 0.7 },
        });
        bldLayer.addTo(map);
        bldLayerRef.current = bldLayer;
        layerControlRef.current?.addOverlay(bldLayer, '🏠 Affected Buildings');
      }

      // Roads
      if (affectedRoadsGeoJSON && affectedRoadsGeoJSON.features && affectedRoadsGeoJSON.features.length > 0) {
        const roadsLayer = L.geoJSON(affectedRoadsGeoJSON, {
          style: { color: '#ef4444', weight: 3.5, opacity: 0.95, dashArray: '6, 6' },
        });
        roadsLayer.addTo(map);
        roadsLayerRef.current = roadsLayer;
        layerControlRef.current?.addOverlay(roadsLayer, '🛣️ Affected Roads');
      }
    }

    // -------------------------------------------------------------------------
    // 5. AUTOMATICALLY ZOOM TIGHTLY TO DETECTED FLOOD POLYGON BOUNDS
    // -------------------------------------------------------------------------
    const targetBounds = (floodBounds && floodBounds.isValid()) ? floodBounds : fallbackBounds;

    if (targetBounds && targetBounds.isValid()) {
      lastAnalysisBoundsRef.current = targetBounds;
      setTimeout(() => {
        try {
          map.invalidateSize();
          map.flyToBounds(targetBounds, { padding: [35, 35], maxZoom: 15, duration: 1.2 });
        } catch (_) {
          try {
            map.fitBounds(targetBounds, { padding: [30, 30], maxZoom: 15 });
          } catch (e) {}
        }
      }, 50);
    } else {
      map.invalidateSize();
    }
  }, [
    mode,
    floodGeoJSON,
    floodMetrics,
    centroid,
    populationGeoJSON,
    exposedPopulation,
    buildingsGeoJSON,
    affectedBuildings,
    affectedVillagesGeoJSON,
    affectedRoadsGeoJSON,
    evacuationCandidates,
    selectedFeature,
    onSelectFeature,
  ]);

  const hasData =
    (floodGeoJSON && floodGeoJSON.features && floodGeoJSON.features.length > 0) ||
    (affectedVillagesGeoJSON && affectedVillagesGeoJSON.features && affectedVillagesGeoJSON.features.length > 0);

  return (
    <div className={`map-wrapper ${isFullscreen ? 'fullscreen' : ''}`}>
      {!hasData && (
        <div className="map-no-data">
          <div style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '0.95rem' }}>
            Interactive Disaster Analysis Map
          </div>
          <span>Upload pre & post satellite GeoTIFFs and run Flood Analysis to view spatial results.</span>
        </div>
      )}

      {/* Main Map Container */}
      <div ref={mapContainerRef} className="leaflet-map-container" />

      {/* Floating Map Toolbar Controls */}
      <div className="map-action-toolbar">
        {hasData && (
          <button
            className="map-tool-btn"
            onClick={handleResetBounds}
            title="Fit map tightly to flood bounds"
            aria-label="Fit to flood extent"
          >
            <span className="btn-text">Reset Extent</span>
          </button>
        )}
        <button
          className="map-tool-btn"
          onClick={handleToggleFullscreen}
          title={isFullscreen ? 'Exit Fullscreen' : 'View Fullscreen'}
          aria-label="Toggle Fullscreen"
        >
          {isFullscreen ? '✕ Exit' : 'Fullscreen'}
        </button>
      </div>

      {/* Active Selection Banner */}
      {selectedFeature && (
        <div className="map-selection-banner">
          <span>Selected {selectedFeature.type === 'village' ? 'Village' : 'Site'}: <b>{selectedFeature.name}</b></span>
          <button
            className="banner-close-btn"
            onClick={() => onSelectFeature && onSelectFeature(null)}
            title="Clear selection"
          >
            ✕
          </button>
        </div>
      )}

      {/* Floating Map Legend Overlay */}
      {hasData && (
        <div className="map-legend-overlay">
          <div className="legend-title">{mode === 'overview' ? 'Flood Overview Layers' : 'Impact Analysis Layers'}</div>
          <div className="legend-items">
            <div className="legend-item">
              <span className="legend-color-box flood-box"></span>
              <span className="legend-label">🌊 Flooded Area</span>
            </div>
            <div className="legend-item">
              <span className="legend-color-box building-box"></span>
              <span className="legend-label">🏘️ Affected Villages</span>
            </div>
            {mode === 'impact' && (
              <>
                <div className="legend-item">
                  <span className="legend-icon">👥</span>
                  <span className="legend-label">People Exposed</span>
                </div>
                <div className="legend-item">
                  <span className="legend-color-box building-box"></span>
                  <span className="legend-label">🏠 Affected Buildings</span>
                </div>
                <div className="legend-item">
                  <span className="legend-line road-line"></span>
                  <span className="legend-label">🛣️ Affected Roads</span>
                </div>
              </>
            )}
            <div className="legend-item">
              <span className="legend-icon">📍</span>
              <span className="legend-label">Flood Centroid</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
