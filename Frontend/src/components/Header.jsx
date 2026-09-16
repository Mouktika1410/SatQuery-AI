import React from 'react';

const STATUS_LABELS = {
  idle: 'Ready',
  running: 'Analysing…',
  complete: 'Analysis Complete',
  error: 'Error',
};

export default function Header({ status = 'idle' }) {
  return (
    <header className="header">
      <div className="header-logo">
        <span className="header-logo-icon">🛰️</span>
        <div>
          <div className="header-logo-text">SatQuery</div>
          <div className="header-subtitle">AI-Powered Flood Analysis Assistant</div>
        </div>
      </div>

      <div className="header-divider" />

      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
        Phase 1 Prototype · Deterministic GIS
      </span>

      <span className={`header-status-badge ${status}`}>
        {STATUS_LABELS[status] || status}
      </span>
    </header>
  );
}
