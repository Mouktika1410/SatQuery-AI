import React, { useState, useEffect } from 'react';
import { Satellite } from 'lucide-react';

const STAGES = [
  { id: 1, title: 'ORBITAL SATELLITE TARGETING', subtitle: 'Acquiring geographic bounding box coordinates...' },
  { id: 2, title: 'ZOOMING INTO ANALYSIS AREA (AOI)', subtitle: 'Aligning coordinate reference system & affine transforms...' },
  { id: 3, title: 'MULTISPECTRAL RASTER COMPARISON', subtitle: 'Analyzing pre-flood baseline vs post-flood event imagery...' },
  { id: 4, title: 'WATER INDEX CHANGE DETECTION', subtitle: 'Scanning pixel intensity diffs & NDWI thresholding...' },
  { id: 5, title: 'INUNDATION REGION EMERGENCE', subtitle: 'Grouping connected water pixels into inundation geometries...' },
  { id: 6, title: 'VECTOR POLYGON BOUNDARY LOCK', subtitle: 'Finalizing GeoJSON boundaries & computing spatial metrics...' },
];

export default function SatelliteTransition({ pipelineResult, preFile, postFile, onComplete }) {
  const [currentStage, setCurrentStage] = useState(1);
  const [progress, setProgress] = useState(0);

  const floodArea = pipelineResult?.polygons?.total_area_km2 ?? pipelineResult?.detection?.flood_area_km2 ?? 41.50;
  const floodAreaStr = floodArea != null ? `${Number(floodArea).toFixed(2)} km²` : '41.50 km²';
  const polygonCount = pipelineResult?.polygons?.polygon_count ?? pipelineResult?.polygons?.geojson?.features?.length ?? 1;
  const crsStr = pipelineResult?.detection?.crs || 'EPSG:4326';
  const methodUsed = pipelineResult?.detection?.method_used || 'SAR + Otsu Water Index';

  const preName = preFile?.name || 'kerala_before_flood.tif';
  const postName = postFile?.name || 'kerala_after_flood.tif';

  useEffect(() => {
    // 6 stages over ~13 seconds
    const interval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) {
          clearInterval(interval);
          setTimeout(() => onComplete && onComplete(), 400);
          return 100;
        }
        return prev + 1;
      });
    }, 130);

    return () => clearInterval(interval);
  }, [onComplete]);

  useEffect(() => {
    if (progress < 18) setCurrentStage(1);
    else if (progress < 36) setCurrentStage(2);
    else if (progress < 54) setCurrentStage(3);
    else if (progress < 72) setCurrentStage(4);
    else if (progress < 90) setCurrentStage(5);
    else setCurrentStage(6);
  }, [progress]);

  const activeInfo = STAGES[currentStage - 1];

  return (
    <div className="sat-transition-overlay">
      {/* Background Satellite View Canvas with Dynamic Stage Zooming */}
      <div className={`sat-canvas-stage stage-${currentStage}`}>
        <div className="sat-tile-basemap" />
        <div className="sat-scanline-beam" />
        <div className="sat-grid-mesh" />

        {/* Stage 1 & 2: Orbital Reticle & Bounding Box */}
        {(currentStage === 1 || currentStage === 2) && (
          <div className="hud-reticle-box">
            <div className="reticle-corner top-left" />
            <div className="reticle-corner top-right" />
            <div className="reticle-corner bottom-left" />
            <div className="reticle-corner bottom-right" />
            <div className="reticle-crosshair" />
            <div className="reticle-coords font-mono">
              TARGET AOI · {crsStr} <br />
              LAT: 9.6791° N · LON: 76.4624° E
            </div>
          </div>
        )}

        {/* Stage 3: Pre / Post Raster Comparison View */}
        {currentStage === 3 && (
          <div className="hud-raster-compare">
            <div className="compare-pane pre-pane">
              <div className="pane-header">BASELINE: {preName}</div>
              <div className="raster-sim-box baseline-sim">
                <span className="sim-label">PRE-EVENT RASTER</span>
              </div>
            </div>
            <div className="compare-divider" />
            <div className="compare-pane post-pane">
              <div className="pane-header">EVENT: {postName}</div>
              <div className="raster-sim-box event-sim">
                <span className="sim-label">POST-EVENT RASTER</span>
              </div>
            </div>
          </div>
        )}

        {/* Stage 4: Progressive Pixel Change Highlight Scan */}
        {currentStage === 4 && (
          <div className="hud-pixel-scan-box">
            <div className="pixel-grid-layer">
              {Array.from({ length: 48 }).map((_, idx) => (
                <div
                  key={idx}
                  className="pixel-node highlighted"
                  style={{ animationDelay: `${(idx % 8) * 0.15}s` }}
                />
              ))}
            </div>
            <div className="hud-scanline-bar" />
            <div className="hud-floating-tag font-mono">
              DETECTING WATER-INDEX CHANGE PIXELS ({methodUsed})
            </div>
          </div>
        )}

        {/* Stage 5: Connected Flooded Region Development */}
        {currentStage === 5 && (
          <div className="hud-flooded-region-box">
            <div className="emerging-flood-shape" />
            <div className="hud-floating-tag font-mono">
              CONNECTING INUNDATION GEOMETRIES ({polygonCount} POLYGONS)
            </div>
          </div>
        )}

        {/* Stage 6: Final Vector Polygon Boundary Lock */}
        {currentStage === 6 && (
          <div className="hud-vector-boundary-box">
            <div className="final-vector-polygon">
              <div className="vector-glow-stroke" />
              <div className="vector-metric-badge font-mono">
                FLOOD BOUNDARY LOCKED: {floodAreaStr}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Floating HUD Operational Controls Header */}
      <div className="sat-hud-topbar">
        <div className="hud-title-group">
          <Satellite size={24} color="#38bdf8" className="hud-sat-icon" />
          <div>
            <div className="hud-title-main">SATQUERY REMOTE SENSING ENGINE</div>
            <div className="hud-stage-step font-mono">STAGE 0{currentStage} / 06 — {activeInfo.title}</div>
          </div>
        </div>

        <button className="hud-skip-btn" onClick={() => onComplete && onComplete()}>
          Skip Sequence →
        </button>
      </div>

      {/* Bottom Progress Bar & Stage Indicator */}
      <div className="sat-hud-bottombar">
        <div className="hud-status-text">{activeInfo.subtitle}</div>
        <div className="hud-progress-track">
          <div className="hud-progress-fill" style={{ width: `${progress}%` }} />
        </div>
      </div>
    </div>
  );
}
