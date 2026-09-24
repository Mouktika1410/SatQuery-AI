import React, { useState, useRef, useEffect } from 'react';
import { Database, UploadCloud, CheckCircle2, ChevronDown, ChevronUp, RefreshCw, Play, Sliders, Sparkles, X } from 'lucide-react';

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
  const [loadingSample, setLoadingSample] = useState(false);
  const sampleFileName = isEvent ? 'kerala_after_flood.tif' : 'kerala_before_flood.tif';

  const handleClick = () => inputRef.current?.click();
  const handleDrop = (e) => {
    e.preventDefault();
    const dropped = e.dataTransfer.files[0];
    if (dropped) onChange(dropped);
  };

  const handleUseSample = async (e) => {
    e.stopPropagation();
    setLoadingSample(true);
    try {
      let res = await fetch(`/samples/${sampleFileName}`);
      if (!res.ok) {
        res = await fetch(`/api/v1/flood/sample/${sampleFileName}`);
      }
      if (!res.ok) {
        throw new Error(`Failed to load ${sampleFileName}`);
      }
      const blob = await res.blob();
      const sampleFile = new File([blob], sampleFileName, { type: 'image/tiff' });
      onChange(sampleFile);
    } catch (err) {
      console.error(`Failed to load sample image ${sampleFileName}:`, err);
    } finally {
      setLoadingSample(false);
    }
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
              <div className="file-selected-actions" onClick={(e) => e.stopPropagation()}>
                <button
                  type="button"
                  className="btn-change-file font-mono"
                  onClick={() => onChange(null)}
                  title="Remove and select another file"
                >
                  Change File
                </button>
              </div>
            </div>
          ) : (
            <div className="file-prompt-container">
              <div className="file-prompt-info">
                <UploadCloud size={24} color="#38bdf8" className="upload-cloud-icon" />
                <div className="file-upload-label font-sans">Click or drag GeoTIFF here</div>
                <div className="file-upload-subtext font-mono">
                  .tif / .tiff - Georeferenced required
                </div>
              </div>

              <div className="sample-data-divider-row font-mono">
                <span className="sample-divider-line" />
                <span className="sample-divider-text">or use Sample Data</span>
                <span className="sample-divider-line" />
              </div>

              <button
                type="button"
                className="btn-use-sample-inside font-sans"
                onClick={handleUseSample}
                disabled={loadingSample}
                title={`Load ${sampleFileName}`}
              >
                <Sparkles size={13} color="#f59e0b" style={{ marginRight: 6 }} />
                <span>{loadingSample ? 'Loading Sample…' : 'Use Kerala Sample'}</span>
              </button>
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
  const [loadingBoth, setLoadingBoth] = useState(false);

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

  const handleLoadBothSamples = async () => {
    setLoadingBoth(true);
    try {
      const fetchFile = async (name) => {
        let r = await fetch(`/samples/${name}`);
        if (!r.ok) r = await fetch(`/api/v1/flood/sample/${name}`);
        const blob = await r.blob();
        return new File([blob], name, { type: 'image/tiff' });
      };

      const [fPre, fPost] = await Promise.all([
        fetchFile('kerala_before_flood.tif'),
        fetchFile('kerala_after_flood.tif'),
      ]);

      setPreFile(fPre);
      setPostFile(fPost);
    } catch (err) {
      console.error('Failed to load sample dataset:', err);
    } finally {
      setLoadingBoth(false);
    }
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
            <h3 className="ingestion-card-title font-sans">IMAGE INGESTION &amp; ANALYSIS</h3>
            <p className="ingestion-card-subtitle font-mono">Upload pre- and post-flood satellite imagery or load verified Kerala sample data</p>
          </div>
        </div>

        <div className="ingestion-quick-actions">
          <button
            type="button"
            className="btn-quick-sample-load font-sans"
            onClick={handleLoadBothSamples}
            disabled={loadingBoth || isRunning}
            title="Load both pre-flood and post-flood Kerala Sentinel test images"
          >
            <Sparkles size={14} color="#f59e0b" style={{ marginRight: 6 }} />
            <span>{loadingBoth ? 'Loading Samples…' : 'Load Both Kerala Samples'}</span>
          </button>
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
            Upload both images or click "Use Kerala Sample" to enable analysis.
          </div>
        )}
      </div>
    </div>
  );
}
