import React, { useEffect, useRef, useState, useCallback } from 'react';
import { loadCesium } from '../services/cesiumLoader';
import {
  Map as MapIcon,
  Compass,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Layers,
  ChevronDown,
  ChevronUp,
  Loader2,
  AlertCircle
} from 'lucide-react';

/**
 * Computes bounding box and center dynamically from real GeoJSON and evacuation data.
 * Zero hardcoded coordinates so any AOI works seamlessly.
 */
function computeBoundingBox(floodGeoJSON, affectedVillagesGeoJSON, affectedRoadsGeoJSON, evacuationCandidates) {
  let minLon = Infinity;
  let minLat = Infinity;
  let maxLon = -Infinity;
  let maxLat = -Infinity;

  function traverseCoords(coords) {
    if (!Array.isArray(coords)) return;
    if (typeof coords[0] === 'number' && typeof coords[1] === 'number') {
      const lon = coords[0];
      const lat = coords[1];
      if (lon < minLon) minLon = lon;
      if (lon > maxLon) maxLon = lon;
      if (lat < minLat) minLat = lat;
      if (lat > maxLat) maxLat = lat;
    } else {
      coords.forEach(traverseCoords);
    }
  }

  function processGeoJSON(geojson) {
    if (!geojson?.features) return;
    geojson.features.forEach((f) => {
      if (f.geometry?.coordinates) {
        traverseCoords(f.geometry.coordinates);
      }
    });
  }

  processGeoJSON(floodGeoJSON);
  processGeoJSON(affectedVillagesGeoJSON);
  processGeoJSON(affectedRoadsGeoJSON);

  if (Array.isArray(evacuationCandidates)) {
    evacuationCandidates.forEach((c) => {
      if (c.lon != null && c.lat != null) {
        if (c.lon < minLon) minLon = c.lon;
        if (c.lon > maxLon) maxLon = c.lon;
        if (c.lat < minLat) minLat = c.lat;
        if (c.lat > maxLat) maxLat = c.lat;
      }
    });
  }

  if (!isFinite(minLon) || !isFinite(minLat)) {
    return {
      centerLon: 76.4624,
      centerLat: 9.6791,
      minLon: 76.3,
      maxLon: 76.6,
      minLat: 9.5,
      maxLat: 9.8,
      spanLon: 0.3,
      spanLat: 0.3,
    };
  }

  return {
    minLon,
    minLat,
    maxLon,
    maxLat,
    centerLon: (minLon + maxLon) / 2,
    centerLat: (minLat + maxLat) / 2,
    spanLon: Math.max(maxLon - minLon, 0.05),
    spanLat: Math.max(maxLat - minLat, 0.05),
  };
}

export default function CesiumViewer({
  floodGeoJSON,
  floodMetrics,
  affectedVillagesGeoJSON,
  affectedRoadsGeoJSON,
  evacuationCandidates,
  selectedFeature,
  onSelectFeature,
  onSwitchTo2D,
}) {
  const containerRef = useRef(null);
  const viewerRef = useRef(null);
  const boundsRef = useRef(null);
  const floodEntitiesRef = useRef([]);
  const villageEntitiesRef = useRef([]);
  const roadEntitiesRef = useRef([]);
  const evacEntitiesRef = useRef([]);

  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [isTilted, setIsTilted] = useState(true);
  const [basemapType, setBasemapType] = useState('google'); // 'google' | 'esri'
  const [showLayerPanel, setShowLayerPanel] = useState(false);
  const [layerVisibility, setLayerVisibility] = useState({
    flood: true,
    villages: true,
    roads: true,
    evac: true,
  });

  // Hover tooltip state for clean Google Earth style hover inspection
  const [hoveredSite, setHoveredSite] = useState(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });

  // Compute dynamic bounding box once from real SatQuery data
  const bounds = computeBoundingBox(
    floodGeoJSON,
    affectedVillagesGeoJSON,
    affectedRoadsGeoJSON,
    evacuationCandidates
  );
  boundsRef.current = bounds;

  // Fly smoothly to target extent in 3D perspective
  const flyToExtent = useCallback((tilted = true, duration = 1.8) => {
    const viewer = viewerRef.current;
    const b = boundsRef.current;
    if (!viewer || !b || viewer.isDestroyed()) return;

    const Cesium = window.Cesium;
    if (!Cesium) return;

    const maxSpan = Math.max(b.spanLon, b.spanLat, 0.08);
    const altitude = maxSpan * 111000 * 2.1;
    const latOffset = tilted ? maxSpan * 0.42 : 0;

    viewer.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(
        b.centerLon,
        b.centerLat - latOffset,
        Math.max(altitude, 16000)
      ),
      orientation: {
        heading: Cesium.Math.toRadians(0), // Looking North
        pitch: Cesium.Math.toRadians(tilted ? -42 : -90), // -42° oblique 3D tilt vs -90° nadir
        roll: 0.0,
      },
      duration: duration,
    });
  }, []);

  // Update Layer Visibility dynamically
  const toggleLayer = (layerName) => {
    setLayerVisibility((prev) => {
      const next = { ...prev, [layerName]: !prev[layerName] };
      const show = next[layerName];

      if (layerName === 'flood') floodEntitiesRef.current.forEach((e) => (e.show = show));
      if (layerName === 'villages') villageEntitiesRef.current.forEach((e) => (e.show = show));
      if (layerName === 'roads') roadEntitiesRef.current.forEach((e) => (e.show = show));
      if (layerName === 'evac') evacEntitiesRef.current.forEach((e) => (e.show = show));

      return next;
    });
  };

  // Switch Satellite Basemap Provider
  const setSatelliteBasemap = (type) => {
    setBasemapType(type);
    const viewer = viewerRef.current;
    const Cesium = window.Cesium;
    if (!viewer || !Cesium || viewer.isDestroyed()) return;

    viewer.imageryLayers.removeAll();

    let provider;
    if (type === 'google') {
      provider = new Cesium.UrlTemplateImageryProvider({
        url: 'https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
        subdomains: ['mt0', 'mt1', 'mt2', 'mt3'],
        maximumLevel: 20,
        credit: 'Google Satellite',
      });
    } else {
      provider = new Cesium.UrlTemplateImageryProvider({
        url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        maximumLevel: 19,
        credit: 'Esri World Imagery',
      });
    }

    viewer.imageryLayers.addImageryProvider(provider);
  };

  // Initialize Cesium viewer & populate layers
  useEffect(() => {
    let isCancelled = false;

    loadCesium()
      .then((Cesium) => {
        if (isCancelled || !containerRef.current) return;

        // 1. High-resolution Google Maps Satellite basemap as default
        const satelliteProvider = new Cesium.UrlTemplateImageryProvider({
          url: 'https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
          subdomains: ['mt0', 'mt1', 'mt2', 'mt3'],
          maximumLevel: 20,
          credit: 'Google Satellite',
        });

        // 2. Initialize Viewer with baseLayer: false to prevent Cesium Ion 401 errors
        const viewer = new Cesium.Viewer(containerRef.current, {
          baseLayer: false,
          terrainProvider: new Cesium.EllipsoidTerrainProvider(),
          animation: false,
          baseLayerPicker: false,
          fullscreenButton: false,
          geocoder: false,
          homeButton: false,
          infoBox: false, // Custom clean tooltip used instead of default iframe
          selectionIndicator: false,
          sceneModePicker: false,
          timeline: false,
          navigationHelpButton: false,
          creditContainer: document.createElement('div'), // Clean UI without credit clutter
        });

        // Mount the real satellite imagery layer directly
        viewer.imageryLayers.removeAll();
        viewer.imageryLayers.addImageryProvider(satelliteProvider);

        // Configure realistic Google Earth atmospheric lighting and globe rendering
        viewer.scene.globe.baseColor = Cesium.Color.fromCssColorString('#0f172a');
        viewer.scene.globe.enableLighting = false; // Bright daylight visibility on all satellite tiles
        viewer.scene.skyAtmosphere = new Cesium.SkyAtmosphere(); // Blue atmospheric glow along Earth horizon
        viewer.scene.globe.showGroundAtmosphere = true;
        viewer.scene.fog.enabled = true;
        viewer.scene.fog.density = 0.0002;

        viewerRef.current = viewer;

        // Clear tracking arrays
        floodEntitiesRef.current = [];
        villageEntitiesRef.current = [];
        roadEntitiesRef.current = [];
        evacEntitiesRef.current = [];

        // ---------------------------------------------------------------------
        // 3. REAL FLOOD POLYGON (Translucent blue fill + bright cyan outline)
        // ---------------------------------------------------------------------
        if (floodGeoJSON?.features) {
          floodGeoJSON.features.forEach((feature) => {
            const geom = feature.geometry;
            if (!geom) return;

            const handlePolygonRings = (rings) => {
              if (!rings || !rings.length) return;
              const exteriorRing = rings[0];
              const flatCoords = [];
              exteriorRing.forEach(([lon, lat]) => {
                flatCoords.push(lon, lat);
              });

              // Translucent water body fill draped on satellite imagery
              const polyEntity = viewer.entities.add({
                name: 'Flood Inundation Area',
                polygon: {
                  hierarchy: Cesium.Cartesian3.fromDegreesArray(flatCoords),
                  material: Cesium.Color.fromCssColorString('#0284c7').withAlpha(0.48),
                  heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
                },
              });
              floodEntitiesRef.current.push(polyEntity);

              // Vivid cyan perimeter outline matching reference image
              const outlineEntity = viewer.entities.add({
                name: 'Flood Perimeter',
                polyline: {
                  positions: Cesium.Cartesian3.fromDegreesArray(flatCoords),
                  width: 3.0,
                  material: Cesium.Color.fromCssColorString('#00e5ff'),
                  clampToGround: true,
                },
              });
              floodEntitiesRef.current.push(outlineEntity);
            };

            if (geom.type === 'Polygon') {
              handlePolygonRings(geom.coordinates);
            } else if (geom.type === 'MultiPolygon') {
              geom.coordinates.forEach(handlePolygonRings);
            }
          });
        }

        // ---------------------------------------------------------------------
        // 4. REAL VILLAGE BOUNDARIES (Thin yellow/orange boundaries, visually subtle)
        // ---------------------------------------------------------------------
        if (affectedVillagesGeoJSON?.features) {
          affectedVillagesGeoJSON.features.forEach((feature) => {
            const geom = feature.geometry;
            if (!geom) return;

            const handleVillageRings = (rings) => {
              if (!rings || !rings.length) return;
              const exteriorRing = rings[0];
              const flatCoords = [];
              exteriorRing.forEach(([lon, lat]) => {
                flatCoords.push(lon, lat);
              });

              const boundaryEntity = viewer.entities.add({
                name: `Village Boundary: ${feature.properties?.name || 'Local Panchayat'}`,
                polyline: {
                  positions: Cesium.Cartesian3.fromDegreesArray(flatCoords),
                  width: 1.8,
                  material: new Cesium.PolylineDashMaterialProperty({
                    color: Cesium.Color.fromCssColorString('#f59e0b').withAlpha(0.75),
                    dashLength: 12,
                  }),
                  clampToGround: true,
                },
              });
              villageEntitiesRef.current.push(boundaryEntity);
            };

            if (geom.type === 'Polygon') {
              handleVillageRings(geom.coordinates);
            } else if (geom.type === 'MultiPolygon') {
              geom.coordinates.forEach(handleVillageRings);
            }
          });
        }

        // ---------------------------------------------------------------------
        // 5. REAL ROADS (Actual road network, visible but subtle, never overwhelming)
        // ---------------------------------------------------------------------
        if (affectedRoadsGeoJSON?.features) {
          affectedRoadsGeoJSON.features.forEach((feature) => {
            const geom = feature.geometry;
            if (!geom) return;

            const handleLine = (coords) => {
              if (!coords || coords.length < 2) return;
              const flatCoords = [];
              coords.forEach(([lon, lat]) => {
                flatCoords.push(lon, lat);
              });

              const roadEntity = viewer.entities.add({
                name: `Road: ${feature.properties?.name || 'Inundated Corridor'}`,
                polyline: {
                  positions: Cesium.Cartesian3.fromDegreesArray(flatCoords),
                  width: 2.0, // Thin, subtle line
                  material: new Cesium.PolylineDashMaterialProperty({
                    color: Cesium.Color.fromCssColorString('#ef4444').withAlpha(0.85),
                    dashLength: 10,
                  }),
                  clampToGround: true,
                },
              });
              roadEntitiesRef.current.push(roadEntity);
            };

            if (geom.type === 'LineString') {
              handleLine(geom.coordinates);
            } else if (geom.type === 'MultiLineString') {
              geom.coordinates.forEach(handleLine);
            }
          });
        }

        // ---------------------------------------------------------------------
        // 6. REAL EVACUATION SITES (Clean professional pins, names on hover/click only)
        // ---------------------------------------------------------------------
        if (Array.isArray(evacuationCandidates)) {
          // Professional Google Earth style teardrop locator pin with green cross
          const pinSvg = 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="28" height="34" viewBox="0 0 28 34"><path d="M14 0C6.3 0 0 6.3 0 14c0 9.8 12.2 19 13.3 19.8.4.3 1 .3 1.4 0C15.8 33 28 23.8 28 14 28 6.3 21.7 0 14 0z" fill="%230284c7" stroke="%23ffffff" stroke-width="1.5"/><circle cx="14" cy="13" r="7.5" fill="%23ffffff"/><circle cx="14" cy="13" r="5" fill="%2310b981"/><path d="M11.5 13l1.8 1.8 3.2-3.2" stroke="%23ffffff" stroke-width="1.6" fill="none" stroke-linecap="round"/></svg>';

          evacuationCandidates.forEach((c) => {
            if (c.lat == null || c.lon == null) return;

            const isSelected = selectedFeature?.name === c.name;

            const evacEntity = viewer.entities.add({
              name: c.name,
              position: Cesium.Cartesian3.fromDegrees(c.lon, c.lat, 10),
              billboard: {
                image: pinSvg,
                width: isSelected ? 34 : 26,
                height: isSelected ? 42 : 32,
                verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
                heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
                disableDepthTestDistance: Number.POSITIVE_INFINITY,
              },
              // NO permanent label on map to prevent overlapping text!
              // Store metadata directly on entity for hover/click tooltip
              userData: {
                name: c.name,
                type: c.type,
                distance: c.distance_to_flood_km != null ? `${c.distance_to_flood_km.toFixed(2)} km` : 'Safe Zone',
                elevation: c.elevation_m != null ? `${c.elevation_m.toFixed(1)} m` : 'N/A',
              },
            });

            evacEntitiesRef.current.push(evacEntity);
          });
        }

        // ---------------------------------------------------------------------
        // 7. HOVER & CLICK INTERACTION HANDLER FOR EVACUATION PINS
        // ---------------------------------------------------------------------
        const handler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas);

        handler.setInputAction((movement) => {
          const picked = viewer.scene.pick(movement.endPosition);
          if (picked && picked.id && picked.id.userData) {
            setHoveredSite(picked.id.userData);
            setTooltipPos({ x: movement.endPosition.x + 14, y: movement.endPosition.y - 12 });
            containerRef.current.style.cursor = 'pointer';
          } else {
            setHoveredSite(null);
            containerRef.current.style.cursor = 'default';
          }
        }, Cesium.ScreenSpaceEventType.MOUSE_MOVE);

        handler.setInputAction((click) => {
          const picked = viewer.scene.pick(click.position);
          if (picked && picked.id && picked.id.userData) {
            const data = picked.id.userData;
            setHoveredSite(data);
            setTooltipPos({ x: click.position.x + 14, y: click.position.y - 12 });
            if (onSelectFeature) {
              onSelectFeature({ type: 'evac', name: data.name, data });
            }
          }
        }, Cesium.ScreenSpaceEventType.LEFT_CLICK);

        // ---------------------------------------------------------------------
        // 8. GOOGLE EARTH FLY-IN CAMERA TRANSITION
        // Start from regional perspective, smoothly fly down into tilted flood area
        // ---------------------------------------------------------------------
        setLoading(false);

        const b = boundsRef.current;
        const maxSpan = Math.max(b.spanLon, b.spanLat, 0.08);

        // Position camera initially at high altitude regional view
        viewer.camera.setView({
          destination: Cesium.Cartesian3.fromDegrees(b.centerLon, b.centerLat - (maxSpan * 0.9), 95000),
          orientation: {
            heading: Cesium.Math.toRadians(0),
            pitch: Cesium.Math.toRadians(-62),
            roll: 0.0,
          },
        });

        // Smoothly fly into the 35-50° tilted flood perspective
        setTimeout(() => {
          if (!viewer.isDestroyed()) {
            flyToExtent(true, 2.2);
          }
        }, 300);
      })
      .catch((err) => {
        if (!isCancelled) {
          console.error('Failed to initialize Cesium 3D viewer:', err);
          setLoadError(err.message || 'Failed to initialize 3D imagery engine.');
          setLoading(false);
        }
      });

    return () => {
      isCancelled = true;
      if (viewerRef.current && !viewerRef.current.isDestroyed()) {
        try {
          viewerRef.current.destroy();
        } catch (_) {}
        viewerRef.current = null;
      }
    };
  }, [
    floodGeoJSON,
    floodMetrics,
    affectedVillagesGeoJSON,
    affectedRoadsGeoJSON,
    evacuationCandidates,
    flyToExtent,
    onSelectFeature,
  ]);

  // Controls: Zoom In
  const handleZoomIn = () => {
    const viewer = viewerRef.current;
    if (!viewer || viewer.isDestroyed()) return;
    const height = viewer.camera.positionCartographic?.height || 20000;
    viewer.camera.zoomIn(height * 0.35);
  };

  // Controls: Zoom Out
  const handleZoomOut = () => {
    const viewer = viewerRef.current;
    if (!viewer || viewer.isDestroyed()) return;
    const height = viewer.camera.positionCartographic?.height || 20000;
    viewer.camera.zoomOut(height * 0.35);
  };

  // Controls: Tilt 3D / Top-Down
  const handleToggleTilt = () => {
    const nextTilt = !isTilted;
    setIsTilted(nextTilt);
    flyToExtent(nextTilt, 1.2);
  };

  // Controls: Reset View
  const handleReset = () => {
    setIsTilted(true);
    flyToExtent(true, 1.5);
  };

  return (
    <div className="cesium-viewer-wrapper">
      {/* Loading state indicator */}
      {loading && (
        <div className="cesium-loading-overlay">
          <Loader2 size={32} className="spin-icon" color="#38bdf8" />
          <div style={{ fontWeight: 600, color: '#f1f5f9', marginTop: 10, fontSize: '0.95rem' }}>
            Loading High-Resolution Satellite 3D View...
          </div>
          <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
            Rendering satellite imagery & real flood extent
          </span>
        </div>
      )}

      {/* Error state fallback */}
      {loadError && (
        <div className="cesium-error-overlay">
          <AlertCircle size={32} color="#ef4444" />
          <div style={{ fontWeight: 600, color: '#f1f5f9', marginTop: 8 }}>
            Unable to Launch Satellite 3D Engine
          </div>
          <p style={{ fontSize: '0.82rem', color: '#94a3b8', maxWidth: 360, textAlign: 'center' }}>
            {loadError}
          </p>
          <button className="btn-primary" style={{ width: 'auto', marginTop: 8 }} onClick={onSwitchTo2D}>
            Return to 2D Map
          </button>
        </div>
      )}

      {/* Main Cesium WebGL DOM Canvas */}
      <div ref={containerRef} className="cesium-map-canvas" />

      {/* Dynamic Hover Tooltip for Evacuation Sites (Only visible when hovered/clicked) */}
      {hoveredSite && (
        <div
          className="cesium-site-tooltip"
          style={{
            position: 'absolute',
            left: tooltipPos.x,
            top: tooltipPos.y,
            pointerEvents: 'none',
            zIndex: 60,
          }}
        >
          <div className="tooltip-header">
            <span className="tooltip-badge">SAFE CANDIDATE</span>
            <span className="tooltip-title">{hoveredSite.name}</span>
          </div>
          <div className="tooltip-body">
            <div className="tooltip-row">
              <span className="tooltip-lbl">Type:</span>
              <span className="tooltip-val">{hoveredSite.type}</span>
            </div>
            <div className="tooltip-row">
              <span className="tooltip-lbl">Distance to Flood:</span>
              <span className="tooltip-val highlight-green">{hoveredSite.distance}</span>
            </div>
            <div className="tooltip-row">
              <span className="tooltip-lbl">DEM Elevation:</span>
              <span className="tooltip-val">{hoveredSite.elevation}</span>
            </div>
          </div>
        </div>
      )}

      {/* Clean Minimalist Control Bar (Google Earth Style) */}
      <div className="cesium-action-toolbar">
        {/* Return to 2D Leaflet Map */}
        <button
          className="cesium-control-btn btn-mode-return"
          onClick={onSwitchTo2D}
          title="Return to 2D Map"
          aria-label="2D Map"
        >
          <MapIcon size={14} />
          <span>2D Map</span>
        </button>

        {/* 3D Active Indicator */}
        <div className="cesium-mode-pill">
          <span>3D View</span>
        </div>

        {/* Tilt Toggle */}
        <button
          className="cesium-control-btn"
          onClick={handleToggleTilt}
          title={isTilted ? 'Switch to Top-Down Nadir View' : 'Switch to 3D Tilted Perspective'}
          aria-label="Toggle Tilt"
        >
          <Compass size={14} />
          <span>{isTilted ? 'Top-Down' : 'Tilt 3D'}</span>
        </button>

        {/* Zoom In */}
        <button
          className="cesium-control-btn icon-only"
          onClick={handleZoomIn}
          title="Zoom In"
          aria-label="Zoom In"
        >
          <ZoomIn size={14} />
        </button>

        {/* Zoom Out */}
        <button
          className="cesium-control-btn icon-only"
          onClick={handleZoomOut}
          title="Zoom Out"
          aria-label="Zoom Out"
        >
          <ZoomOut size={14} />
        </button>

        {/* Reset Camera Extent */}
        <button
          className="cesium-control-btn icon-only"
          onClick={handleReset}
          title="Reset Camera to Extent"
          aria-label="Reset Camera"
        >
          <RotateCcw size={14} />
        </button>

        {/* Layer Controls Dropdown */}
        <div className="cesium-layer-dropdown-wrapper">
          <button
            className={`cesium-control-btn ${showLayerPanel ? 'active' : ''}`}
            onClick={() => setShowLayerPanel(!showLayerPanel)}
            title="Toggle Map Layers & Basemap"
            aria-label="Layer Controls"
          >
            <Layers size={14} />
            <span>Layers</span>
            {showLayerPanel ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          </button>

          {showLayerPanel && (
            <div className="cesium-layer-panel card">
              <div className="panel-section-title">Satellite Basemap</div>
              <div className="basemap-toggle-row">
                <button
                  className={`btn-basemap-choice ${basemapType === 'google' ? 'active' : ''}`}
                  onClick={() => setSatelliteBasemap('google')}
                >
                  Google Satellite
                </button>
                <button
                  className={`btn-basemap-choice ${basemapType === 'esri' ? 'active' : ''}`}
                  onClick={() => setSatelliteBasemap('esri')}
                >
                  Esri Satellite
                </button>
              </div>

              <div className="panel-section-title" style={{ marginTop: 10 }}>GIS Layers</div>
              <label className="layer-checkbox-row">
                <input
                  type="checkbox"
                  checked={layerVisibility.flood}
                  onChange={() => toggleLayer('flood')}
                />
                <span className="swatch-box flood-swatch" />
                <span>Flood Extent</span>
              </label>

              <label className="layer-checkbox-row">
                <input
                  type="checkbox"
                  checked={layerVisibility.villages}
                  onChange={() => toggleLayer('villages')}
                />
                <span className="swatch-box village-swatch" />
                <span>Village Boundaries</span>
              </label>

              <label className="layer-checkbox-row">
                <input
                  type="checkbox"
                  checked={layerVisibility.roads}
                  onChange={() => toggleLayer('roads')}
                />
                <span className="swatch-box road-swatch" />
                <span>Inundated Roads</span>
              </label>

              <label className="layer-checkbox-row">
                <input
                  type="checkbox"
                  checked={layerVisibility.evac}
                  onChange={() => toggleLayer('evac')}
                />
                <span className="swatch-box evac-swatch" />
                <span>Evacuation Sites</span>
              </label>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
