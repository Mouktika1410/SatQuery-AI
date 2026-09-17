import React, { useEffect, useRef } from 'react';

function fmt(val, unit = '', decimals = 2) {
  if (val === null || val === undefined) return null;
  if (typeof val === 'number') return `${val.toFixed(decimals)} ${unit}`.trim();
  return String(val);
}

function MetricCard({ icon, value, label, subtext, highlight = false }) {
  const isNA = value === null || value === undefined;
  return (
    <div className={`metric-item ${highlight ? 'highlight' : ''}`}>
      <div className="metric-header">
        {icon && <span className="metric-icon">{icon}</span>}
        <span className={`metric-value ${isNA ? 'na' : ''}`}>
          {isNA ? 'N/A' : value}
        </span>
      </div>
      <div className="metric-label">{label}</div>
      {subtext && <div className="metric-subtext">{subtext}</div>}
    </div>
  );
}

export default function MetricsPanel({ result, selectedFeature, onSelectFeature }) {
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
          <div className="card-title">⚠️ Operational Warnings</div>
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
          <div className="card-title">
            <span>🌊 Flood Detection Summary</span>
          </div>

          <div className="metric-grid">
            <MetricCard
              icon="🌊"
              value={floodedArea}
              label="Flooded Area"
              highlight={true}
            />
            <MetricCard
              icon="📈"
              value={floodPct}
              label="Image Coverage"
            />
            <MetricCard
              icon="⚙️"
              value={detectMethod}
              label="Detection Method"
            />
            <MetricCard
              icon="📐"
              value={polygonCount}
              label="Polygon Count"
            />
          </div>

          {detection.notes && detection.notes.length > 0 && (
            <div className="info-notice">
              ℹ️ {detection.notes.slice(0, 2).join(' · ')}
            </div>
          )}
        </div>
      )}

      {/* 2. Impact & Exposure */}
      <div className="card">
        <div className="card-title">
          <span>📊 Impact & Exposure</span>
        </div>

        <div className="metric-grid">
          <MetricCard
            icon="👥"
            value={
              impact?.affected_population != null
                ? impact.affected_population.toLocaleString()
                : null
            }
            label="Affected Population"
            subtext="Modeled estimate"
          />
          <MetricCard
            icon="🏠"
            value={
              impact?.affected_buildings != null
                ? impact.affected_buildings.toLocaleString()
                : null
            }
            label="Submerged Buildings"
            subtext="Footprint intersections"
          />
          <MetricCard
            icon="🛣️"
            value={fmt(impact?.affected_road_length_km, 'km')}
            label="Inundated Roads"
            subtext="Flooded segments"
          />
          <MetricCard
            icon="🏘️"
            value={impact?.affected_villages?.length ?? null}
            label="Affected Villages"
            subtext="Boundary overlaps"
          />
        </div>
      </div>

      {/* 3. Affected Villages */}
      <div className="card">
        <div className="card-title">
          <span>🏘️ Affected Villages</span>
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
                  <span className="village-name">🏘️ {v.name}</span>
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
        <div className="card-title">
          <span>📡 Data Layer Availability</span>
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
        <div className="card-title">
          <span>🔴 Priority Analysis</span>
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
              ⚠️ <b>Decision Support Note:</b> Heuristic priority score based on available normalized geospatial factors. This is a decision-support metric, <i>not a machine-learning prediction</i>.
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
        <div className="card-title">
          <span>🏫 Candidate Evacuation Locations</span>
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
                      <span className="evac-name">🏫 {c.name}</span>
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
              ⚠️ <b>Operational Caution:</b> Candidate accessible sites for on-ground verification only. These locations are NOT guaranteed safe zones or verified evacuation centers.
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

