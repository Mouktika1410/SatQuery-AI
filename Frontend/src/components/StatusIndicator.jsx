import React from 'react';

const STEPS = ['Validate', 'Detect', 'Polygonize', 'Impact', 'Evacuation'];

const STATE_STEP_MAP = {
  running: 0,
  complete: 5,
  error: -1,
  idle: -1,
};

const STATUS_TEXT = {
  idle: 'Upload two georeferenced GeoTIFF images to begin analysis.',
  running: 'Running flood analysis pipeline…',
  complete: 'Analysis complete. Results shown on map and panels.',
  error: 'Analysis failed.',
};

export default function StatusIndicator({ state, error }) {
  const currentStep = STATE_STEP_MAP[state] ?? -1;

  return (
    <div className="status-bar">
      <div className={`status-dot ${state}`} />
      <span>
        {state === 'error' && error
          ? `Error: ${error}`
          : STATUS_TEXT[state] || state}
      </span>

      {state === 'running' && (
        <div className="status-steps">
          {STEPS.map((step, i) => (
            <span
              key={step}
              className={`step-badge ${
                i < currentStep ? 'done' : i === currentStep ? 'active' : ''
              }`}
            >
              {i < currentStep ? '✓ ' : ''}{step}
            </span>
          ))}
        </div>
      )}

      {state === 'complete' && (
        <div className="status-steps">
          {STEPS.map((step) => (
            <span key={step} className="step-badge done">✓ {step}</span>
          ))}
        </div>
      )}
    </div>
  );
}
