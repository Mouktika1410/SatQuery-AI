import React from 'react';

function fmt(val, unit = '', decimals = 2) {
  if (val === null || val === undefined) return null;
  if (typeof val === 'number') return `${val.toFixed(decimals)} ${unit}`.trim();
  return String(val);
}

function MetricItem({ value, label }) {
  const isNA = value === null || value === undefined;
  return (
    <div className="metric-item">
      <div className={`metric-value ${isNA ? 'na' : ''}`}>
        {isNA ? 'N/A' : value}
      </div>
      <div className="metric-label">{label}</div>
    </div>
  );
}

function DataAvailabilityBadges({ availability }) {
  if (!availability) return null;
  return (
    <div className="data-availability">
      {Object.entries(availability).map(([key, available]) => (
        <span key={key} className={`avail-badge ${available ? 'yes' : 'no'}`}>
          {available ? '✓' : '○'} {key}
        </span>
      ))}
    </div>
  );
}

export default function MetricsPanel({ result }) {
  if (!result) return null;

  const { detection, polygons, impact, priority_scores, evacuation, warnings } = result;

  return (
    <>
      {/* Warnings */}
      {warnings && warnings.length > 0 && (
        <div className="card">
          <div className="card-title">⚠️ Warnings</div>
          {warnings.map((w, i) => (
            <div key={i} className="notice" style={{ marginTop: i > 0 ? 4 : 0 }}>
              {w}
            </div>
          ))}
        </div>
      )}

      {/* Detection Summary */}
      {detection?.success && (
        <div className="card">
          <div className="card-title">🌊 Flood Detection</div>
          <div className="metric-grid">
            <MetricItem
              value={fmt(polygons?.total_area_km2 ?? detection?.flood_area_km2, 'km²')}
              label="Flooded Area"
            />
            <MetricItem
              value={fmt(detection?.flood_percentage, '%')}
              label="Image Coverage"
            />
            <MetricItem
              value={polygons?.polygon_count ?? '—'}
              label="Polygons"
            />
            <MetricItem
              value={detection?.method_used ?? '—'}
              label="Method"
            />
          </div>
          {detection.notes && detection.notes.length > 0 && (
            <div className="info-notice">
              {detection.notes.slice(0, 2).join(' · ')}
            </div>
          )}
        </div>
      )}

      {/* Impact Metrics */}
      <div className="card">
        <div className="card-title">📊 Impact Metrics</div>

        <div className="metric-grid">
          <MetricItem
            value={
              impact?.affected_population !== null && impact?.affected_population !== undefined
                ? impact.affected_population.toLocaleString()
                : null
            }
            label="Est. Population"
          />
          <MetricItem
            value={
              impact?.affected_buildings !== null && impact?.affected_buildings !== undefined
                ? impact.affected_buildings.toLocaleString()
                : null
            }
            label="Buildings"
          />
          <MetricItem
            value={fmt(impact?.affected_road_length_km, 'km')}
            label="Road Length"
          />
          <MetricItem
            value={impact?.affected_villages?.length ?? null}
            label="Villages"
          />
        </div>

        <DataAvailabilityBadges availability={impact?.data_availability} />

        {/* Village list */}
        {impact?.affected_villages?.length > 0 && (
          <>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: 10, marginBottom: 4 }}>
              Affected Villages
            </div>
            <ul className="village-list">
              {impact.affected_villages.slice(0, 8).map((v, i) => (
                <li key={i} className="village-item">
                  <span className="village-name">{v.name}</span>
                  <span className="village-area">{v.area_flooded_km2?.toFixed(2)} km²</span>
                </li>
              ))}
              {impact.affected_villages.length > 8 && (
                <li style={{ fontSize: '0.7rem', color: 'var(--text-muted)', padding: '4px 8px' }}>
                  +{impact.affected_villages.length - 8} more…
                </li>
              )}
            </ul>
          </>
        )}

        {(!impact?.data_availability?.villages &&
          !impact?.data_availability?.buildings &&
          !impact?.data_availability?.roads) && (
          <div className="info-notice" style={{ marginTop: 8 }}>
            No GIS datasets loaded. Add files to <code>data/boundaries/</code>,{' '}
            <code>data/buildings/</code>, <code>data/roads/</code> to compute impact metrics.
          </div>
        )}
      </div>

      {/* Priority Scores */}
      {priority_scores?.length > 0 && (
        <div className="card">
          <div className="card-title">🔴 Priority Rankings</div>
          <table className="priority-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Village</th>
                <th>Score</th>
              </tr>
            </thead>
            <tbody>
              {priority_scores.slice(0, 8).map((p) => (
                <tr key={p.rank}>
                  <td style={{ color: 'var(--accent)', fontWeight: 700 }}>{p.rank}</td>
                  <td>{p.village_name}</td>
                  <td>
                    <div className="score-bar-bg">
                      <div
                        className="score-bar-fill"
                        style={{ width: `${(p.priority_score * 100).toFixed(1)}%` }}
                      />
                    </div>
                    <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
                      {p.priority_score.toFixed(3)}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="notice" style={{ marginTop: 8 }}>
            ⚠️ Heuristic decision-support scores. Not validated predictions.
          </div>
        </div>
      )}

      {/* Evacuation Candidates */}
      {evacuation && (
        <div className="card">
          <div className="card-title">🏫 Candidate Sites</div>
          {evacuation.total_found === 0 ? (
            <div className="info-notice">
              {evacuation.filtered_reason || 'No candidate sites found.'}
              {!evacuation.filtered_reason?.includes('data/pois') && (
                <span> Add a POI GeoJSON to <code>data/pois/</code>.</span>
              )}
            </div>
          ) : (
            <>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: 6 }}>
                {evacuation.total_found} site(s) outside flood boundary
              </div>
              <ul className="evac-list">
                {evacuation.candidates.slice(0, 6).map((c, i) => (
                  <li key={i} className="evac-item">
                    <div className="evac-name">{c.name}</div>
                    <div className="evac-meta">
                      {c.type} · {c.distance_to_flood_km != null
                        ? `${c.distance_to_flood_km.toFixed(2)} km from flood`
                        : 'distance N/A'}
                    </div>
                  </li>
                ))}
                {evacuation.candidates.length > 6 && (
                  <li style={{ fontSize: '0.7rem', color: 'var(--text-muted)', padding: '4px 8px' }}>
                    +{evacuation.candidates.length - 6} more…
                  </li>
                )}
              </ul>
              <div className="notice" style={{ marginTop: 8 }}>
                ⚠️ {evacuation.disclaimer}
              </div>
            </>
          )}
        </div>
      )}
    </>
  );
}
