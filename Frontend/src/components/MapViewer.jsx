import React, { useEffect, useRef, useState, useCallback } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Focus, Maximize2, Minimize2, X, Satellite, Box, Layers } from 'lucide-react';
import Map3DViewer from './Map3DViewer';

export default function MapViewer({
  floodGeoJSON,
  floodMetrics,
  evacuationCandidates,
  affectedVillages,
  affectedVillagesGeoJSON,
  affectedRoadsGeoJSON,
  affectedBuildingsGeoJSON,
  priorityScores,
  selectedFeature,
  onSelectFeature,
  skipAnimation = false,
  focusVillage = null,
  onClearFocusVillage,
  onBackToImpact,
}) {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const floodLayerRef = useRef(null);
  const villagesLayerRef = useRef(null);
  const roadsLayerRef = useRef(null);
  const evacuLayerRef = useRef(null);
  const evacRouteLayerRef = useRef(null);
  const layerControlRef = useRef(null);
  const baseLayersRef = useRef({});
  const overlayLayersRef = useRef({});
  const lastAnalysisBoundsRef = useRef(null);

  // Active layer visibility state for custom legend or controls
  const [activeLayers, setActiveLayers] = useState({
    flood: true,
    villages: true,
    roads: true,
    evac: true,
  });

  // Track fullscreen state safely
  const [isFullscreen, setIsFullscreen] = useState(false);

  // View mode state: '3d' is the DEFAULT when Map Explorer opens
  const [viewMode, setViewMode] = useState('3d');

  // Automatically ensure 3D mode is active when focusing on a village from Impact Analysis
  useEffect(() => {
    if (focusVillage) {
      setViewMode('3d');
    }
  }, [focusVillage]);

  // Switch to 2D Leaflet map safely preserving map instance & state
  const handleSwitchTo2D = useCallback(() => {
    setViewMode('2d');
    setTimeout(() => {
      try {
        mapInstanceRef.current?.invalidateSize();
      } catch (_) {}
    }, 60);
  }, []);

  const handleSwitchTo3D = useCallback(() => {
    setViewMode('3d');
    setTimeout(() => {
      try {
        window.__map3d?.resize();
      } catch (_) {}
    }, 60);
  }, []);

  // Initialize Leaflet map once - begins with the wide India-level view from the sample-data workflow
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    const map = L.map(mapContainerRef.current, {
      center: [20.5937, 78.9629], // Center over India as broad neutral baseline
      zoom: 5,
      zoomControl: false,
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

    // Track layer add/remove to keep legend synced
    map.on('overlayadd', (e) => {
      if (e.name.includes('Flood')) setActiveLayers((prev) => ({ ...prev, flood: true }));
      if (e.name.includes('Villages')) setActiveLayers((prev) => ({ ...prev, villages: true }));
      if (e.name.includes('Roads')) setActiveLayers((prev) => ({ ...prev, roads: true }));
      if (e.name.includes('Candidate') || e.name.includes('Evacuation')) setActiveLayers((prev) => ({ ...prev, evac: true }));
    });

    map.on('overlayremove', (e) => {
      if (e.name.includes('Flood')) setActiveLayers((prev) => ({ ...prev, flood: false }));
      if (e.name.includes('Villages')) setActiveLayers((prev) => ({ ...prev, villages: false }));
      if (e.name.includes('Roads')) setActiveLayers((prev) => ({ ...prev, roads: false }));
      if (e.name.includes('Candidate') || e.name.includes('Evacuation')) setActiveLayers((prev) => ({ ...prev, evac: false }));
    });

    map.on('click', (e) => {
      if (e.originalEvent && !e.originalEvent._handled) {
        onSelectFeature?.(null);
      }
    });

    mapInstanceRef.current = map;
    window.__map2d = map;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  // Reset / Fit to Analysis Extent handler
  const handleResetBounds = useCallback(() => {
    const map = mapInstanceRef.current;
    if (map && lastAnalysisBoundsRef.current && lastAnalysisBoundsRef.current.isValid()) {
      map.fitBounds(lastAnalysisBoundsRef.current, { padding: [45, 45], maxZoom: 14, animate: true });
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

  // Update layers and fit/fly bounds smoothly whenever pipeline results update
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    window.__floodGeoJSON = floodGeoJSON;
    window.__affectedVillagesGeoJSON = affectedVillagesGeoJSON;
    let combinedBounds = null;

    // -------------------------------------------------------------------------
    // 1. FLOOD EXTENT LAYER (Real completed polygon, no duplicate animation)
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
          className: 'flood-polygon-path',
          color: '#00e5ff', // Vivid cyan outline
          weight: 2.2,
          opacity: 0.95,
          fillColor: '#0284c7', // Bright translucent blue flood fill
          fillOpacity: 0.62,
          lineJoin: 'round',
          lineCap: 'round',
        },
        onEachFeature: (feature, lyr) => {
          lyr.on({
            mouseover: (e) => {
              const layer = e.target;
              layer.setStyle({
                fillColor: '#38bdf8',
                fillOpacity: 0.75,
                weight: 3.2,
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
      layerControlRef.current?.addOverlay(floodLayer, 'Flood Extent');

      try {
        const b = floodLayer.getBounds();
        if (b && b.isValid()) {
          combinedBounds = combinedBounds ? combinedBounds.extend(b) : b;
        }
      } catch (_) {}
    }

    // -------------------------------------------------------------------------
    // 2. INTERACTIVE VILLAGES LAYER (Real Kerala village boundaries)
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
            color: isSelected ? '#ef4444' : '#f59e0b', // Red highlight if selected, else amber/orange
            weight: isSelected ? 3.5 : 2.0,
            opacity: 0.95,
            fill: false,
            fillOpacity: 0,
            dashArray: isSelected ? undefined : '6, 5',
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

          lyr.on({
            mouseover: (e) => {
              const layer = e.target;
              layer.setStyle({
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

          lyr.bindPopup(
            '<div class="gis-popup village-popup">' +
              '<div class="gis-popup-header">' +
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
                  'Heuristic decision-support score from spatial overlay. Field verification advised.' +
                '</div>' +
              '</div>' +
            '</div>',
            { maxWidth: 280 }
          );
        },
      });

      villagesLayer.addTo(map);
      villagesLayerRef.current = villagesLayer;
      layerControlRef.current?.addOverlay(villagesLayer, 'Affected Villages');

      try {
        const b = villagesLayer.getBounds();
        if (b && b.isValid()) {
          combinedBounds = combinedBounds ? combinedBounds.extend(b) : b;
        }
      } catch (_) {}
    }

    // -------------------------------------------------------------------------
    // 3. AFFECTED ROADS LAYER (Real Kerala road corridors)
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
        style: (feature) => {
          const isPrimary = feature?.properties?.highway === 'primary';
          return {
            color: '#ef4444', // High contrast red
            weight: isPrimary ? 4.5 : 2.5,
            opacity: 0.95,
            dashArray: '6, 6',
          };
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
                `<div class="gis-popup-title">${roadName}</div>` +
              '</div>' +
              '<div class="gis-popup-body">' +
                '<div class="gis-popup-row">' +
                  '<span class="gis-popup-label">Corridor Classification:</span>' +
                  `<span class="gis-popup-val font-mono">${highwayType}</span>` +
                '</div>' +
                '<div class="gis-popup-status-badge road-status-badge">' +
                  'Inundated / Submerged Segment — Impassable' +
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
      layerControlRef.current?.addOverlay(roadsLayer, 'Inundated Roads');

      try {
        const b = roadsLayer.getBounds();
        if (b && b.isValid()) {
          combinedBounds = combinedBounds ? combinedBounds.extend(b) : b;
        }
      } catch (_) {}
    }

    // -------------------------------------------------------------------------
    // 4. EVACUATION CANDIDATE SITES LAYER (Real candidate sites with pins)
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

        const isSelected =
          (selectedFeature?.type === 'evac' || selectedFeature?.type === 'evacuation') &&
          selectedFeature?.name?.toLowerCase().trim() === c.name?.toLowerCase().trim();

        if (isSelected) {
          setTimeout(() => {
            try {
              marker.openPopup();
            } catch (_) {}
          }, 1300);
        }

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
              `<div class="gis-popup-title">${c.name}</div>` +
              `<span class="gis-popup-badge badge-green">${c.type}</span>` +
            '</div>' +
            '<div class="gis-popup-body">' +
              '<div class="gis-popup-row">' +
                '<span class="gis-popup-label">Distance to Flood:</span>' +
                `<span class="gis-popup-val highlight-green">${distStr}</span>` +
              '</div>' +
              (c.route_distance_km != null
                ? '<div class="gis-popup-row">' +
                    '<span class="gis-popup-label">Road Route Distance:</span>' +
                    `<span class="gis-popup-val highlight-amber" style="font-weight: 700; color: #00e5ff;">${c.route_distance_km.toFixed(2)} km</span>` +
                  '</div>' +
                  '<div class="gis-popup-row">' +
                    '<span class="gis-popup-label">Route Departure:</span>' +
                    `<span class="gis-popup-val" style="font-size: 11px;">${c.origin_name || 'Flood Boundary'}</span>` +
                  '</div>'
                : '') +
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
                '<b>CANDIDATE SITE ONLY:</b> Requires on-ground physical inspection. NOT a verified shelter.' +
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
      layerControlRef.current?.addOverlay(group, 'Evacuation Sites');
    }

    // -------------------------------------------------------------------------
    // 4b. EVACUATION ROAD ROUTE TO SELECTED CENTER (2D LEAFLET)
    // -------------------------------------------------------------------------
    if (evacRouteLayerRef.current) {
      try {
        map.removeLayer(evacRouteLayerRef.current);
      } catch (_) {}
      evacRouteLayerRef.current = null;
    }

    const isEvacSelected = (selectedFeature?.type === 'evac' || selectedFeature?.type === 'evacuation');
    const selName = selectedFeature?.name?.toLowerCase().trim();
    const cand = isEvacSelected
      ? (evacuationCandidates?.find((c) => c.name?.toLowerCase().trim() === selName) || selectedFeature?.data)
      : null;

    if (cand?.route_geojson) {
      const routeGroup = L.featureGroup();
      // High-contrast casing halo
      const casing = L.geoJSON(cand.route_geojson, {
        style: {
          color: '#0f172a',
          weight: 7.5,
          opacity: 0.85,
          lineCap: 'round',
          lineJoin: 'round',
        },
      });
      // Vivid electric cyan route
      const line = L.geoJSON(cand.route_geojson, {
        style: {
          color: '#00e5ff',
          weight: 4.5,
          opacity: 0.98,
          lineCap: 'round',
          lineJoin: 'round',
        },
      });
      routeGroup.addLayer(casing);
      routeGroup.addLayer(line);
      routeGroup.addTo(map);
      evacRouteLayerRef.current = routeGroup;
    }
    window.__activeEvacRoute2D = cand?.route_geojson || null;

    // -------------------------------------------------------------------------
    // 5. FIT / FLY BOUNDS SMOOTHLY TO DETECTED EXTENT
    // -------------------------------------------------------------------------
    if (combinedBounds && combinedBounds.isValid()) {
      lastAnalysisBoundsRef.current = combinedBounds;

      setTimeout(() => {
        try {
          map.invalidateSize();
          if (skipAnimation) {
            map.fitBounds(combinedBounds, { padding: [50, 50], maxZoom: 14 });
          } else {
            map.flyToBounds(combinedBounds, {
              padding: [50, 50],
              maxZoom: 14,
              duration: 1.2,
            });
          }
        } catch (_) {
          try {
            map.fitBounds(combinedBounds, { padding: [40, 40], maxZoom: 14 });
          } catch (e) {}
        }
      }, 50);
    } else {
      map.invalidateSize();
    }
  }, [
    floodGeoJSON,
    floodMetrics,
    affectedVillagesGeoJSON,
    affectedRoadsGeoJSON,
    evacuationCandidates,
    selectedFeature,
    onSelectFeature,
    skipAnimation,
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
          <Satellite size={40} color="#38bdf8" className="map-no-data-icon" />
          <div style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '0.95rem' }}>
            Interactive GIS Flood Analysis Map
          </div>
          <span>Upload pre & post satellite GeoTIFFs and click Run Flood Analysis to inspect spatial results.</span>
        </div>
      )}

      {/* Main Leaflet Map Container - ALWAYS maintained in DOM to preserve state */}
      <div
        ref={mapContainerRef}
        className="leaflet-map-container"
        style={{ display: viewMode === '2d' ? 'block' : 'none' }}
      />

      {/* 3D Map Explorer Container */}
      <div
        style={{
          display: viewMode === '3d' ? 'block' : 'none',
          position: 'absolute',
          inset: 0,
          width: '100%',
          height: '100%',
        }}
      >
        {hasData && (
          <Map3DViewer
            floodGeoJSON={floodGeoJSON}
            floodMetrics={floodMetrics}
            affectedVillages={affectedVillages}
            affectedVillagesGeoJSON={affectedVillagesGeoJSON}
            affectedRoadsGeoJSON={affectedRoadsGeoJSON}
            affectedBuildingsGeoJSON={affectedBuildingsGeoJSON}
            evacuationCandidates={evacuationCandidates}
            focusVillage={focusVillage}
            onClearFocusVillage={onClearFocusVillage}
            onBackToImpact={onBackToImpact}
            priorityScores={priorityScores}
            selectedFeature={selectedFeature}
            onSelectFeature={onSelectFeature}
          />
        )}
      </div>

      {/* Floating Map Toolbar Controls (Persistent across 2D & 3D) */}
      <div className="map-action-toolbar" style={{ zIndex: 30 }}>
        {hasData && (
          <div className="map-view-mode-toggle">
            <button
              className={`view-mode-pill ${viewMode === '3d' ? 'active' : ''}`}
              onClick={handleSwitchTo3D}
              title="3D Map Explorer"
            >
              <Box size={13} />
              <span>3D</span>
            </button>
            <button
              className={`view-mode-pill ${viewMode === '2d' ? 'active' : ''}`}
              onClick={handleSwitchTo2D}
              title="2D Leaflet Map"
            >
              <Layers size={13} />
              <span>2D</span>
            </button>
          </div>
        )}
        {viewMode === '2d' && hasData && (
          <button
            className="map-tool-btn"
            onClick={handleResetBounds}
            title="Fit to analysis extent"
            aria-label="Fit to analysis extent"
          >
            <Focus size={15} />
            <span className="btn-text">Reset Extent</span>
          </button>
        )}
        <button
          className="map-tool-btn"
          onClick={handleToggleFullscreen}
          title={isFullscreen ? 'Exit Fullscreen' : 'View Fullscreen'}
          aria-label="Toggle Fullscreen"
        >
          {isFullscreen ? <Minimize2 size={15} /> : <Maximize2 size={15} />}
          <span className="btn-text">{isFullscreen ? 'Exit' : 'Fullscreen'}</span>
        </button>
      </div>

      {/* Active Selection Indicator */}
      {selectedFeature && (
        <div className="map-selection-banner">
          <span>Selected {selectedFeature.type === 'village' ? 'Village' : 'Site'}: <b>{selectedFeature.name}</b></span>
          <button
            className="banner-close-btn"
            onClick={() => onSelectFeature && onSelectFeature(null)}
            title="Clear selection"
          >
            <X size={14} />
          </button>
        </div>
      )}
    </div>
  );
}
