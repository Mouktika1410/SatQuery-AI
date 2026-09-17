import React, { useEffect, useRef } from 'react';
import {
  Activity,
  FileText,
  Layers,
  Building,
  Users,
  CheckCircle2,
  AlertTriangle,
  Info,
  Building2,
  MapPin,
  ShieldAlert,
  Satellite,
  BarChart2,
  TrendingUp,
  Sliders
} from 'lucide-react';

function fmt(val, unit = '', decimals = 2) {
  if (val === null || val === undefined) return null;
  if (typeof val === 'number') return `${val.toFixed(decimals)} ${unit}`.trim();
  return String(val);
}

function MetricCard({ icon: Icon, value, label, subtext, highlight = false }) {
  const isNA = value === null || value === undefined;
  return (
    <div className={`metric-item ${highlight ? 'highlight' : ''}`}>
      <div className="metric-header">
        {Icon && <span className="metric-icon"><Icon size={16} color={highlight ? '#38bdf8' : '#94a3b8'} /></span>}
        <span className={`metric-value ${isNA ? 'na' : ''}`}>
          {isNA ? 'N/A' : value}
        </span>
      </div>
      <div className="metric-label">{label}</div>
      {subtext && <div className="metric-subtext">{subtext}</div>}
    </div>
  );
}

function SatelliteImageCard({ title, accentColor, file, validationData, sceneMetrics, isEvent = false }) {
  const [url, setUrl] = React.useState(null);
  const [imgErr, setImgErr] = React.useState(false);

  React.useEffect(() => {
    if (file) {
      const u = URL.createObjectURL(file);
      setUrl(u);
      return () => URL.revokeObjectURL(u);
    }
  }, [file]);

  const filename = validationData?.filename || file?.name || (isEvent ? 'post_flood.tif' : 'pre_flood.tif');
  const dims = validationData?.width && validationData?.height ? `${validationData.width} × ${validationData.height} px` : null;
  const crs = validationData?.crs_epsg ? `EPSG:${validationData.crs_epsg}` : (validationData?.crs ? String(validationData.crs) : 'Georeferenced');
  const bands = validationData?.band_count ? `${validationData.band_count} Band${validationData.band_count > 1 ? 's' : ''}` : null;
  const dataType = validationData?.data_type ? validationData.data_type.toUpperCase() : null;
  const size = file?.size ? `${(file.size / 1024).toFixed(1)} KB` : null;

  return (
    <div style={{
      background: isEvent ? 'linear-gradient(180deg, #1f1013 0%, #0d1117 100%)' : 'linear-gradient(180deg, #101827 0%, #0d1117 100%)',
      border: `1.5px solid ${accentColor}`,
      borderRadius: '8px',
      padding: '10px',
      display: 'flex',
      flexDirection: 'column',
      gap: '8px',
      boxShadow: `0 4px 14px ${accentColor}20`,
    }}>
      {/* Header Bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: `1px solid ${accentColor}30`, paddingBottom: '6px' }}>
        <span style={{ fontSize: '0.78rem', fontWeight: 700, color: accentColor, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          {title}
        </span>
        <span style={{
          fontSize: '0.62rem',
          fontWeight: 600,
          background: `${accentColor}25`,
          color: accentColor,
          padding: '2px 8px',
          borderRadius: '12px',
          border: `1px solid ${accentColor}50`
        }}>
          {isEvent ? 'Event Scene' : 'Baseline Scene'}
        </span>
      </div>

      {/* Image or High-Tech GIS Raster Preview */}
      {url && !imgErr ? (
        <img
          src={url}
          alt={title}
          onError={() => setImgErr(true)}
          style={{ width: '100%', height: '100px', objectFit: 'cover', borderRadius: '5px', border: `1px solid ${accentColor}40` }}
        />
      ) : (
        <div style={{
          height: '100px',
          background: `radial-gradient(circle at center, ${accentColor}18 0%, #0b0f19 100%)`,
          borderRadius: '5px',
          border: `1px dashed ${accentColor}50`,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '8px',
          textAlign: 'center',
          position: 'relative',
          overflow: 'hidden'
        }}>
          <div style={{
            position: 'absolute',
            inset: 0,
            opacity: 0.1,
            backgroundImage: `linear-gradient(${accentColor} 1px, transparent 1px), linear-gradient(90deg, ${accentColor} 1px, transparent 1px)`,
            backgroundSize: '14px 14px'
          }} />
          <Satellite size={24} color={accentColor} style={{ zIndex: 1, marginBottom: 2 }} />
          <div style={{ fontSize: '0.72rem', fontWeight: 600, color: '#f1f5f9', zIndex: 1, wordBreak: 'break-all', maxWidth: '100%' }}>
            {filename}
          </div>
          <div style={{ fontSize: '0.63rem', color: '#94a3b8', zIndex: 1, marginTop: '2px' }}>
            {isEvent ? 'Post-Flood Inundation Raster' : 'Pre-Flood Baseline Raster'}
          </div>
        </div>
      )}

      {/* Metadata Badges */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px', fontSize: '0.65rem' }}>
        <div style={{ background: '#0f172a', padding: '3px 6px', borderRadius: '4px', border: '1px solid #1e293b', color: '#cbd5e1' }}>
          Dimensions: <strong style={{ color: '#f8fafc' }}>{dims || 'Raster Bounds'}</strong>
        </div>
        <div style={{ background: '#0f172a', padding: '3px 6px', borderRadius: '4px', border: '1px solid #1e293b', color: '#cbd5e1' }}>
          CRS: <strong style={{ color: '#f8fafc' }}>{crs}</strong>
        </div>
        {bands && (
          <div style={{ background: '#0f172a', padding: '3px 6px', borderRadius: '4px', border: '1px solid #1e293b', color: '#cbd5e1' }}>
            Bands: <strong style={{ color: '#f8fafc' }}>{bands}</strong>
          </div>
        )}
        {size && (
          <div style={{ background: '#0f172a', padding: '3px 6px', borderRadius: '4px', border: '1px solid #1e293b', color: '#cbd5e1' }}>
            Size: <strong style={{ color: '#f8fafc' }}>{size}</strong>
          </div>
        )}
      </div>
    </div>
  );
}

function ImageSideBySidePreview({ result, preFile, postFile }) {
  const preValidation = result?.validation?.pre_flood || null;
  const postValidation = result?.validation?.post_flood || null;
  const floodedArea = result?.polygons?.total_area_km2 ?? result?.detection?.flood_area_km2 ?? null;
  const areaHa = result?.polygons?.total_area_ha ?? (floodedArea != null ? floodedArea * 100 : null);
  const floodPct = result?.detection?.flood_percentage ?? null;
  const polyCount = result?.polygons?.polygon_count ?? null;
  const method = result?.detection?.method_used || 'NDWI / Relative Difference';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: '10px',
        alignItems: 'stretch'
      }}>
        <SatelliteImageCard
          title="Before Flood"
          accentColor="#3b82f6"
          file={preFile}
          validationData={preValidation}
          isEvent={false}
        />
        <SatelliteImageCard
          title="After Flood"
          accentColor="#ef4444"
          file={postFile}
          validationData={postValidation}
          sceneMetrics={{ floodedArea, floodPct }}
          isEvent={true}
        />
      </div>

      {floodedArea != null && (
        <div style={{
          background: '#0d131f',
          border: '1px solid #1e293b',
          borderRadius: '6px',
          padding: '8px 10px'
        }}>
          <div style={{ fontSize: '0.7rem', fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '6px' }}>
            Computed Scene Delta & Change Metrics
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px', fontSize: '0.68rem' }}>
            <div style={{ background: '#182030', padding: '5px 8px', borderRadius: '4px', border: '1px solid #2d3748' }}>
              <span style={{ color: '#94a3b8' }}>Inundation Shift:</span>{' '}
              <strong style={{ color: '#60a5fa' }}>0.00 ➔ {floodedArea.toFixed(2)} km²</strong>
              {areaHa != null && <span style={{ color: '#94a3b8' }}> ({areaHa.toFixed(0)} ha)</span>}
            </div>
            {floodPct != null && (
              <div style={{ background: '#182030', padding: '5px 8px', borderRadius: '4px', border: '1px solid #2d3748' }}>
                <span style={{ color: '#94a3b8' }}>Scene Coverage Shift:</span>{' '}
                <strong style={{ color: '#f59e0b' }}>+ {floodPct.toFixed(2)}%</strong>
              </div>
            )}
            {polyCount != null && (
              <div style={{ background: '#182030', padding: '5px 8px', borderRadius: '4px', border: '1px solid #2d3748' }}>
                <span style={{ color: '#94a3b8' }}>Vector Features:</span>{' '}
                <strong style={{ color: '#34d399' }}>{polyCount} flood polygon(s)</strong>
              </div>
            )}
            <div style={{ background: '#182030', padding: '5px 8px', borderRadius: '4px', border: '1px solid #2d3748' }}>
              <span style={{ color: '#94a3b8' }}>Algorithm:</span>{' '}
              <strong style={{ color: '#e2e8f0' }}>{method}</strong>
            </div>
          </div>
        </div>
      )}

      {/* Clean Neutral Status Note */}
      <div style={{
        marginTop: '10px',
        padding: '6px 10px',
        background: '#161b26',
        border: '1px solid #2d3748',
        borderRadius: '6px',
        fontSize: '0.7rem',
        color: '#94a3b8',
        display: 'flex',
        alignItems: 'center',
        gap: '6px'
      }}>
        <Info size={14} color="#60a5fa" />
        <span>AI visual analysis is currently unavailable.</span>
      </div>
    </div>
  );
}

export default function MetricsPanel({ result, preFile, postFile, selectedFeature, onSelectFeature }) {
  const containerRef = useRef(null);

  useEffect(() => {
    if (result && containerRef.current) {
      containerRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, [result]);

  if (!result) return null;

  const { detection, polygons, impact, priority_scores, evacuation, warnings } = result;

  const floodedArea = fmt(polygons?.total_area_km2 ?? detection?.flood_area_km2, 'km²');
  const floodPct = fmt(detection?.flood_percentage, '%');
  const detectMethod = detection?.method_used ?? '—';
  const polygonCount = polygons?.polygon_count ?? '—';
  const availability = impact?.data_availability;

  const layerDefs = [
    { key: 'villages', label: 'Villages Boundary' },
    { key: 'population', label: 'Population Grid' },
    { key: 'buildings', label: 'Building Footprints' },
    { key: 'roads', label: 'Road Network' },
    { key: 'dem', label: 'DEM Elevation' },
  ];

  return (
    <div ref={containerRef} className="dashboard-metrics-panel">
      {/* System Warnings */}
      {warnings && warnings.length > 0 && (
        <div className="card card-warning">
          <div className="card-title" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <AlertTriangle size={16} color="#f59e0b" />
            <span>Operational Warnings</span>
          </div>
          {warnings.map((w, i) => (
            <div key={i} className="notice warning-notice">
              {w}
            </div>
          ))}
        </div>
      )}

      {/* 1. Flood Detection Summary */}
      {detection?.success && (
        <div className="card">
          <div className="card-title" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <Activity size={16} color="#38bdf8" />
            <span>Flood Detection Summary</span>
          </div>

          <div className="metric-grid">
            <MetricCard
              icon={Activity}
              value={floodedArea}
              label="Flooded Area"
              highlight={true}
            />
            <MetricCard
              icon={TrendingUp}
              value={floodPct}
              label="Image Coverage"
            />
            <MetricCard
              icon={Sliders}
              value={detectMethod}
              label="Detection Method"
            />
            <MetricCard
              icon={Layers}
              value={polygonCount}
              label="Polygon Count"
            />
          </div>

          {detection.notes && detection.notes.length > 0 && (
            <div className="info-notice">
              <Info size={14} style={{ marginRight: 6 }} />
              {detection.notes.slice(0, 2).join(' · ')}
            </div>
          )}
        </div>
      )}

      {/* VLM Satellite Visual Comparison */}
      {result.vlm_analysis && (
        <div className="card">
          <div className="card-title" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <Satellite size={16} color="#38bdf8" />
            <span>Satellite Visual Comparison</span>
          </div>
          {result.vlm_analysis.available ? (
            <div style={{ fontSize: '0.85rem', lineHeight: '1.45', color: '#e2e8f0' }}>
              <div style={{ whiteSpace: 'pre-line', marginBottom: 8 }}>
                {result.vlm_analysis.comparison}
              </div>
              {result.vlm_analysis.disclaimer && (
                <div style={{ fontSize: '0.7rem', color: '#9ca3af', fontStyle: 'italic', borderTop: '1px solid #2d3748', paddingTop: 6 }}>
                  {result.vlm_analysis.disclaimer}
                </div>
              )}
            </div>
          ) : (
            <div style={{ fontSize: '0.85rem', lineHeight: '1.45', color: '#e2e8f0' }}>
              <ImageSideBySidePreview result={result} preFile={preFile} postFile={postFile} />
            </div>
          )}
        </div>
      )}

      {/* 2. Impact & Exposure */}
      <div className="card">
        <div className="card-title" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <BarChart2 size={16} color="#38bdf8" />
          <span>Impact & Exposure</span>
        </div>

        <div className="metric-grid">
          <MetricCard
            icon={Users}
            value={
              impact?.affected_population != null
                ? impact.affected_population.toLocaleString()
                : null
            }
            label="Affected Population"
            subtext="Modeled estimate"
          />
          <MetricCard
            icon={Building}
            value={
              impact?.affected_buildings != null
                ? impact.affected_buildings.toLocaleString()
                : null
            }
            label="Submerged Buildings"
            subtext="Footprint intersections"
          />
          <MetricCard
            icon={Activity}
            value={fmt(impact?.affected_road_length_km, 'km')}
            label="Inundated Roads"
            subtext="Flooded segments"
          />
          <MetricCard
            icon={Building2}
            value={impact?.affected_villages?.length ?? null}
            label="Affected Villages"
            subtext="Boundary overlaps"
          />
        </div>
      </div>

      {/* 3. Affected Villages */}
      <div className="card">
        <div className="card-title" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <Building2 size={16} color="#f59e0b" />
          <span>Affected Villages</span>
        </div>

        {impact?.affected_villages?.length > 0 ? (
          <ul className="village-list">
            {impact.affected_villages.map((v, i) => {
              const isSelected = selectedFeature?.type === 'village' && selectedFeature?.name === v.name;
              return (
                <li
                  key={i}
                  className={`village-item interactive ${isSelected ? 'selected' : ''}`}
                  onClick={() => onSelectFeature && onSelectFeature(isSelected ? null : { type: 'village', name: v.name })}
                  title="Click to locate on GIS map"
                >
                  <span className="village-name" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <MapPin size={14} color="#f59e0b" />
                    {v.name}
                  </span>
                  <span className="village-area">{v.area_flooded_km2?.toFixed(2)} km² flooded</span>
                </li>
              );
            })}
          </ul>
        ) : (
          <div className="info-notice">
            {availability?.villages === false
              ? 'Village boundary GIS layer not available.'
              : 'No mapped village boundaries intersect the flood area.'}
          </div>
        )}
      </div>

      {/* 4. Data Layer Availability */}
      <div className="card">
        <div className="card-title" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <Layers size={16} color="#38bdf8" />
          <span>Data Layer Availability</span>
        </div>

        {availability ? (
          <div className="data-availability-grid">
            {layerDefs.map(({ key, label }) => {
              const isAvail = Boolean(availability[key]);
              return (
                <div key={key} className={`avail-badge-row ${isAvail ? 'yes' : 'no'}`}>
                  <span className="avail-dot">{isAvail ? '●' : '○'}</span>
                  <span className="avail-name">{label}</span>
                  <span className="avail-status">{isAvail ? 'Available' : 'Missing'}</span>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="info-notice">Data availability metadata not recorded.</div>
        )}
      </div>

      {/* 5. Priority Analysis */}
      <div className="card">
        <div className="card-title" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <ShieldAlert size={16} color="#ef4444" />
          <span>Priority Analysis</span>
        </div>

        {priority_scores?.length > 0 ? (
          <>
            <table className="priority-table">
              <thead>
                <tr>
                  <th style={{ width: '30px' }}>#</th>
                  <th>Village</th>
                  <th style={{ width: '110px' }}>Priority Score</th>
                </tr>
              </thead>
              <tbody>
                {priority_scores.map((p) => {
                  const isSelected = selectedFeature?.type === 'village' && selectedFeature?.name === p.village_name;
                  return (
                    <tr
                      key={p.rank}
                      className={`priority-row interactive ${isSelected ? 'selected' : ''}`}
                      onClick={() => onSelectFeature && onSelectFeature(isSelected ? null : { type: 'village', name: p.village_name })}
                      title="Click to highlight village on map"
                    >
                      <td className="rank-col">{p.rank}</td>
                      <td className="name-col">{p.village_name}</td>
                      <td className="score-col">
                        <div className="score-bar-bg">
                          <div
                            className="score-bar-fill"
                            style={{
                              width: `${Math.min(100, Math.max(5, p.priority_score * 100)).toFixed(1)}%`,
                            }}
                          />
                        </div>
                        <span className="score-val">{p.priority_score.toFixed(3)}</span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>

            <div className="notice disclaimer-notice">
              <b>Decision Support Note:</b> Heuristic priority score based on available normalized geospatial factors. This is a decision-support metric, <i>not a machine-learning prediction</i>.
            </div>
          </>
        ) : (
          <div className="info-notice">
            No priority rankings computed (requires affected villages).
          </div>
        )}
      </div>

      {/* 6. Candidate Evacuation Locations */}
      <div className="card">
        <div className="card-title" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <ShieldAlert size={16} color="#10b981" />
          <span>Candidate Evacuation Locations</span>
        </div>

        {evacuation?.candidates?.length > 0 ? (
          <>
            <div style={{ fontSize: '0.74rem', color: 'var(--text-secondary)', marginBottom: 8 }}>
              {evacuation.total_found} candidate facility site(s) located outside flood zone:
            </div>

            <ul className="evac-list">
              {evacuation.candidates.map((c, i) => {
                const isSelected = selectedFeature?.type === 'evacuation' && selectedFeature?.name === c.name;
                return (
                  <li
                    key={i}
                    className={`evac-item interactive ${isSelected ? 'selected' : ''}`}
                    onClick={() => onSelectFeature && onSelectFeature(isSelected ? null : { type: 'evacuation', name: c.name, lat: c.lat, lon: c.lon })}
                    title="Click to locate candidate site on map"
                  >
                    <div className="evac-header">
                      <span className="evac-name" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <Building2 size={14} color="#10b981" />
                        {c.name}
                      </span>
                      <span className="evac-type">{c.type}</span>
                    </div>
                    <div className="evac-metrics">
                      {c.distance_to_flood_km != null && (
                        <span>Distance to flood: <b>{c.distance_to_flood_km.toFixed(2)} km</b></span>
                      )}
                      {c.elevation_m != null && (
                        <span> · DEM Elevation: <b>{c.elevation_m.toFixed(1)} m</b></span>
                      )}
                    </div>
                  </li>
                );
              })}
            </ul>

            <div className="notice disclaimer-notice">
              <b>Operational Caution:</b> Candidate accessible sites for on-ground verification only. These locations are NOT guaranteed safe zones or verified evacuation centers.
            </div>
          </>
        ) : (
          <div className="info-notice">
            {evacuation?.filtered_reason || 'No candidate accessible sites identified.'}
          </div>
        )}
      </div>
    </div>
  );
}
