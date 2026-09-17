import React from 'react';
import { Satellite, Map, ArrowRight } from 'lucide-react';

export default function LandingPage({ onGetStarted, hasAnalysisData }) {
  return (
    <div className="landing-page">
      {/* Full-screen Earth/Satellite Observation Background */}
      <div className="landing-earth-bg" />
      <div className="landing-orbital-grid" />
      <div className="landing-scan-reticle" />

      {/* Top Header / Branding Bar */}
      <header className="landing-header">
        <div className="landing-brand">
          <Satellite size={26} color="#38bdf8" className="brand-icon" />
          <span className="brand-name">SatQuery</span>
          <span className="brand-tag font-mono">REMOTE SENSING V1.0</span>
        </div>
        {hasAnalysisData && (
          <button className="landing-quick-btn" onClick={() => onGetStarted('map')}>
            <Map size={15} style={{ marginRight: 6 }} />
            Open Active Map
          </button>
        )}
      </header>

      {/* Main Hero Content */}
      <main className="landing-hero-center">
        <div className="hero-status-pill">
          <span className="pulse-dot-green" />
          <span>AUTONOMOUS HYDRO-SPATIAL INTELLIGENCE</span>
        </div>

        <h1 className="hero-heading">
          Satellite Flood Analysis & <br />
          <span className="hero-cyan-glow">Spatial Impact Engine</span>
        </h1>

        <p className="hero-tagline">
          Rapid dual-temporal inundation detection, GIS boundary extraction, and grounded vulnerability scoring.
        </p>

        <div className="hero-single-action">
          <button
            className="btn-operational-start"
            onClick={() => onGetStarted(hasAnalysisData ? 'map' : 'upload')}
          >
            <span>{hasAnalysisData ? 'Open Map Explorer' : 'Get Started — Launch Pipeline'}</span>
            <ArrowRight size={18} className="btn-arrow" />
          </button>
        </div>

        {/* Minimal Operational Status Ticker */}
        <div className="hero-hud-footer font-mono">
          <div className="hud-metric">
            <span className="hud-lbl">SENSOR:</span>
            <span className="hud-val">GeoTIFF Multi-Band / Optical</span>
          </div>
          <span className="hud-divider">|</span>
          <div className="hud-metric">
            <span className="hud-lbl">METHOD:</span>
            <span className="hud-val">NDWI + Otsu Relative Threshold</span>
          </div>
          <span className="hud-divider">|</span>
          <div className="hud-metric">
            <span className="hud-lbl">DATUM:</span>
            <span className="hud-val">EPSG:4326 GeoJSON Vectors</span>
          </div>
        </div>
      </main>
    </div>
  );
}
