import React, { useState } from 'react';
import {
  Satellite,
  Map,
  ArrowRight,
  Sparkles,
  Radio,
  Layers,
  Activity,
  ShieldAlert,
  Brain,
  X,
  ChevronRight,
  Crosshair,
  Scan,
  Focus
} from 'lucide-react';

export default function LandingPage({ onGetStarted, hasAnalysisData }) {
  const [showDemoModal, setShowDemoModal] = useState(false);

  return (
    <div className="landing-page">
      {/* 1. Dark Backdrop & Grid Overlay */}
      <div className="landing-space-backdrop" />
      <div className="landing-orbital-grid" />

      {/* 2. Realistic Satellite Earth Observation Hero Visual (Right Side Fill) */}
      <div className="landing-satellite-hero-visual">
        {/* Dark Multi-Stop Gradient Blend Mask */}
        <div className="satellite-blend-gradient" />

        {/* Real High-Resolution Earth-Observation Satellite Image with Flood Inundation Extent */}
        <img
          src="/satellite-flood-hero.jpg"
          alt="SatQuery Earth Observation Satellite Flood Extent"
          className="satellite-hero-img"
        />
      </div>

      {/* 3. Top Header Bar */}
      <header className="cinematic-header">
        <div className="header-brand-group">
          <div className="brand-logo-icon">
            <Satellite size={24} color="#38bdf8" />
          </div>
          <div className="brand-text-block">
            <div className="brand-title font-sans">
              SAT<span className="brand-accent">QUERY</span>
            </div>
            <span className="brand-subtitle font-mono">SPATIAL DISASTER & FLOOD INTELLIGENCE</span>
          </div>
        </div>

        <div className="header-action-group font-sans">
          <button className="btn-header-demo" onClick={() => setShowDemoModal(true)}>
            <Sparkles size={14} color="#f59e0b" style={{ marginRight: 6 }} />
            <span>Interactive Walkthrough</span>
          </button>

          <button className="btn-header-platform" onClick={() => onGetStarted(hasAnalysisData ? 'map' : 'upload')}>
            <span>{hasAnalysisData ? 'Open Platform' : 'Launch Workspace'}</span>
            <ChevronRight size={15} style={{ marginLeft: 4 }} />
          </button>
        </div>
      </header>

      {/* 4. Main Hero Left-Aligned Content Section */}
      <main className="cinematic-hero-overlay">
        <div className="hero-content-column">
          {/* Eyebrow Label */}
          <div className="hero-eyebrow font-mono">
            <span className="eyebrow-line" />
            <span>GEOSPATIAL FLOOD SURVEILLANCE</span>
          </div>

          {/* Headline */}
          <h1 className="hero-title font-sans">
            See the Flood.<br />
            Understand the<br />
            <span className="hero-highlight-orange">Risk.</span>
          </h1>

          {/* Subtitle Tagline */}
          <p className="hero-description font-sans">
            Satellite-driven observations for detecting inundation extent, population exposure, and critical infrastructure risk across disaster-affected regions.
          </p>

          {/* Primary Action Button Row (Clean, Professional & No Video Button) */}
          <div className="hero-actions-primary-row">
            <button
              className="btn-hero-explore"
              onClick={() => onGetStarted(hasAnalysisData ? 'map' : 'upload')}
            >
              <span>{hasAnalysisData ? 'Explore SATQUERY Map' : 'Explore SATQUERY'}</span>
              <ArrowRight size={17} className="btn-icon-arrow" />
            </button>

            <button className="btn-hero-demo" onClick={() => setShowDemoModal(true)}>
              <Sparkles size={15} color="#fef3c7" style={{ marginRight: 8 }} />
              <span>System Walkthrough (Demo)</span>
            </button>
          </div>
        </div>
      </main>

      {/* 5. Bottom Telemetry Ticker Footer */}
      <footer className="cinematic-telemetry-footer font-mono">
        <div className="telemetry-item">
          <Radio size={14} color="#38bdf8" className="telemetry-icon" />
          <div className="telemetry-text">
            <span className="lbl">SATELLITE OBSERVATIONS</span>
            <span className="val">SENTINEL-1 SAR / SENTINEL-2 OPTICAL</span>
          </div>
        </div>

        <div className="telemetry-divider">|</div>

        <div className="telemetry-item">
          <Layers size={14} color="#38bdf8" className="telemetry-icon" />
          <div className="telemetry-text">
            <span className="lbl">HYDROLOGIC CONTEXT</span>
            <span className="val">NDWI + OTSU RELATIVE THRESHOLD</span>
          </div>
        </div>

        <div className="telemetry-divider">|</div>

        <div className="telemetry-item">
          <Activity size={14} color="#38bdf8" className="telemetry-icon" />
          <div className="telemetry-text">
            <span className="lbl">SPATIAL ANALYTICS</span>
            <span className="val">EPSG:4326 GEOJSON VECTORS</span>
          </div>
        </div>

        <div className="telemetry-divider">|</div>

        <div className="telemetry-item">
          <ShieldAlert size={14} color="#f59e0b" className="telemetry-icon" />
          <div className="telemetry-text">
            <span className="lbl">IMPACT INSIGHTS</span>
            <span className="val">POPULATION & ROAD EXPOSURE</span>
          </div>
        </div>

        <div className="telemetry-divider">|</div>

        <div className="telemetry-item">
          <Brain size={14} color="#10b981" className="telemetry-icon" />
          <div className="telemetry-text">
            <span className="lbl">AI ASSISTANT</span>
            <span className="val">GROUNDED DECISION SUPPORT</span>
          </div>
        </div>
      </footer>

      {/* 6. System Walkthrough Modal */}
      {showDemoModal && (
        <div className="cinematic-modal-overlay" onClick={() => setShowDemoModal(false)}>
          <div className="cinematic-modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title-group">
                <Sparkles size={18} color="#f59e0b" />
                <span>SatQuery Operational System Walkthrough</span>
              </div>
              <button className="modal-close-btn" onClick={() => setShowDemoModal(false)}>
                <X size={16} />
              </button>
            </div>

            <div className="modal-body">
              <p className="modal-intro">
                SatQuery provides a deterministic geospatial processing pipeline for emergency responders, spatial analysts, and disaster management teams.
              </p>

              <div className="walkthrough-grid font-sans">
                <div className="walkthrough-card">
                  <div className="step-badge">STEP 01</div>
                  <h4>Dual-Temporal Scene Validation</h4>
                  <p>Validates coordinate reference systems (CRS), affine transformation matrices, and bounding overlap between pre-event and post-event Sentinel scenes.</p>
                </div>

                <div className="walkthrough-card">
                  <div className="step-badge">STEP 02</div>
                  <h4>Deterministic Inundation Masking</h4>
                  <p>Computes multi-band NDWI spectral change or adaptive single-band Otsu thresholding to extract flooded pixels without manual tuning.</p>
                </div>

                <div className="walkthrough-card">
                  <div className="step-badge">STEP 03</div>
                  <h4>Polygon Vectorization & GIS Overlay</h4>
                  <p>Converts raster flood masks to topology-preserving GeoJSON vectors and intersects them with local village boundaries, road networks, and population grids.</p>
                </div>

                <div className="walkthrough-card">
                  <div className="step-badge">STEP 04</div>
                  <h4>Safe Evacuation Screening & Grounded AI</h4>
                  <p>Screens candidate evacuation facilities outside the inundation zone and powers a grounded LLM assistant strictly tied to computed metrics.</p>
                </div>
              </div>
            </div>

            <div className="modal-footer">
              <button className="btn-ghost-sm" onClick={() => setShowDemoModal(false)}>
                Close Walkthrough
              </button>
              <button
                className="btn-primary-sm"
                onClick={() => {
                  setShowDemoModal(false);
                  onGetStarted(hasAnalysisData ? 'map' : 'upload');
                }}
              >
                <span>Launch Interactive Workspace</span>
                <ArrowRight size={14} style={{ marginLeft: 6 }} />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
