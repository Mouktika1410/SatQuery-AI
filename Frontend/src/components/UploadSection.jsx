import React, { useState, useRef, useEffect } from 'react';
import { Database, UploadCloud, CheckCircle2, ChevronDown, ChevronUp, RefreshCw, Play, Sliders } from 'lucide-react';

const METHODS = [
  { value: 'auto', label: 'Auto (Recommended - Multi-Band NDWI / Otsu)' },
  { value: 'differencing', label: 'Differencing + Otsu (Single Band)' },
  { value: 'ndwi', label: 'NDWI (Green & NIR Multi-Band Optical)' },
];

function BaselineSatThumb() {
  return (
    <div className="sat-thumb-container">
      <img
        src="/pre-flood-thumb.jpg"
        alt="Pre-Flood Satellite Baseline Observation"
        className="sat-thumb-img"
      />
    </div>
  );
}

function EventSatThumb() {
  return (
    <div className="sat-thumb-container">
      <img
        src="/post-flood-thumb.jpg"
        alt="Post-Flood Satellite Event Inundation"
        className="sat-thumb-img"
      />
    </div>
  );
}

function FileDropZone({ label, file, onChange, id, isEvent }) {
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
    <div className="ingestion-dropzone-box">
      <div className="dropzone-header-title font-sans">
        {label}
      </div>

      <div className="dropzone-card-content">
        {/* Left Side Satellite Thumbnail Preview */}
        {isEvent ? <EventSatThumb /> : <BaselineSatThumb />}

        {/* Right Side Dashed Drag and Drop Container */}
        <div
          className={`file-upload-box-enhanced ${file ? 'has-file' : ''}`}
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
            <div className="file-selected-info">
              <CheckCircle2 size={24} color="#10b981" />
              <div className="file-upload-name font-mono">{file.name}</div>
              <div className="file-upload-size font-mono">{formatSize(file.size)}</div>
            </div>
          ) : (
            <div className="file-prompt-info">
              <UploadCloud size={24} color="#38bdf8" className="upload-cloud-icon" />
              <div className="file-upload-label font-sans">Click or drag GeoTIFF here</div>
              <div className="file-upload-subtext font-mono">
                .tif / .tiff - Georeferenced required
              </div>
            </div>
          )}
        </div>
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
    <div className="ingestion-section-wrapper">
      {/* Section Header */}
      <div className="ingestion-header-row">
        <div className="ingestion-title-block">
          <div className="title-icon-box">
            <Database size={20} color="#38bdf8" />
          </div>
          <div>
            <h3 className="ingestion-card-title font-sans">IMAGE INGESTION & ANALYSIS</h3>
            <p className="ingestion-card-subtitle font-mono">Upload pre- and post-flood satellite imagery to run the analysis</p>
          </div>
        </div>
      </div>

      {/* Pre/Post Sub-Panel Containers Grid */}
      <div className="ingestion-dropzones-grid">
        <FileDropZone
          label="Pre-Flood Image (Baseline)"
          file={preFile}
          onChange={setPreFile}
          id="pre-upload"
          isEvent={false}
        />
        <FileDropZone
          label="Post-Flood Image (Event)"
          file={postFile}
          onChange={setPostFile}
          id="post-upload"
          isEvent={true}
        />
      </div>

      {/* Detection Options Accordion Header Bar */}
      <div className="detection-options-container">
        <button className="options-toggle-btn" onClick={() => setShowOptions((v) => !v)}>
          <div className="toggle-left">
            <Sliders size={15} color="#38bdf8" />
            <span className="font-sans">Detection Options</span>
          </div>
          {showOptions ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
        </button>

        {showOptions && (
          <div className="options-body-grid">
            <div className="form-group">
              <label className="font-mono">Detection Method</label>
              <select value={method} onChange={(e) => setMethod(e.target.value)} className="font-sans">
                {METHODS.map((m) => (
                  <option key={m.value} value={m.value}>{m.label}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label className="font-mono">Morphology Cleanup Iterations: {morphIters}</label>
              <div className="range-row">
                <input
                  type="range"
                  min={0}
                  max={5}
                  value={morphIters}
                  onChange={(e) => setMorphIters(Number(e.target.value))}
                />
                <span className="range-val font-mono">{morphIters}</span>
              </div>
            </div>

            <div className="form-group">
              <label className="font-mono">Polygon Simplification Tolerance</label>
              <input
                type="number"
                step="0.00001"
                min="0"
                value={simplifyTol}
                onChange={(e) => setSimplifyTol(e.target.value)}
                className="font-mono"
              />
            </div>
          </div>
        )}
      </div>

      {/* Primary Action Button */}
      <div className="ingestion-action-footer">
        <button
          className="btn-primary-ingestion"
          onClick={handleRun}
          disabled={!canRun}
        >
          {isRunning ? (
            <>
              <RefreshCw size={16} className="spin-icon" />
              <span>Running Flood Analysis…</span>
            </>
          ) : (
            <>
              <Play size={16} />
              <span>Run Flood Analysis</span>
            </>
          )}
        </button>

        {(!preFile || !postFile) && (
          <div className="ingestion-disabled-hint font-mono">
            Upload both images to enable analysis.
          </div>
        )}
      </div>
    </div>
  );
}


