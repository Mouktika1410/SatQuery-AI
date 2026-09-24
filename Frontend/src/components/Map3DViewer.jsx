import React, { useEffect, useRef, useState, useCallback } from 'react';
import * as maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import maplibreWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url';

// Configure MapLibre Web Worker for Vite
maplibregl.setWorkerUrl(maplibreWorkerUrl);
import {
  Compass,
  RotateCcw,
  Layers,
  ArrowLeft,
  MapPin,
  ExternalLink,
  ShieldCheck,
  Building,
  Activity,
  Maximize2,
  Minimize2,
} from 'lucide-react';

/**
 * Computes bounding box and center dynamically from any GeoJSON feature or collection.
 * Zero hardcoded coordinates so any AOI works seamlessly.
 */
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

/**
 * Fast ray-casting point-in-polygon helper for GeoJSON rings.
 */
function pointInPolygon(point, ring) {
  const [x, y] = point;
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const xi = ring[i][0], yi = ring[i][1];
    const xj = ring[j][0], yj = ring[j][1];
    const intersect = ((yi > y) !== (yj > y)) && (x < (xj - xi) * (y - yi) / (yj - yi) + xi);
    if (intersect) inside = !inside;
  }
  return inside;
}

function pointDistanceSq(p1, p2) {
  const dx = p1[0] - p2[0];
  const dy = p1[1] - p2[1];
  return dx * dx + dy * dy;
}

/**
 * Checks if a given lngLat coordinate intersects or is nearest to an affected village boundary.
 * Works seamlessly with Polygon, MultiPolygon, LineString, and MultiLineString geometries.
 */
function findIntersectingVillage(lngLat, villagesGeoJSON) {
  if (!villagesGeoJSON?.features || villagesGeoJSON.features.length === 0) return null;
  const [lng, lat] = [lngLat.lng, lngLat.lat];

  // 1. Polygon containment check (if Polygon or MultiPolygon)
  for (const f of villagesGeoJSON.features) {
    if (!f.geometry) continue;
    const geom = f.geometry;
    if (geom.type === 'Polygon' && Array.isArray(geom.coordinates?.[0])) {
      if (pointInPolygon([lng, lat], geom.coordinates[0])) return f;
    } else if (geom.type === 'MultiPolygon' && Array.isArray(geom.coordinates)) {
      for (const poly of geom.coordinates) {
        if (Array.isArray(poly?.[0]) && pointInPolygon([lng, lat], poly[0])) return f;
      }
    }
  }

  // 2. LineString / boundary proximity check
  let closestFeature = null;
  let minDistanceSq = Infinity;
  const MAX_THRESH_SQ = 0.08 * 0.08; // ~8-9km proximity threshold

  for (const f of villagesGeoJSON.features) {
    if (!f.geometry) continue;
    const geom = f.geometry;

    function checkCoords(coords) {
      if (!Array.isArray(coords)) return;
      if (typeof coords[0] === 'number' && typeof coords[1] === 'number') {
        const d2 = pointDistanceSq([lng, lat], coords);
        if (d2 < minDistanceSq) {
          minDistanceSq = d2;
          closestFeature = f;
        }
      } else {
        coords.forEach(checkCoords);
      }
    }

    checkCoords(geom.coordinates);
  }

  if (minDistanceSq <= MAX_THRESH_SQ) {
    return closestFeature;
  }

  return null;
}

/**
 * Checks if a given lngLat coordinate intersects any flood polygon in the GeoJSON.
 */
function findIntersectingFlood(lngLat, floodGeoJSON) {
  if (!floodGeoJSON) return false;
  const [lng, lat] = [lngLat.lng, lngLat.lat];
  const features = floodGeoJSON.type === 'FeatureCollection' ? floodGeoJSON.features : [floodGeoJSON];
  for (const f of features) {
    const geom = f.geometry || f;
    if (geom.type === 'Polygon' && Array.isArray(geom.coordinates?.[0])) {
      if (pointInPolygon([lng, lat], geom.coordinates[0])) return true;
    } else if (geom.type === 'MultiPolygon' && Array.isArray(geom.coordinates)) {
      for (const poly of geom.coordinates) {
        if (Array.isArray(poly?.[0]) && pointInPolygon([lng, lat], poly[0])) return true;
      }
    }
  }
  return false;
}

function isMapStyleReady(m) {
  return Boolean(m && (m.style?.stylesheet || m.isStyleLoaded()));
}

export default function Map3DViewer({
  floodGeoJSON,
  floodMetrics,
  affectedVillages,
  affectedVillagesGeoJSON,
  affectedRoadsGeoJSON,
  affectedBuildingsGeoJSON,
  evacuationCandidates,
  focusVillage,
  onClearFocusVillage,
  onBackToImpact,
  priorityScores,
  selectedFeature,
  onSelectFeature,
}) {
  const mapContainerRef = useRef(null);
  const mapRef = useRef(null);
  const markersRef = useRef([]);
  const hasFlownInitialRef = useRef(false);
  const activePopupRef = useRef(null);

  const [basemapType, setBasemapType] = useState('google'); // 'google' | 'esri'
  const [isTilted, setIsTilted] = useState(true);
  const [showLayerPanel, setShowLayerPanel] = useState(false);
  const [layerVisibility, setLayerVisibility] = useState({
    mapContext: true,
    flood: true,
    villages: true,
    roads: true,
    buildings: true,
    evac: true,
  });

  // Build fast lookups for priority scores and village data matching 2D MapViewer
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

  // Keep latest refs accessible to map click handlers
  const latestPropsRef = useRef({});
  latestPropsRef.current = {
    floodGeoJSON,
    floodMetrics,
    affectedVillages,
    affectedVillagesGeoJSON,
    affectedRoadsGeoJSON,
    evacuationCandidates,
    selectedFeature,
    onSelectFeature,
    layerVisibility,
  };

  useEffect(() => {
    window.__floodGeoJSON = floodGeoJSON;
    window.__affectedVillagesGeoJSON = affectedVillagesGeoJSON;
    window.__evacuationCandidates = evacuationCandidates;
  }, [floodGeoJSON, affectedVillagesGeoJSON, evacuationCandidates]);

  // Calculate dynamic regional bounds from flood polygon
  const regionalBounds = getGeoJSONBBox(floodGeoJSON);

  // Calculate target bounds: village intersection if focused, otherwise regional flood
  const targetBounds = focusVillage?.geometry
    ? getGeoJSONBBox(focusVillage.geometry) || regionalBounds
    : regionalBounds;

  // Show Flood Extent Popup
  const showFloodPopup = useCallback((lngLat) => {
    const map = mapRef.current;
    if (!map) return null;

    const {
      floodGeoJSON: curFloodGeo,
      floodMetrics: curMetrics,
      affectedVillagesGeoJSON: curVillagesGeo,
    } = latestPropsRef.current;

    if (activePopupRef.current) activePopupRef.current.remove();

    const areaVal = curMetrics?.areaKm2 != null ? Number(curMetrics.areaKm2).toFixed(2) : null;
    const areaStr = areaVal ? `${areaVal} km²` : 'Calculated Extent';
    const pctStr = curMetrics?.floodPercentage != null ? `${Number(curMetrics.floodPercentage).toFixed(2)}%` : null;
    const countStr = curMetrics?.polygonCount != null ? curMetrics.polygonCount : (curFloodGeo?.features ? curFloodGeo.features.length : 1);

    // Check if click intersects or is near an affected village location
    const hitVillage = findIntersectingVillage(lngLat, curVillagesGeo);
    let villageInfoHtml = '';

    if (hitVillage) {
      const rawName = hitVillage.properties?.name || hitVillage.properties?.NAME || 'Affected Village';
      const cleanKey = rawName.toLowerCase().trim();
      const vData = villageLookup.current[cleanKey];
      const pData = priorityLookup.current[cleanKey];

      const floodedKm2 = vData?.area_flooded_km2 != null ? `${vData.area_flooded_km2.toFixed(2)} km²` : null;
      const popEst = vData?.population_affected != null ? vData.population_affected.toLocaleString() : null;
      const rank = pData?.rank != null ? `#${pData.rank}` : null;
      const score = pData?.priority_score != null ? pData.priority_score.toFixed(3) : null;

      villageInfoHtml = `
        <div style="margin-top: 6px; padding-top: 6px; border-top: 1px dashed #cbd5e1;">
          <div class="gis-popup-row">
            <span class="gis-popup-label">Intersecting Village:</span>
            <span class="gis-popup-val" style="color: #b45309; font-weight: 700;">${rawName}</span>
          </div>
          ${floodedKm2 ? `
          <div class="gis-popup-row">
            <span class="gis-popup-label">Village Flooded:</span>
            <span class="gis-popup-val highlight-amber">${floodedKm2}</span>
          </div>` : ''}
          ${score ? `
          <div class="gis-popup-row">
            <span class="gis-popup-label">Priority Score:</span>
            <span class="gis-popup-val font-mono">${score} ${rank ? `(${rank})` : ''}</span>
          </div>` : ''}
          ${popEst ? `
          <div class="gis-popup-row">
            <span class="gis-popup-label">Estimated Pop Affected:</span>
            <span class="gis-popup-val">${popEst}</span>
          </div>` : ''}
        </div>
      `;
    }

    const popupContent = `
      <div class="gis-popup flood-popup">
        <div class="gis-popup-header">
          <div class="gis-popup-title">Detected Flood Extent</div>
          <span class="gis-popup-badge badge-flood">Water Inundation</span>
        </div>
        <div class="gis-popup-body">
          <div class="gis-popup-row">
            <span class="gis-popup-label">Flooded Area:</span>
            <span class="gis-popup-val highlight-blue">${areaStr}</span>
          </div>
          ${pctStr ? `
          <div class="gis-popup-row">
            <span class="gis-popup-label">Image Coverage:</span>
            <span class="gis-popup-val">${pctStr}</span>
          </div>` : ''}
          <div class="gis-popup-row">
            <span class="gis-popup-label">Polygons Count:</span>
            <span class="gis-popup-val">${countStr}</span>
          </div>
          ${villageInfoHtml}
          <div class="gis-popup-footnote">Generated via satellite water-detection and vector simplification</div>
        </div>
      </div>
    `;

    const popup = new maplibregl.Popup({ offset: 12, closeButton: true, maxWidth: '280px' })
      .setLngLat(lngLat)
      .setHTML(popupContent)
      .addTo(map);

    activePopupRef.current = popup;
    return popup;
  }, []);

  // Show Village Popup & Update Selection
  const showVillagePopup = useCallback((villageFeature, lngLat) => {
    const map = mapRef.current;
    if (!map || !villageFeature) return null;

    const { onSelectFeature: curSelectHandler } = latestPropsRef.current;
    if (activePopupRef.current) activePopupRef.current.remove();

    const rawName = villageFeature.properties?.name || villageFeature.properties?.NAME || 'Affected Village';
    const cleanKey = rawName.toLowerCase().trim();
    const vData = villageLookup.current[cleanKey];
    const pData = priorityLookup.current[cleanKey];

    if (curSelectHandler) {
      curSelectHandler({ type: 'village', name: rawName, data: { ...vData, ...pData } });
    }

    const floodedKm2 = vData?.area_flooded_km2 != null ? `${vData.area_flooded_km2.toFixed(2)} km²` : null;
    const popEst = vData?.population_affected != null ? vData.population_affected.toLocaleString() : null;
    const rank = pData?.rank != null ? `#${pData.rank}` : null;
    const score = pData?.priority_score != null ? pData.priority_score.toFixed(3) : null;

    const popupContent = `
      <div class="gis-popup village-popup">
        <div class="gis-popup-header">
          <div class="gis-popup-title">${rawName}</div>
          ${rank ? `<span class="gis-popup-badge badge-amber">Rank ${rank}</span>` : ''}
        </div>
        <div class="gis-popup-body">
          ${floodedKm2 ? `
          <div class="gis-popup-row">
            <span class="gis-popup-label">Flooded Inundation:</span>
            <span class="gis-popup-val highlight-amber">${floodedKm2}</span>
          </div>` : ''}
          ${score ? `
          <div class="gis-popup-row">
            <span class="gis-popup-label">Urgency Score:</span>
            <span class="gis-popup-val font-mono">${score}</span>
          </div>` : ''}
          ${popEst ? `
          <div class="gis-popup-row">
            <span class="gis-popup-label">Estimated Pop Affected:</span>
            <span class="gis-popup-val">${popEst}</span>
          </div>` : ''}
          <div class="gis-popup-footnote alert-box">
            Heuristic decision-support score from spatial overlay. Field verification advised.
          </div>
        </div>
      </div>
    `;

    const popup = new maplibregl.Popup({ offset: 12, closeButton: true, maxWidth: '280px' })
      .setLngLat(lngLat)
      .setHTML(popupContent)
      .addTo(map);

    activePopupRef.current = popup;
    return popup;
  }, []);

  // Show Inundated Road Popup
  const showRoadPopup = useCallback((roadFeature, lngLat) => {
    const map = mapRef.current;
    if (!map || !roadFeature) return null;

    if (activePopupRef.current) activePopupRef.current.remove();

    const roadName = roadFeature.properties?.name || 'Inundated Road Corridor';
    const highwayType = roadFeature.properties?.highway || roadFeature.properties?.type || 'Road Network';

    const popupContent = `
      <div class="gis-popup road-popup">
        <div class="gis-popup-header">
          <div class="gis-popup-title">${roadName}</div>
          <span class="gis-popup-badge badge-road">Submerged</span>
        </div>
        <div class="gis-popup-body">
          <div class="gis-popup-row">
            <span class="gis-popup-label">Corridor Classification:</span>
            <span class="gis-popup-val font-mono">${highwayType}</span>
          </div>
          <div class="gis-popup-footnote alert-box-warning" style="margin-top: 6px;">
            Inundated / Submerged Segment — Impassable
          </div>
          <div class="gis-popup-footnote">Road vector geometry intersected with detected flood boundary</div>
        </div>
      </div>
    `;

    const popup = new maplibregl.Popup({ offset: 12, closeButton: true, maxWidth: '280px' })
      .setLngLat(lngLat)
      .setHTML(popupContent)
      .addTo(map);

    activePopupRef.current = popup;
    return popup;
  }, []);

  // Render Evacuation Markers with active selection state
  const renderEvacuationMarkers = useCallback((map, candidates, visible = true, currentSelected = null) => {
    markersRef.current.forEach((m) => m.remove());
    markersRef.current = [];

    if (!Array.isArray(candidates) || candidates.length === 0 || !map) return;

    candidates.forEach((c) => {
      if (c.lon == null || c.lat == null) return;

      const isSelected =
        (currentSelected?.type === 'evac' || currentSelected?.type === 'evacuation') &&
        currentSelected?.name?.toLowerCase().trim() === c.name?.toLowerCase().trim();

      const el = document.createElement('div');
      el.className = `cesium-evac-pin-dom ${isSelected ? 'selected-pin' : ''}`;
      el.style.display = visible ? 'block' : 'none';
      el.style.cursor = 'pointer';

      // Visual styling for selected (amber gold) vs standard (deep emerald green)
      if (isSelected) {
        el.innerHTML = `
          <div style="
            width: 32px;
            height: 32px;
            background: #f59e0b;
            border: 2.5px solid #fef08a;
            border-radius: 50% 50% 50% 0;
            transform: rotate(-45deg) scale(1.15);
            box-shadow: 0 0 16px #f59e0b, 0 6px 16px rgba(0, 0, 0, 0.6);
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.25s ease;
          ">
            <span style="
              transform: rotate(45deg);
              color: #0f172a;
              font-weight: 900;
              font-size: 13px;
              line-height: 1;
            ">✓</span>
          </div>
        `;
      } else {
        el.innerHTML = `
          <div style="
            width: 28px;
            height: 28px;
            background: #022c22;
            border: 2px solid #10b981;
            border-radius: 50% 50% 50% 0;
            transform: rotate(-45deg);
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.45);
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.25s ease;
          ">
            <span style="
              transform: rotate(45deg);
              color: #34d399;
              font-weight: 800;
              font-size: 11px;
              line-height: 1;
            ">✓</span>
          </div>
        `;
      }

      const distStr = c.distance_to_flood_km != null ? `${c.distance_to_flood_km.toFixed(2)} km` : 'Outside Flood Zone';
      const elevStr = c.elevation_m != null ? `${c.elevation_m.toFixed(1)} m (DEM)` : null;
      const coordsStr = `${c.lat.toFixed(4)}°N, ${c.lon.toFixed(4)}°E`;

      const popupHtml = `
        <div class="gis-popup evac-popup">
          <div class="gis-popup-header">
            <div class="gis-popup-title">${c.name}</div>
            <span class="gis-popup-badge badge-green">${c.type}</span>
          </div>
          <div class="gis-popup-body">
            <div class="gis-popup-row">
              <span class="gis-popup-label">Distance to Flood:</span>
              <span class="gis-popup-val highlight-green">${distStr}</span>
            </div>
            ${c.route_distance_km != null ? `
            <div class="gis-popup-row">
              <span class="gis-popup-label">Road Route Distance:</span>
              <span class="gis-popup-val highlight-amber" style="font-weight: 700; color: #00e5ff;">${c.route_distance_km.toFixed(2)} km</span>
            </div>
            <div class="gis-popup-row">
              <span class="gis-popup-label">Route Departure:</span>
              <span class="gis-popup-val" style="font-size: 11px;">${c.origin_name || 'Flood Boundary'}</span>
            </div>` : ''}
            ${elevStr ? `
            <div class="gis-popup-row">
              <span class="gis-popup-label">Elevation:</span>
              <span class="gis-popup-val">${elevStr}</span>
            </div>` : ''}
            <div class="gis-popup-row">
              <span class="gis-popup-label">Coordinates:</span>
              <span class="gis-popup-val font-mono" style="font-size:11px">${coordsStr}</span>
            </div>
            <div class="gis-popup-footnote alert-box-warning">
              <b>CANDIDATE SITE ONLY:</b> Requires on-ground physical inspection. NOT a verified shelter.
            </div>
          </div>
        </div>
      `;

      const popup = new maplibregl.Popup({ offset: 20, closeButton: true, maxWidth: '280px' })
        .setHTML(popupHtml);

      el.addEventListener('click', (ev) => {
        ev.stopPropagation();
        if (ev.originalEvent) ev.originalEvent._handled = true;

        if (activePopupRef.current) {
          activePopupRef.current.remove();
        }

        if (onSelectFeature) {
          onSelectFeature({ type: 'evac', name: c.name, data: c });
        }

        marker.togglePopup();
        activePopupRef.current = popup;
      });

      const marker = new maplibregl.Marker({ element: el })
        .setLngLat([c.lon, c.lat])
        .setPopup(popup)
        .addTo(map);

      if (isSelected) {
        setTimeout(() => {
          try {
            if (!marker.getPopup().isOpen()) {
              marker.togglePopup();
              activePopupRef.current = popup;
            }
          } catch (_) {}
        }, 150);
      }

      markersRef.current.push(marker);
    });
  }, [onSelectFeature]);

  // Initialize MapLibre map with satellite basemap + transparent street/map context overlay
  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    const tileUrl =
      basemapType === 'google'
        ? 'https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}'
        : 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}';

    // Google Hybrid Roads & Place Labels transparent PNG overlay
    const streetContextUrl = 'https://mt1.google.com/vt/lyrs=h&x={x}&y={y}&z={z}';

    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: {
        version: 8,
        sources: {
          'satellite-tiles': {
            type: 'raster',
            tiles: [tileUrl],
            tileSize: 256,
            maxzoom: 20,
            attribution: '© Google / Esri Satellite',
          },
          'map-context-tiles': {
            type: 'raster',
            tiles: [streetContextUrl],
            tileSize: 256,
            maxzoom: 20,
            attribution: '© Google Maps',
          },
        },
        layers: [
          {
            id: 'satellite-basemap',
            type: 'raster',
            source: 'satellite-tiles',
            minzoom: 0,
            maxzoom: 20,
          },
          {
            id: 'map-context-layer',
            type: 'raster',
            source: 'map-context-tiles',
            minzoom: 0,
            maxzoom: 20,
            layout: {
              visibility: layerVisibility.mapContext !== false ? 'visible' : 'none',
            },
          },
        ],
      },
      // Start at wide India regional baseline view
      center: [78.9629, 20.5937],
      zoom: 4.5,
      pitch: 0,
      bearing: 0,
      antialias: true,
      maxPitch: 85,
    });

    mapRef.current = map;
    window.__map3d = map;
    window.__map3dShowFloodPopup = showFloodPopup;
    window.__map3dShowVillagePopup = showVillagePopup;

    // Add navigation controls (visualize pitch)
    map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), 'top-right');

    const onStyleReady = () => {
      if (!isMapStyleReady(map)) return;

      // Initialize Village Focus Layers if not present
      if (!map.getSource('village-focus-data')) {
        map.addSource('village-focus-data', {
          type: 'geojson',
          data: { type: 'FeatureCollection', features: [] },
        });

        map.addLayer({
          id: 'village-focus-fill-layer',
          type: 'fill',
          source: 'village-focus-data',
          paint: {
            'fill-color': '#38bdf8',
            'fill-opacity': 0.65,
          },
        });

        map.addLayer({
          id: 'village-focus-outline-layer',
          type: 'line',
          source: 'village-focus-data',
          paint: {
            'line-color': '#00e5ff',
            'line-width': 3.2,
            'line-opacity': 1.0,
          },
        });
      }
    };

    if (isMapStyleReady(map)) {
      onStyleReady();
    } else {
      map.once('style.load', onStyleReady);
      map.once('load', onStyleReady);
    }

    // Generic Canvas Click Handler for Map Background and Fallback Raycasting
    const handleMapClick = (e) => {
      if (e.originalEvent?._handled) return;

      const {
        floodGeoJSON: curFloodGeo,
        affectedVillagesGeoJSON: curVillagesGeo,
        layerVisibility: curVis,
        onSelectFeature: curSelectHandler,
      } = latestPropsRef.current;

      // 1. Check Inundated Roads
      if (curVis.roads && map.getLayer('roads-line-layer')) {
        const roadFeatures = map.queryRenderedFeatures(e.point, { layers: ['roads-line-layer'] });
        if (roadFeatures.length > 0) {
          showRoadPopup(roadFeatures[0], e.lngLat);
          return;
        }
      }

      // 2. Check Village Boundaries (Query rendered features or pointInPolygon)
      if (curVis.villages && (map.getLayer('villages-outline-layer') || map.getLayer('villages-fill-layer'))) {
        const villageLayers = ['villages-outline-layer', 'villages-fill-layer'].filter((id) => map.getLayer(id));
        const villageFeatures = map.queryRenderedFeatures(e.point, { layers: villageLayers });
        const hitVillage = villageFeatures.length > 0 ? villageFeatures[0] : findIntersectingVillage(e.lngLat, curVillagesGeo);

        if (hitVillage) {
          showVillagePopup(hitVillage, e.lngLat);
          return;
        }
      }

      // 3. Check Flood Polygon (Query rendered features or pointInPolygon)
      if (curVis.flood && map.getLayer('flood-fill-layer')) {
        const floodFeats = map.queryRenderedFeatures(e.point, { layers: ['flood-fill-layer'] });
        const isFlood = floodFeats.length > 0 || findIntersectingFlood(e.lngLat, curFloodGeo);

        if (isFlood) {
          showFloodPopup(e.lngLat);
          return;
        }
      }

      // 4. Clicked Outside on Background -> Deselect and Close Popup Cleanly
      if (activePopupRef.current) {
        activePopupRef.current.remove();
        activePopupRef.current = null;
      }
      if (curSelectHandler) {
        curSelectHandler(null);
      }
    };

    // Hover cursor feedback over interactive layers
    const handleMouseMove = (e) => {
      const activeInteractiveLayers = [
        'flood-fill-layer',
        'villages-outline-layer',
        'villages-fill-layer',
        'roads-line-layer',
      ].filter((id) => map.getLayer(id));

      if (activeInteractiveLayers.length === 0) return;
      const feats = map.queryRenderedFeatures(e.point, { layers: activeInteractiveLayers });
      map.getCanvas().style.cursor = feats && feats.length > 0 ? 'pointer' : '';
    };

    map.on('click', handleMapClick);
    map.on('mousemove', handleMouseMove);

    // Auto-resize observer so toggling 2D/3D or window resizing updates WebGL viewport
    let resizeObserver = null;
    if (window.ResizeObserver && mapContainerRef.current) {
      resizeObserver = new ResizeObserver(() => {
        try {
          map.resize();
        } catch (_) {}
      });
      resizeObserver.observe(mapContainerRef.current);
    }

    return () => {
      if (resizeObserver) resizeObserver.disconnect();
      map.off('click', handleMapClick);
      map.off('mousemove', handleMouseMove);
      if (activePopupRef.current) activePopupRef.current.remove();
      markersRef.current.forEach((m) => m.remove());
      markersRef.current = [];
      map.remove();
      mapRef.current = null;
      window.__map3d = null;
      window.__map3dShowFloodPopup = null;
      window.__map3dShowVillagePopup = null;
    };
  }, [basemapType, showFloodPopup, showVillagePopup, showRoadPopup]);

  // Reactive synchronizer for REAL Flood Polygon
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const syncFloodLayer = () => {
      if (!isMapStyleReady(map)) return;

      const sourceId = 'flood-data';
      const fillLayerId = 'flood-fill-layer';
      const outlineLayerId = 'flood-outline-layer';

      const hasValid =
        floodGeoJSON &&
        (
          (floodGeoJSON.type === 'FeatureCollection' && Array.isArray(floodGeoJSON.features) && floodGeoJSON.features.length > 0) ||
          (floodGeoJSON.type === 'Feature' && floodGeoJSON.geometry) ||
          (floodGeoJSON.coordinates)
        );

      const normalizedData = hasValid
        ? (floodGeoJSON.type === 'FeatureCollection'
            ? floodGeoJSON
            : { type: 'FeatureCollection', features: [floodGeoJSON.type === 'Feature' ? floodGeoJSON : { type: 'Feature', properties: {}, geometry: floodGeoJSON }] })
        : { type: 'FeatureCollection', features: [] };

      const existingSource = map.getSource(sourceId);
      if (existingSource) {
        existingSource.setData(normalizedData);
      } else {
        map.addSource(sourceId, {
          type: 'geojson',
          data: normalizedData,
        });
      }

      if (!map.getLayer(fillLayerId)) {
        map.addLayer({
          id: fillLayerId,
          type: 'fill',
          source: sourceId,
          layout: {
            visibility: layerVisibility.flood && hasValid ? 'visible' : 'none',
          },
          paint: {
            'fill-color': '#0284c7', // Bright translucent blue flood fill coherent with 2D Leaflet
            'fill-opacity': 0.62,
          },
        });

        // Layer-specific click listener
        map.on('click', fillLayerId, (e) => {
          if (e.originalEvent) e.originalEvent._handled = true;
          showFloodPopup(e.lngLat);
        });
      }

      if (!map.getLayer(outlineLayerId)) {
        map.addLayer({
          id: outlineLayerId,
          type: 'line',
          source: sourceId,
          layout: {
            visibility: layerVisibility.flood && hasValid ? 'visible' : 'none',
          },
          paint: {
            'line-color': '#00e5ff', // Vivid cyan outline coherent with 2D Leaflet
            'line-width': 2.8,
            'line-opacity': 0.95,
          },
        });
      }

      if (map.getLayer(fillLayerId)) {
        map.setLayoutProperty(fillLayerId, 'visibility', layerVisibility.flood && hasValid ? 'visible' : 'none');
      }
      if (map.getLayer(outlineLayerId)) {
        map.setLayoutProperty(outlineLayerId, 'visibility', layerVisibility.flood && hasValid ? 'visible' : 'none');
      }
    };

    if (isMapStyleReady(map)) {
      syncFloodLayer();
    } else {
      map.once('style.load', syncFloodLayer);
      map.once('load', syncFloodLayer);
    }
  }, [floodGeoJSON, layerVisibility.flood, showFloodPopup]);

  // Reactive synchronizer for GIS layers (Villages, Roads, Buildings)
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const syncGISLayers = () => {
      if (!isMapStyleReady(map)) return;

      // 1. Village Boundaries
      const vValid = affectedVillagesGeoJSON && affectedVillagesGeoJSON.features?.length > 0;
      const vData = vValid ? affectedVillagesGeoJSON : { type: 'FeatureCollection', features: [] };
      const vSrc = map.getSource('villages-data');
      if (vSrc) {
        vSrc.setData(vData);
      } else {
        map.addSource('villages-data', { type: 'geojson', data: vData });
      }

      // Invisible/subtle fill for reliable clicking anywhere inside a village
      if (!map.getLayer('villages-fill-layer')) {
        map.addLayer({
          id: 'villages-fill-layer',
          type: 'fill',
          source: 'villages-data',
          paint: {
            'fill-color': '#f59e0b',
            'fill-opacity': 0.04,
          },
        });

        map.on('click', 'villages-fill-layer', (e) => {
          if (e.originalEvent) e.originalEvent._handled = true;
          showVillagePopup(e.features?.[0], e.lngLat);
        });
      }
      if (map.getLayer('villages-fill-layer')) {
        map.setLayoutProperty('villages-fill-layer', 'visibility', layerVisibility.villages && vValid ? 'visible' : 'none');
      }

      if (!map.getLayer('villages-outline-layer')) {
        map.addLayer({
          id: 'villages-outline-layer',
          type: 'line',
          source: 'villages-data',
          paint: {
            'line-color': '#f59e0b',
            'line-width': 2.2,
            'line-dasharray': [3, 2],
            'line-opacity': 0.9,
          },
        });

        map.on('click', 'villages-outline-layer', (e) => {
          if (e.originalEvent) e.originalEvent._handled = true;
          showVillagePopup(e.features?.[0], e.lngLat);
        });
      }
      if (map.getLayer('villages-outline-layer')) {
        map.setLayoutProperty('villages-outline-layer', 'visibility', layerVisibility.villages && vValid ? 'visible' : 'none');
      }

      // Village Selected Highlight Outline
      if (!map.getLayer('villages-selected-outline-layer')) {
        map.addLayer({
          id: 'villages-selected-outline-layer',
          type: 'line',
          source: 'villages-data',
          paint: {
            'line-color': '#ef4444',
            'line-width': 4.0,
            'line-opacity': 1.0,
          },
          filter: ['==', ['downcase', ['coalesce', ['get', 'name'], ['get', 'NAME'], '']], ''],
        });
      }
      if (map.getLayer('villages-selected-outline-layer')) {
        map.setLayoutProperty('villages-selected-outline-layer', 'visibility', layerVisibility.villages && vValid ? 'visible' : 'none');
      }

      // 2. Inundated Roads
      const rValid = affectedRoadsGeoJSON && affectedRoadsGeoJSON.features?.length > 0;
      const rData = rValid ? affectedRoadsGeoJSON : { type: 'FeatureCollection', features: [] };
      const rSrc = map.getSource('roads-data');
      if (rSrc) {
        rSrc.setData(rData);
      } else {
        map.addSource('roads-data', { type: 'geojson', data: rData });
      }
      if (!map.getLayer('roads-line-layer')) {
        map.addLayer({
          id: 'roads-line-layer',
          type: 'line',
          source: 'roads-data',
          paint: {
            'line-color': '#ef4444',
            'line-width': 2.6,
            'line-dasharray': [4, 2],
            'line-opacity': 0.95,
          },
        });

        map.on('click', 'roads-line-layer', (e) => {
          if (e.originalEvent) e.originalEvent._handled = true;
          showRoadPopup(e.features?.[0], e.lngLat);
        });
      }
      if (map.getLayer('roads-line-layer')) {
        map.setLayoutProperty('roads-line-layer', 'visibility', layerVisibility.roads && rValid ? 'visible' : 'none');
      }

      // 3. Building Footprints
      const bValid = affectedBuildingsGeoJSON && affectedBuildingsGeoJSON.features?.length > 0;
      const bData = bValid ? affectedBuildingsGeoJSON : { type: 'FeatureCollection', features: [] };
      const bSrc = map.getSource('buildings-data');
      if (bSrc) {
        bSrc.setData(bData);
      } else {
        map.addSource('buildings-data', { type: 'geojson', data: bData });
      }
      if (!map.getLayer('buildings-fill-layer')) {
        map.addLayer({
          id: 'buildings-fill-layer',
          type: 'fill',
          source: 'buildings-data',
          paint: {
            'fill-color': '#f8fafc',
            'fill-opacity': 0.78,
          },
        });
      }
      if (!map.getLayer('buildings-outline-layer')) {
        map.addLayer({
          id: 'buildings-outline-layer',
          type: 'line',
          source: 'buildings-data',
          paint: {
            'line-color': '#94a3b8',
            'line-width': 1.0,
            'line-opacity': 0.85,
          },
        });
      }
      if (map.getLayer('buildings-fill-layer')) {
        map.setLayoutProperty('buildings-fill-layer', 'visibility', layerVisibility.buildings && bValid ? 'visible' : 'none');
      }
      if (map.getLayer('buildings-outline-layer')) {
        map.setLayoutProperty('buildings-outline-layer', 'visibility', layerVisibility.buildings && bValid ? 'visible' : 'none');
      }
    };

    if (isMapStyleReady(map)) {
      syncGISLayers();
    } else {
      map.once('style.load', syncGISLayers);
      map.once('load', syncGISLayers);
    }
  }, [
    affectedVillagesGeoJSON,
    affectedRoadsGeoJSON,
    affectedBuildingsGeoJSON,
    layerVisibility.villages,
    layerVisibility.roads,
    layerVisibility.buildings,
    showVillagePopup,
    showRoadPopup,
  ]);

  // Reactive Selected Village Highlight Filter
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !isMapStyleReady(map) || !map.getLayer('villages-selected-outline-layer')) return;

    if (selectedFeature?.type === 'village' && selectedFeature?.name) {
      const selName = selectedFeature.name.toLowerCase().trim();
      map.setFilter('villages-selected-outline-layer', [
        '==',
        ['downcase', ['coalesce', ['get', 'name'], ['get', 'NAME'], '']],
        selName,
      ]);
    } else {
      map.setFilter('villages-selected-outline-layer', ['==', ['coalesce', ['get', 'name'], ''], '__none__']);
    }
  }, [selectedFeature]);

  // Reactive synchronizer for Evacuation Markers (passes selectedFeature)
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    renderEvacuationMarkers(map, evacuationCandidates, layerVisibility.evac, selectedFeature);
  }, [evacuationCandidates, layerVisibility.evac, selectedFeature, renderEvacuationMarkers]);

  // Reactive synchronizer for Evacuation Road Route leading to Selected Center
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const syncEvacRoute = () => {
      if (!isMapStyleReady(map)) return;

      const isEvacSelected = (selectedFeature?.type === 'evac' || selectedFeature?.type === 'evacuation');
      const selName = selectedFeature?.name?.toLowerCase().trim();
      const cand = isEvacSelected
        ? (evacuationCandidates?.find((c) => c.name?.toLowerCase().trim() === selName) || selectedFeature?.data)
        : null;

      const routeData = (cand?.route_geojson && layerVisibility.evac)
        ? cand.route_geojson
        : { type: 'FeatureCollection', features: [] };

      const routeSrc = map.getSource('evac-route-data');
      if (routeSrc) {
        routeSrc.setData(routeData);
      } else {
        map.addSource('evac-route-data', { type: 'geojson', data: routeData });
      }
      window.__activeEvacRoute3D = routeData;

      // Add high-contrast casing halo underneath route line
      if (!map.getLayer('evac-route-casing-layer')) {
        map.addLayer({
          id: 'evac-route-casing-layer',
          type: 'line',
          source: 'evac-route-data',
          layout: {
            'line-cap': 'round',
            'line-join': 'round',
          },
          paint: {
            'line-color': '#0f172a',
            'line-width': 7.5,
            'line-opacity': 0.85,
          },
        });
      }

      // Add prominent glowing electric cyan evacuation route line
      if (!map.getLayer('evac-route-line-layer')) {
        map.addLayer({
          id: 'evac-route-line-layer',
          type: 'line',
          source: 'evac-route-data',
          layout: {
            'line-cap': 'round',
            'line-join': 'round',
          },
          paint: {
            'line-color': '#00e5ff',
            'line-width': 4.5,
            'line-opacity': 0.98,
          },
        });
      }

      const isVisible = layerVisibility.evac && Boolean(cand?.route_geojson);
      if (map.getLayer('evac-route-casing-layer')) {
        map.setLayoutProperty('evac-route-casing-layer', 'visibility', isVisible ? 'visible' : 'none');
      }
      if (map.getLayer('evac-route-line-layer')) {
        map.setLayoutProperty('evac-route-line-layer', 'visibility', isVisible ? 'visible' : 'none');
      }
    };

    if (isMapStyleReady(map)) {
      syncEvacRoute();
    } else {
      map.once('style.load', syncEvacRoute);
      map.once('load', syncEvacRoute);
    }
  }, [selectedFeature, evacuationCandidates, layerVisibility.evac]);

  // Cinematic initial camera fly-in
  useEffect(() => {
    const map = mapRef.current;
    if (!map || hasFlownInitialRef.current || !targetBounds) return;

    const triggerFlight = () => {
      if (!isMapStyleReady(map) || hasFlownInitialRef.current || !targetBounds) return;
      hasFlownInitialRef.current = true;
      const maxSpan = Math.max(targetBounds.spanLon, targetBounds.spanLat);
      const targetZoom = Math.min(15.8, Math.max(12.5, Math.round(14.2 - Math.log2(maxSpan / 0.08))));

      setTimeout(() => {
        try {
          map.flyTo({
            center: [targetBounds.centerLon, targetBounds.centerLat],
            zoom: targetZoom,
            pitch: 52,
            bearing: -15,
            duration: 3200,
            essential: true,
          });
        } catch (_) {}
      }, 100);
    };

    if (isMapStyleReady(map)) {
      triggerFlight();
    } else {
      map.once('style.load', triggerFlight);
      map.once('load', triggerFlight);
    }
  }, [targetBounds]);

  // Update focus village highlight & smooth camera swoop
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !isMapStyleReady(map)) return;

    if (focusVillage?.geometry) {
      // Set intersection geometry in focus source
      const src = map.getSource('village-focus-data');
      if (src) {
        src.setData({
          type: 'Feature',
          geometry: focusVillage.geometry,
          properties: { name: focusVillage.name },
        });
      }

      // Smooth camera swoop into selected village ∩ detected flood polygon
      const vBounds = getGeoJSONBBox(focusVillage.geometry);
      if (vBounds) {
        const vSpan = Math.max(vBounds.spanLon, vBounds.spanLat);
        const vZoom = Math.min(16.5, Math.max(14.5, Math.round(15.2 - Math.log2(vSpan / 0.03))));

        map.flyTo({
          center: [vBounds.centerLon, vBounds.centerLat],
          zoom: vZoom,
          pitch: 54,
          bearing: -20,
          duration: 2400,
          essential: true,
        });
      }
    } else {
      const src = map.getSource('village-focus-data');
      if (src) {
        src.setData({ type: 'FeatureCollection', features: [] });
      }
    }
  }, [focusVillage]);

  // Update Layer Visibility
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !isMapStyleReady(map)) return;

    const setVis = (layerId, visible) => {
      if (map.getLayer(layerId)) {
        map.setLayoutProperty(layerId, 'visibility', visible ? 'visible' : 'none');
      }
    };

    setVis('map-context-layer', layerVisibility.mapContext !== false);
    setVis('flood-fill-layer', layerVisibility.flood);
    setVis('flood-outline-layer', layerVisibility.flood);
    setVis('villages-fill-layer', layerVisibility.villages);
    setVis('villages-outline-layer', layerVisibility.villages);
    setVis('villages-selected-outline-layer', layerVisibility.villages);
    setVis('roads-line-layer', layerVisibility.roads);
    setVis('buildings-fill-layer', layerVisibility.buildings);
    setVis('buildings-outline-layer', layerVisibility.buildings);

    markersRef.current.forEach((m) => {
      const el = m.getElement();
      if (el) el.style.display = layerVisibility.evac ? 'block' : 'none';
    });
  }, [layerVisibility]);

  // Tilt Toggle
  const handleToggleTilt = useCallback(() => {
    const map = mapRef.current;
    if (!map) return;
    const newTilt = !isTilted;
    setIsTilted(newTilt);
    map.easeTo({
      pitch: newTilt ? 52 : 0,
      duration: 800,
    });
  }, [isTilted]);

  // Reset Extent Handler
  const handleResetExtent = useCallback(() => {
    const map = mapRef.current;
    if (!map || !regionalBounds) return;

    const maxSpan = Math.max(regionalBounds.spanLon, regionalBounds.spanLat);
    const targetZoom = Math.min(15.8, Math.max(12.5, Math.round(14.2 - Math.log2(maxSpan / 0.08))));

    map.flyTo({
      center: [regionalBounds.centerLon, regionalBounds.centerLat],
      zoom: targetZoom,
      pitch: 52,
      bearing: -15,
      duration: 2000,
      essential: true,
    });

    if (onClearFocusVillage) onClearFocusVillage();
  }, [regionalBounds, onClearFocusVillage]);

  // Derive village priority stats if available
  const villageScore = focusVillage && priorityScores?.find(
    (p) => p.village_name?.toLowerCase().trim() === focusVillage.name?.toLowerCase().trim()
  );

  return (
    <div className="map-3d-wrapper" style={{ position: 'relative', width: '100%', height: '100%' }}>
      {/* MapLibre WebGL Canvas Container */}
      <div ref={mapContainerRef} style={{ width: '100%', height: '100%' }} />

      {/* Floating Focus Village Banner (when village is selected from Impact Analysis) */}
      {focusVillage && (
        <div
          className="map-3d-focus-banner"
          style={{
            position: 'absolute',
            top: 16,
            left: 16,
            zIndex: 10,
            background: 'rgba(15, 23, 42, 0.92)',
            backdropFilter: 'blur(10px)',
            border: '1.5px solid #0284c7',
            borderRadius: '10px',
            padding: '12px 16px',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5)',
            color: '#f8fafc',
            maxWidth: 380,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 6, fontWeight: 700, fontSize: '0.92rem', color: '#38bdf8' }}>
              <MapPin size={16} color="#38bdf8" />
              <span>{focusVillage.name} Local 3D View</span>
            </span>
            {villageScore && (
              <span style={{ fontSize: '0.72rem', background: '#0369a1', color: '#e0f2fe', padding: '2px 8px', borderRadius: '12px', fontWeight: 600 }}>
                Score: {villageScore.priority_score?.toFixed(3)}
              </span>
            )}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px', fontSize: '0.78rem', color: '#cbd5e1', marginBottom: 10 }}>
            <div>Flooded Area: <strong style={{ color: '#38bdf8' }}>{focusVillage.area_flooded_km2?.toFixed(2)} km²</strong></div>
            <div>Camera: <strong style={{ color: '#34d399' }}>Tilted 3D Oblique</strong></div>
          </div>

          <div style={{ display: 'flex', gap: 8 }}>
            <button
              className="btn-ghost-sm"
              onClick={handleResetExtent}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 5,
                fontSize: '0.75rem',
                background: '#1e293b',
                color: '#94a3b8',
                border: '1px solid #334155',
                borderRadius: '6px',
                padding: '4px 10px',
                cursor: 'pointer',
              }}
            >
              <RotateCcw size={13} />
              <span>Full Flood Extent</span>
            </button>
            {onBackToImpact && (
              <button
                className="btn-primary-sm"
                onClick={onBackToImpact}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 5,
                  fontSize: '0.75rem',
                  background: '#0284c7',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '6px',
                  padding: '4px 12px',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                <ArrowLeft size={13} />
                <span>Back to Impact Analysis</span>
              </button>
            )}
          </div>
        </div>
      )}

      {/* Floating 3D Action Controls */}
      <div
        className="map-3d-floating-controls"
        style={{
          position: 'absolute',
          bottom: 24,
          left: '50%',
          transform: 'translateX(-50%)',
          zIndex: 10,
          background: 'rgba(15, 23, 42, 0.9)',
          backdropFilter: 'blur(8px)',
          border: '1px solid rgba(255, 255, 255, 0.12)',
          borderRadius: '30px',
          padding: '6px 12px',
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          boxShadow: '0 8px 30px rgba(0, 0, 0, 0.45)',
        }}
      >
        <button
          className="map-3d-btn"
          onClick={handleToggleTilt}
          title={isTilted ? 'Switch to Top-Down 2D' : 'Switch to Tilted 3D'}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 5,
            background: isTilted ? 'rgba(56, 189, 248, 0.2)' : 'transparent',
            border: isTilted ? '1px solid #38bdf8' : '1px solid transparent',
            color: isTilted ? '#38bdf8' : '#e2e8f0',
            borderRadius: '20px',
            padding: '5px 12px',
            fontSize: '0.8rem',
            cursor: 'pointer',
            fontWeight: 600,
          }}
        >
          <Compass size={14} />
          <span>{isTilted ? '3D Oblique' : 'Top Down'}</span>
        </button>

        <button
          className="map-3d-btn"
          onClick={handleResetExtent}
          title="Reset Extent"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 5,
            background: 'transparent',
            border: '1px solid transparent',
            color: '#e2e8f0',
            borderRadius: '20px',
            padding: '5px 12px',
            fontSize: '0.8rem',
            cursor: 'pointer',
          }}
        >
          <RotateCcw size={14} />
          <span>Reset</span>
        </button>

        <div style={{ width: 1, height: 16, background: 'rgba(255, 255, 255, 0.2)' }} />

        <button
          className="map-3d-btn"
          onClick={() => setShowLayerPanel(!showLayerPanel)}
          title="Toggle Layers"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 5,
            background: showLayerPanel ? 'rgba(56, 189, 248, 0.2)' : 'transparent',
            border: showLayerPanel ? '1px solid #38bdf8' : '1px solid transparent',
            color: showLayerPanel ? '#38bdf8' : '#e2e8f0',
            borderRadius: '20px',
            padding: '5px 12px',
            fontSize: '0.8rem',
            cursor: 'pointer',
          }}
        >
          <Layers size={14} />
          <span>Layers</span>
        </button>
      </div>

      {/* Layers Panel Drawer */}
      {showLayerPanel && (
        <div
          style={{
            position: 'absolute',
            bottom: 74,
            left: '50%',
            transform: 'translateX(-50%)',
            zIndex: 10,
            background: 'rgba(15, 23, 42, 0.95)',
            backdropFilter: 'blur(10px)',
            border: '1px solid #334155',
            borderRadius: '12px',
            padding: '12px 16px',
            minWidth: 250,
            boxShadow: '0 12px 32px rgba(0, 0, 0, 0.6)',
            fontSize: '0.8rem',
            color: '#f8fafc',
          }}
        >
          <div style={{ fontWeight: 700, marginBottom: 8, color: '#38bdf8', textTransform: 'uppercase', fontSize: '0.72rem', letterSpacing: '0.05em' }}>
            GIS Layer Visibility
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={layerVisibility.mapContext !== false}
                onChange={(e) => setLayerVisibility({ ...layerVisibility, mapContext: e.target.checked })}
              />
              <span style={{ color: '#94a3b8' }}>● Streets & Place Labels</span>
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={layerVisibility.flood}
                onChange={(e) => setLayerVisibility({ ...layerVisibility, flood: e.target.checked })}
              />
              <span style={{ color: '#38bdf8' }}>● Flood Polygon</span>
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={layerVisibility.villages}
                onChange={(e) => setLayerVisibility({ ...layerVisibility, villages: e.target.checked })}
              />
              <span style={{ color: '#f59e0b' }}>● Village Boundaries</span>
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={layerVisibility.roads}
                onChange={(e) => setLayerVisibility({ ...layerVisibility, roads: e.target.checked })}
              />
              <span style={{ color: '#ef4444' }}>● Road Corridors</span>
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={layerVisibility.buildings}
                onChange={(e) => setLayerVisibility({ ...layerVisibility, buildings: e.target.checked })}
              />
              <span style={{ color: '#cbd5e1' }}>● Building Footprints</span>
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={layerVisibility.evac}
                onChange={(e) => setLayerVisibility({ ...layerVisibility, evac: e.target.checked })}
              />
              <span style={{ color: '#10b981' }}>● Evacuation Sites</span>
            </label>
          </div>
        </div>
      )}
    </div>
  );
}
