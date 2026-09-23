import React, { useState, useCallback } from 'react';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import LandingPage from './components/LandingPage';
import SatelliteTransition from './components/SatelliteTransition';
import UploadSection from './components/UploadSection';
import StatusIndicator from './components/StatusIndicator';
import MetricsPanel from './components/MetricsPanel';
import MapViewer from './components/MapViewer';
import AiAssistant from './components/AiAssistant';
import { runFullPipeline } from './services/api';
import {
  BarChart2,
  Upload,
  ShieldAlert,
  Focus,
  Play,
  BookOpen,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  Layers,
  Globe,
  Activity,
  ShieldCheck
} from 'lucide-react';

export default function App() {
  const [showLanding, setShowLanding] = useState(true);
  const [showTransition, setShowTransition] = useState(false);
  const [activeTab, setActiveTab] = useState('upload');

  const [analysisState, setAnalysisState] = useState('idle');
  const [sessionId, setSessionId] = useState(null);
  const [pipelineResult, setPipelineResult] = useState(null);
  const [error, setError] = useState(null);

  const [uploadedFiles, setUploadedFiles] = useState({ pre: null, post: null });
  const [selectedFeature, setSelectedFeature] = useState(null);

  // Quick panel toggle on Map Explorer
  const [showMapDrawer, setShowMapDrawer] = useState(true);

  const handleRunAnalysis = useCallback(async (preFile, postFile, options) => {
    setAnalysisState('running');
    setError(null);
    setPipelineResult(null);
    setSessionId(null);
    setUploadedFiles({ pre: preFile, post: postFile });

    try {
      const result = await runFullPipeline(preFile, postFile, options);
      setPipelineResult(result);
      setSessionId(result.session_id);
      setAnalysisState('complete');
      // Stage 2: Show analysis/detection transition from previous sample-data version
      setShowTransition(true);
    } catch (err) {
      const msg = err.message || 'Analysis failed. Check the backend is running.';
      setError(msg);
      setAnalysisState('error');
    }
  }, []);

  const handleTransitionComplete = useCallback(() => {
    setShowTransition(false);
    setShowLanding(false);
    setActiveTab('map');
  }, []);

  const handleGetStarted = useCallback((targetTab) => {
    setShowLanding(false);
    setActiveTab(targetTab || 'upload');
  }, []);

  const handleGoHome = useCallback(() => {
    setShowLanding(true);
  }, []);

  const floodGeoJSON = pipelineResult?.polygons?.geojson || null;
  const floodMetrics = {
    areaKm2: pipelineResult?.polygons?.total_area_km2 ?? pipelineResult?.detection?.flood_area_km2 ?? null,
    floodPercentage: pipelineResult?.detection?.flood_percentage ?? null,
    polygonCount: pipelineResult?.polygons?.polygon_count ?? null,
  };
  const evacuationCandidates = pipelineResult?.evacuation?.candidates || [];
  const affectedVillages = pipelineResult?.impact?.affected_villages || [];
  const affectedVillagesGeoJSON = pipelineResult?.impact?.affected_villages_geojson || null;
  const affectedRoadsGeoJSON = pipelineResult?.impact?.affected_roads_geojson || null;
  const priorityScores = pipelineResult?.priority_scores || [];

  const hasData = Boolean(pipelineResult);

  if (showTransition && pipelineResult) {
    return (
      <SatelliteTransition
        pipelineResult={pipelineResult}
        preFile={uploadedFiles.pre}
        postFile={uploadedFiles.post}
        onComplete={handleTransitionComplete}
      />
    );
  }

  if (showLanding) {
    return (
      <LandingPage
        onGetStarted={handleGetStarted}
        hasAnalysisData={hasData}
      />
    );
  }

  return (
    <div className="app">
      <Header
        status={analysisState}
        activeTab={activeTab}
        onNavigate={(tab) => {
          setShowLanding(false);
          setActiveTab(tab);
        }}
        onGoHome={handleGoHome}
        hasData={hasData}
      />

      <div className="app-workspace">
        <Sidebar
          activeTab={activeTab}
          onSelectTab={(tab) => {
            setShowLanding(false);
            setActiveTab(tab);
          }}
          onGoHome={handleGoHome}
          hasData={hasData}
        />

        <main className="workspace-main">
          {/* TAB 1: MAP EXPLORER (Hero Full View) */}
          {activeTab === 'map' && (
            <div className="map-view-hero">
              <MapViewer
                pipelineResult={pipelineResult}
                preFile={uploadedFiles.pre}
                postFile={uploadedFiles.post}
                floodGeoJSON={floodGeoJSON}
                floodMetrics={floodMetrics}
                evacuationCandidates={evacuationCandidates}
                affectedVillages={affectedVillages}
                affectedVillagesGeoJSON={affectedVillagesGeoJSON}
                affectedRoadsGeoJSON={affectedRoadsGeoJSON}
                priorityScores={priorityScores}
                selectedFeature={selectedFeature}
                onSelectFeature={setSelectedFeature}
              />

              {/* Floating Quick Drawer on Map */}
              <div className={`map-floating-drawer ${showMapDrawer ? 'expanded' : 'collapsed'}`}>
                <div className="drawer-header">
                  <span className="drawer-title" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    {hasData ? (
                      <>
                        <BarChart2 size={15} color="#38bdf8" />
                        <span>Analysis Summary</span>
                      </>
                    ) : (
                      <>
                        <Upload size={15} color="#38bdf8" />
                        <span>Quick Upload</span>
                      </>
                    )}
                  </span>
                  <button
                    className="drawer-toggle-btn"
                    onClick={() => setShowMapDrawer(!showMapDrawer)}
                    title={showMapDrawer ? 'Collapse overlay' : 'Expand overlay'}
                  >
                    {showMapDrawer ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
                  </button>
                </div>

                {showMapDrawer && (
                  <div className="drawer-body">
                    {!hasData ? (
                      <UploadSection
                        onRunAnalysis={handleRunAnalysis}
                        isRunning={analysisState === 'running'}
                      />
                    ) : (
                      <div className="drawer-summary-metrics">
                        <div className="drawer-stat-grid">
                          <div className="drawer-stat">
                            <span className="lbl">Flooded Area</span>
                            <span className="val highlight-blue">
                              {floodMetrics.areaKm2 != null ? `${Number(floodMetrics.areaKm2).toFixed(2)} km²` : 'N/A'}
                            </span>
                          </div>
                          <div className="drawer-stat">
                            <span className="lbl">Villages Affected</span>
                            <span className="val highlight-amber">
                              {affectedVillages.length}
                            </span>
                          </div>
                        </div>

                        <div className="drawer-action-row">
                          <button
                            className="btn-ghost-sm"
                            onClick={() => setActiveTab('impact')}
                          >
                            Full Impact Metrics →
                          </button>
                          <button
                            className="btn-ghost-sm"
                            onClick={() => setActiveTab('ai')}
                          >
                            Ask AI Assistant →
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 2: IMPACT ANALYSIS */}
          {activeTab === 'impact' && (
            <div className="split-impact-view">
              <div className="impact-metrics-container">
                {pipelineResult ? (
                  <MetricsPanel
                    result={pipelineResult}
                    preFile={uploadedFiles.pre}
                    postFile={uploadedFiles.post}
                    selectedFeature={selectedFeature}
                    onSelectFeature={setSelectedFeature}
                  />
                ) : (
                  <div className="empty-state-card card">
                    <BarChart2 size={32} color="#38bdf8" className="empty-icon" />
                    <h3>No Impact Analysis Data</h3>
                    <p>Upload pre & post flood GeoTIFF rasters to generate hydro-spatial impact metrics.</p>
                    <button
                      className="btn-primary"
                      style={{ width: 'auto', marginTop: 12 }}
                      onClick={() => setActiveTab('upload')}
                    >
                      Go to Data Upload →
                    </button>
                  </div>
                )}
              </div>

              {/* Auxiliary Map Preview */}
              <div className="impact-map-side">
                <MapViewer
                  pipelineResult={pipelineResult}
                  preFile={uploadedFiles.pre}
                  postFile={uploadedFiles.post}
                  floodGeoJSON={floodGeoJSON}
                  floodMetrics={floodMetrics}
                  evacuationCandidates={evacuationCandidates}
                  affectedVillages={affectedVillages}
                  affectedVillagesGeoJSON={affectedVillagesGeoJSON}
                  affectedRoadsGeoJSON={affectedRoadsGeoJSON}
                  priorityScores={priorityScores}
                  selectedFeature={selectedFeature}
                  onSelectFeature={setSelectedFeature}
                  skipAnimation={true}
                />
              </div>
            </div>
          )}

          {/* TAB 3: EVACUATION SITES */}
          {activeTab === 'evacuation' && (
            <div className="split-impact-view">
              <div className="impact-metrics-container">
                <div className="card">
                  <div className="card-title" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <ShieldAlert size={16} color="#10b981" />
                    <span>Candidate Evacuation Sites Screening</span>
                  </div>

                  {evacuationCandidates.length > 0 ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                      <div className="alert-box-warning" style={{ margin: 0, display: 'flex', alignItems: 'center', gap: 6 }}>
                        <AlertTriangle size={14} color="#f59e0b" />
                        <span><b>UNVERIFIED SITES:</b> Screened automatically outside the flood inundation buffer zone. Physical ground inspection required before deployment.</span>
                      </div>

                      <div className="evac-table-container">
                        <table className="priority-table">
                          <thead>
                            <tr>
                              <th>Facility Name</th>
                              <th>Type</th>
                              <th>Flood Dist</th>
                              <th>Elevation</th>
                              <th>Action</th>
                            </tr>
                          </thead>
                          <tbody>
                            {evacuationCandidates.map((c, i) => (
                              <tr
                                key={i}
                                className={(selectedFeature?.type === 'evac' || selectedFeature?.type === 'evacuation') && selectedFeature?.name === c.name ? 'row-selected' : ''}
                                onClick={() => setSelectedFeature({ type: 'evac', name: c.name, data: c })}
                                style={{ cursor: 'pointer' }}
                              >
                                <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{c.name}</td>
                                <td><span className="table-badge badge-green">{c.type}</span></td>
                                <td className="highlight-green" style={{ fontWeight: 600 }}>
                                  {c.distance_to_flood_km != null ? `${c.distance_to_flood_km.toFixed(2)} km` : 'Safe Zone'}
                                </td>
                                <td>{c.elevation_m != null ? `${c.elevation_m.toFixed(1)} m` : 'N/A'}</td>
                                <td>
                                  <button
                                    className="btn-ghost-sm"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      setSelectedFeature({ type: 'evac', name: c.name, data: c });
                                      setActiveTab('map');
                                    }}
                                    style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}
                                  >
                                    <Focus size={13} />
                                    <span>Locate</span>
                                  </button>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  ) : (
                    <div className="empty-state-card">
                      <ShieldAlert size={32} color="#10b981" className="empty-icon" />
                      <h3>No Evacuation Candidates Screened</h3>
                      <p>Run flood analysis on baseline & event rasters to identify safe candidates outside the inundation zone.</p>
                      <button
                        className="btn-primary"
                        style={{ width: 'auto', marginTop: 12 }}
                        onClick={() => setActiveTab('upload')}
                      >
                        Start Analysis →
                      </button>
                    </div>
                  )}
                </div>
              </div>

              <div className="impact-map-side">
                <MapViewer
                  pipelineResult={pipelineResult}
                  preFile={uploadedFiles.pre}
                  postFile={uploadedFiles.post}
                  floodGeoJSON={floodGeoJSON}
                  floodMetrics={floodMetrics}
                  evacuationCandidates={evacuationCandidates}
                  affectedVillages={affectedVillages}
                  affectedVillagesGeoJSON={affectedVillagesGeoJSON}
                  affectedRoadsGeoJSON={affectedRoadsGeoJSON}
                  priorityScores={priorityScores}
                  selectedFeature={selectedFeature}
                  onSelectFeature={setSelectedFeature}
                />
              </div>
            </div>
          )}

          {/* TAB 4: UPLOAD & METHODOLOGY */}
          {activeTab === 'upload' && (
            <div className="upload-view-container">
              {/* Top Row: 2 Equal Column Cards matching Reference Image */}
              <div className="upload-top-grid">
                {/* Left Column: Image Ingestion & Analysis */}
                <div className="upload-ingestion-card card">
                  <UploadSection
                    onRunAnalysis={handleRunAnalysis}
                    isRunning={analysisState === 'running'}
                  />
                </div>

                {/* Right Column: Analysis Methodology */}
                <div className="upload-methodology-card card">
                  <div className="methodology-card-header">
                    <div className="card-title-group">
                      <BookOpen size={18} color="#38bdf8" />
                      <div>
                        <h3 className="card-heading font-sans">ANALYSIS METHODOLOGY</h3>
                        <p className="card-subheading font-mono">From raw satellite data to actionable disaster intelligence</p>
                      </div>
                    </div>
                  </div>

                  <div className="methodology-steps-list">
                    <div className="method-step-item">
                      <div className="step-badge-num font-mono">01</div>
                      <div className="step-details">
                        <h4 className="font-sans">Georeferenced Raster Alignment</h4>
                        <p className="font-sans">Validates EPSG coordinate reference systems, pixel affine matrices, and bounding overlap between pre-event and post-event satellite scenes.</p>
                      </div>
                    </div>

                    <div className="method-step-item">
                      <div className="step-badge-num font-mono">02</div>
                      <div className="step-details">
                        <h4 className="font-sans">Adaptive Water Inundation Detection</h4>
                        <p className="font-sans">Computes multi-band NDWI = (Green - NIR)/(Green + NIR) or adaptive Otsu histogram thresholding on single-band differences.</p>
                      </div>
                    </div>

                    <div className="method-step-item">
                      <div className="step-badge-num font-mono">03</div>
                      <div className="step-details">
                        <h4 className="font-sans">Vector Polygon Simplification</h4>
                        <p className="font-sans">Extracts raster pixel contours using <code>rasterio.features.shapes</code>, buffers geometry artifacts, and simplifies vertices to 0.0001° tolerance.</p>
                      </div>
                    </div>

                    <div className="method-step-item">
                      <div className="step-badge-num font-mono">04</div>
                      <div className="step-details">
                        <h4 className="font-sans">Spatial Overlay & Vulnerability Prioritization</h4>
                        <p className="font-sans">Intersects inundation vectors with local village boundaries, road networks, and screening candidate evacuation sites outside 100m buffer zones.</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 5: AI ASSISTANT */}
          {activeTab === 'ai' && (
            <div className="ai-view-container">
              <div className="ai-chat-full-panel">
                <AiAssistant sessionId={sessionId} pipelineResult={pipelineResult} />
              </div>
            </div>
          )}
        </main>
      </div>

      <StatusIndicator state={analysisState} error={error} />
    </div>
  );
}
