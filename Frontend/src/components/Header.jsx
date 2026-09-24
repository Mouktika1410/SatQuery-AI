import React from 'react';
import { Satellite, Upload, BookOpen } from 'lucide-react';

const STATUS_LABELS = {
  idle: 'Ready',
  running: 'Analysing…',
  complete: 'Analysis Complete',
  error: 'Error',
};

const TAB_TITLES = {
  map: 'Map Explorer',
  impact: 'Impact & Vulnerability Analysis',
  evacuation: 'Evacuation Site Screening',
  upload: 'Data Ingestion & Methodology',
  ai: 'AI Contextual Assistant',
};

export default function Header({ status = 'idle', activeTab = 'map', onNavigate, onGoHome, onOpenGuide, hasData }) {
  return (
    <header className="header">
      <div className="header-left">
        <button className="header-logo-btn" onClick={onGoHome} title="Go to Landing Page">
          <Satellite className="header-logo-icon" size={22} color="#38bdf8" />
          <div>
            <div className="header-logo-text">SatQuery</div>
            <div className="header-subtitle">Spatial Flood Intelligence</div>
          </div>
        </button>

        <div className="header-divider" />

        <div className="header-breadcrumb">
          <span className="breadcrumb-category">Workspace</span>
          <span className="breadcrumb-slash">/</span>
          <span className="breadcrumb-current">{TAB_TITLES[activeTab] || 'Map Explorer'}</span>
        </div>
      </div>

      <div className="header-right">
        {onOpenGuide && (
          <button
            className="header-cta-guide"
            onClick={onOpenGuide}
            title="Open SatQuery User Guide"
          >
            <BookOpen size={14} style={{ marginRight: 6 }} />
            User Guide
          </button>
        )}

        {onNavigate && (
          <button
            className="header-cta-upload"
            onClick={() => onNavigate('upload')}
          >
            <Upload size={14} style={{ marginRight: 6 }} />
            Upload Data
          </button>
        )}

        <span className={`header-status-badge ${status}`}>
          <span className="status-badge-dot" />
          {STATUS_LABELS[status] || status}
        </span>
      </div>
    </header>
  );
}
