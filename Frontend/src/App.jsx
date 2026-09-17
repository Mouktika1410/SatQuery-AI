import React, { useState, useCallback } from 'react';
import Header from './components/Header';
import UploadSection from './components/UploadSection';
import StatusIndicator from './components/StatusIndicator';
import MetricsPanel from './components/MetricsPanel';
import MapViewer from './components/MapViewer';
import AiAssistant from './components/AiAssistant';
import { runFullPipeline } from './services/api';

export default function App() {
  const [analysisState, setAnalysisState] = useState('idle');
  const [sessionId, setSessionId] = useState(null);
  const [pipelineResult, setPipelineResult] = useState(null);
  const [error, setError] = useState(null);

  const handleRunAnalysis = useCallback(async (preFile, postFile, options) => {
    setAnalysisState('running');
    setError(null);
    setPipelineResult(null);
    setSessionId(null);

    try {
      const result = await runFullPipeline(preFile, postFile, options);
      setPipelineResult(result);
      setSessionId(result.session_id);
      setAnalysisState('complete');
    } catch (err) {
      const msg = err.message || 'Analysis failed. Check the backend is running.';
      setError(msg);
      setAnalysisState('error');
    }
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

  return (
    <div className="app">
      <Header status={analysisState} />

      <div className="app-body">
        {/* Left Panel: Upload + Metrics */}
        <div className="left-panel">
          <UploadSection
            onRunAnalysis={handleRunAnalysis}
            isRunning={analysisState === 'running'}
          />
          {pipelineResult && <MetricsPanel result={pipelineResult} />}
        </div>

        {/* Center: Map */}
        <div className="main-panel">
          <MapViewer
            floodGeoJSON={floodGeoJSON}
            floodMetrics={floodMetrics}
            evacuationCandidates={evacuationCandidates}
            affectedVillages={affectedVillages}
            affectedVillagesGeoJSON={affectedVillagesGeoJSON}
            affectedRoadsGeoJSON={affectedRoadsGeoJSON}
          />
        </div>

        {/* Right Panel: AI Assistant */}
        <div className="right-panel">
          <AiAssistant sessionId={sessionId} pipelineResult={pipelineResult} />
        </div>
      </div>

      <StatusIndicator state={analysisState} error={error} />
    </div>
  );
}
