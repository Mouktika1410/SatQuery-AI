import React, { useState, useRef } from 'react';

const METHODS = [
  { value: 'auto', label: 'Auto (recommended)' },
  { value: 'differencing', label: 'Differencing + Otsu' },
  { value: 'ndwi', label: 'NDWI (optical multi-band)' },
];

function FileDropZone({ label, file, onChange, id }) {
  const inputRef = useRef(null);

  const handleClick = () => inputRef.current?.click();
  const handleDrop = (e) => {
    e.preventDefault();
    const dropped = e.dataTransfer.files[0];
    if (dropped) onChange(dropped);
  };

  const formatSize = (bytes) => {
    if (!bytes) return '';
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div>
      <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginBottom: 5 }}>
        {label}
      </div>
      <div
        className={`file-upload-box ${file ? 'has-file' : ''}`}
        onClick={handleClick}
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
        tabIndex={0}
        onKeyDown={(e) => e.key === 'Enter' && handleClick()}
        role="button"
        aria-label={`Upload ${label}`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".tif,.tiff"
          onChange={(e) => e.target.files[0] && onChange(e.target.files[0])}
          style={{ display: 'none' }}
          id={id}
        />
        {file ? (
          <>
            <span className="upload-icon">✅</span>
            <div className="file-upload-name">{file.name}</div>
            <div className="file-upload-size">{formatSize(file.size)}</div>
          </>
        ) : (
          <>
            <span className="upload-icon">📁</span>
            <div className="file-upload-label">Click or drag GeoTIFF here</div>
            <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: 3 }}>
              .tif / .tiff · Georeferenced required
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default function UploadSection({ onRunAnalysis, isRunning }) {
  const [preFile, setPreFile] = useState(null);
  const [postFile, setPostFile] = useState(null);
  const [showOptions, setShowOptions] = useState(false);
  const [method, setMethod] = useState('auto');
  const [morphIters, setMorphIters] = useState(2);
  const [simplifyTol, setSimplifyTol] = useState('0.0001');

  const canRun = preFile && postFile && !isRunning;

  const handleRun = () => {
    if (!canRun) return;
    onRunAnalysis(preFile, postFile, {
      method,
      morphologyIterations: morphIters,
      simplifyTolerance: simplifyTol,
      bufferM: 100.0,
    });
  };

  return (
    <div className="card">
      <div className="card-title">
        🖼️ Image Upload
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <FileDropZone
          label="Pre-Flood Image (Baseline)"
          file={preFile}
          onChange={setPreFile}
          id="pre-upload"
        />
        <FileDropZone
          label="Post-Flood Image (Event)"
          file={postFile}
          onChange={setPostFile}
          id="post-upload"
        />
      </div>

      {/* Options toggle */}
      <button className="options-toggle" onClick={() => setShowOptions((v) => !v)}>
        <span>Detection Options</span>
        <span>{showOptions ? '▲' : '▼'}</span>
      </button>

      {showOptions && (
        <div className="options-body">
          <div className="form-group">
            <label>Detection Method</label>
            <select value={method} onChange={(e) => setMethod(e.target.value)}>
              {METHODS.map((m) => (
                <option key={m.value} value={m.value}>{m.label}</option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label>Morphology Cleanup Iterations: {morphIters}</label>
            <div className="range-row">
              <input
                type="range"
                min={0}
                max={5}
                value={morphIters}
                onChange={(e) => setMorphIters(Number(e.target.value))}
              />
              <span className="range-val">{morphIters}</span>
            </div>
          </div>

          <div className="form-group">
            <label>Polygon Simplification Tolerance</label>
            <input
              type="number"
              step="0.00001"
              min="0"
              value={simplifyTol}
              onChange={(e) => setSimplifyTol(e.target.value)}
            />
          </div>
        </div>
      )}

      <div style={{ marginTop: 12 }}>
        <button
          className="btn-primary"
          onClick={handleRun}
          disabled={!canRun}
        >
          {isRunning ? (
            <>⏳ Running Analysis…</>
          ) : (
            <>🚀 Run Flood Analysis</>
          )}
        </button>

        {(!preFile || !postFile) && (
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textAlign: 'center', marginTop: 6 }}>
            Upload both images to enable analysis
          </div>
        )}
      </div>
    </div>
  );
}
