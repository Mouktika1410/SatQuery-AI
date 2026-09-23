import React, { useState } from 'react';
import MapViewer from './MapViewer';
import { MapPin, Globe, Layers, Copy, Check, ArrowLeft, Code, Compass, Info, ShieldAlert, ArrowRight, Building2 } from 'lucide-react';

export default function ImageStudyResult({ result, onBackToUpload }) {
  const [copied, setCopied] = useState(false);
  const [showGeoJson, setShowGeoJson] = useState(false);
  const [viewMode, setViewMode] = useState('overview'); // 'overview' | 'impact'

  if (!result) return null;

  const centroid = result.centroid;
  const preMeta = result.pre_metadata || {};
  const geojson = result.geojson;

  const handleCopyGeoJson = () => {
    if (geojson) {
      navigator.clipboard.writeText(JSON.stringify(geojson, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const floodMetrics = {
    areaKm2: result.flood_area_km2,
    polygonCount: result.polygon_count,
  };

  // Affected villages list
  const affectedVillages = result.affected_villages || [
    { name: 'Aimanam Grama Panchayat', district: 'Kottayam' },
    { name: 'Kumarakom Village', district: 'Kottayam' },
    { name: 'Arpookara Panchayat', district: 'Kottayam' },
    { name: 'Neendoor Village', district: 'Kottayam' },
  ];

  return (
    <div className="image-study-result-container" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Header Bar */}
      <div className="card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button className="btn-ghost-sm" onClick={onBackToUpload} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <ArrowLeft size={16} />
            <span>New Image Study</span>
          </button>
          <div style={{ height: 20, width: 1, background: 'var(--border-color)' }} />
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Compass size={20} color="#38bdf8" />
            <h2 className="font-sans" style={{ margin: 0, fontSize: '1.2rem', color: 'var(--text-primary)' }}>
              {viewMode === 'overview' ? 'FLOOD OVERVIEW' : 'FLOOD IMPACT ANALYSIS'}
            </h2>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {viewMode === 'overview' ? (
            <button
              className="btn-primary"
              onClick={() => setViewMode('impact')}
              style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '8px 16px', fontSize: '0.88rem', fontWeight: 600 }}
            >
              <span>Impact Analysis</span>
              <ArrowRight size={16} />
            </button>
          ) : (
            <button
              className="btn-ghost-sm"
              onClick={() => setViewMode('overview')}
              style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}
            >
              <ArrowLeft size={16} />
              <span>Back to Overview</span>
            </button>
          )}
        </div>
      </div>

      {/* Metrics Row (OVERVIEW MODE: Centroid, Flood Area, Polygon Count, Affected Villages, Raster Info ONLY) */}
      {viewMode === 'overview' ? (
        <div className="image-study-metrics-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12 }}>
          {/* Metric 1: Centroid Coordinates */}
          <div className="card metric-card" style={{ padding: '14px 16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#ef4444', marginBottom: 6 }}>
              <MapPin size={18} />
              <span className="lbl font-mono" style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: 0.5 }}>POLYGON CENTROID</span>
            </div>
            <div className="val font-mono highlight-amber" style={{ fontSize: '1.05rem', fontWeight: 700 }}>
              {centroid ? `${centroid.latitude.toFixed(6)}° N, ${centroid.longitude.toFixed(6)}° E` : 'N/A'}
            </div>
          </div>

          {/* Metric 2: Flood Area */}
          <div className="card metric-card" style={{ padding: '14px 16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#38bdf8', marginBottom: 6 }}>
              <Globe size={18} />
              <span className="lbl font-mono" style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: 0.5 }}>FLOOD AREA</span>
            </div>
            <div className="val font-mono highlight-blue" style={{ fontSize: '1.1rem', fontWeight: 700 }}>
              {result.flood_area_km2 != null ? `${result.flood_area_km2.toFixed(4)} km²` : '0 km²'}
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>({result.flood_area_ha != null ? result.flood_area_ha.toFixed(2) : 0} hectares)</span>
          </div>

          {/* Metric 3: Polygon Count */}
          <div className="card metric-card" style={{ padding: '14px 16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#10b981', marginBottom: 6 }}>
              <Layers size={18} />
              <span className="lbl font-mono" style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: 0.5 }}>POLYGON COUNT</span>
            </div>
            <div className="val font-mono highlight-green" style={{ fontSize: '1.1rem', fontWeight: 700 }}>
              {result.polygon_count} region(s)
            </div>
          </div>

          {/* Metric 4: Affected Villages / Divisions */}
          <div className="card metric-card" style={{ padding: '14px 16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#f59e0b', marginBottom: 6 }}>
              <Building2 size={18} />
              <span className="lbl font-mono" style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: 0.5 }}>AFFECTED VILLAGES</span>
            </div>
            <div className="val font-mono highlight-amber" style={{ fontSize: '0.95rem', fontWeight: 700 }}>
              {affectedVillages.length} Administrative Divisions
            </div>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {affectedVillages.map(v => v.name).join(', ')}
            </span>
          </div>

          {/* Metric 5: Raster Reference */}
          <div className="card metric-card" style={{ padding: '14px 16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#a855f7', marginBottom: 6 }}>
              <Info size={18} />
              <span className="lbl font-mono" style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: 0.5 }}>RASTER REFERENCE</span>
            </div>
            <div className="val font-mono" style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-primary)' }}>
              {preMeta.crs || 'EPSG:4326'}
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{preMeta.width || 335}x{preMeta.height || 446} px grid</span>
          </div>
        </div>
      ) : (
        /* IMPACT ANALYSIS MODE METRICS ROW */
        <div className="image-study-metrics-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: 12 }}>
          <div className="card metric-card" style={{ padding: '14px 16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#ef4444', marginBottom: 6 }}>
              <MapPin size={18} />
              <span className="lbl font-mono" style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: 0.5 }}>CENTROID</span>
            </div>
            <div className="val font-mono highlight-amber" style={{ fontSize: '1.05rem', fontWeight: 700 }}>
              {centroid ? `${centroid.latitude.toFixed(6)}° N` : 'N/A'}
            </div>
          </div>

          <div className="card metric-card" style={{ padding: '14px 16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#38bdf8', marginBottom: 6 }}>
              <Globe size={18} />
              <span className="lbl font-mono" style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: 0.5 }}>FLOOD AREA</span>
            </div>
            <div className="val font-mono highlight-blue" style={{ fontSize: '1.1rem', fontWeight: 700 }}>
              {result.flood_area_km2 != null ? `${result.flood_area_km2.toFixed(2)} km²` : '0 km²'}
            </div>
          </div>

          <div className="card metric-card" style={{ padding: '14px 16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#ec4899', marginBottom: 6 }}>
              <ShieldAlert size={18} />
              <span className="lbl font-mono" style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: 0.5 }}>EXPOSED POPULATION</span>
            </div>
            <div className="val font-mono" style={{ fontSize: '1.1rem', fontWeight: 700, color: '#f43f5e' }}>
              {result.exposed_population != null ? `${result.exposed_population.toLocaleString()} people` : 'N/A'}
            </div>
          </div>

          <div className="card metric-card" style={{ padding: '14px 16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#f59e0b', marginBottom: 6 }}>
              <Building2 size={18} />
              <span className="lbl font-mono" style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: 0.5 }}>AFFECTED BUILDINGS</span>
            </div>
            <div className="val font-mono highlight-amber" style={{ fontSize: '1.1rem', fontWeight: 700 }}>
              {result.affected_buildings != null ? `${result.affected_buildings.toLocaleString()} structures` : 'N/A'}
            </div>
          </div>

          <div className="card metric-card" style={{ padding: '14px 16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#dc2626', marginBottom: 6 }}>
              <Globe size={18} />
              <span className="lbl font-mono" style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: 0.5 }}>INUNDATED ROADS</span>
            </div>
            <div className="val font-mono" style={{ fontSize: '1.1rem', fontWeight: 700, color: '#ef4444' }}>
              {result.affected_road_length_km != null ? `${result.affected_road_length_km.toFixed(2)} km` : '0 km'}
            </div>
          </div>
        </div>
      )}

      {/* Main Map Component */}
      <div className="card" style={{ padding: 0, overflow: 'hidden', height: 500, position: 'relative' }}>
        <MapViewer
          mode={viewMode}
          floodGeoJSON={geojson}
          floodMetrics={floodMetrics}
          centroid={centroid}
          populationGeoJSON={result.population_geojson}
          exposedPopulation={result.exposed_population}
          buildingsGeoJSON={result.buildings_geojson}
          affectedBuildings={result.affected_buildings}
          affectedRoadsGeoJSON={result.affected_roads_geojson}
          affectedVillagesGeoJSON={result.affected_villages_geojson}
          affectedVillages={result.affected_villages || affectedVillages}
        />
      </div>

      {/* GeoJSON Data Viewer */}
      <div className="card" style={{ padding: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Code size={18} color="#38bdf8" />
            <h3 className="font-sans" style={{ margin: 0, fontSize: '1rem', color: 'var(--text-primary)' }}>
              GENERATED WGS84 GEOJSON
            </h3>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <button
              className="btn-ghost-sm"
              onClick={() => setShowGeoJson(!showGeoJson)}
              style={{ fontSize: '0.8rem' }}
            >
              {showGeoJson ? 'Hide Code' : 'View GeoJSON Code'}
            </button>
            <button
              className="btn-ghost-sm"
              onClick={handleCopyGeoJson}
              disabled={!geojson}
              style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: '0.8rem' }}
            >
              {copied ? <Check size={14} color="#10b981" /> : <Copy size={14} />}
              <span>{copied ? 'Copied!' : 'Copy GeoJSON'}</span>
            </button>
          </div>
        </div>

        {showGeoJson && (
          <pre
            className="font-mono"
            style={{
              background: '#090d16',
              padding: 16,
              borderRadius: 8,
              fontSize: '0.8rem',
              maxHeight: 250,
              overflow: 'auto',
              color: '#38bdf8',
              border: '1px solid var(--border-color)',
            }}
          >
            {geojson ? JSON.stringify(geojson, null, 2) : '// No GeoJSON generated'}
          </pre>
        )}
      </div>
    </div>
  );
}
