import React, { useState } from 'react';
import { Upload, FileCheck, AlertTriangle, Layers, ArrowRight, Compass } from 'lucide-react';

export default function ImageStudyUpload({ onRunImageStudy, isRunning }) {
  const [preFile, setPreFile] = useState(null);
  const [postFile, setPostFile] = useState(null);
  const [validationError, setValidationError] = useState(null);

  const validateFile = (file) => {
    if (!file) return false;
    const name = file.name.toLowerCase();
    if (!name.endsWith('.tif') && !name.endsWith('.tiff')) {
      setValidationError(
        `File "${file.name}" is not a GeoTIFF raster. Non-georeferenced format images (JPG, PNG) are not supported. Please select valid georeferenced GeoTIFF (.tif / .tiff) files.`
      );
      return false;
    }
    setValidationError(null);
    return true;
  };

  const handlePreChange = (e) => {
    const f = e.target.files?.[0];
    if (f && validateFile(f)) {
      setPreFile(f);
    }
  };

  const handlePostChange = (e) => {
    const f = e.target.files?.[0];
    if (f && validateFile(f)) {
      setPostFile(f);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!preFile || !postFile) {
      setValidationError('Please upload both Before-Flood and After-Flood GeoTIFF rasters.');
      return;
    }
    onRunImageStudy(preFile, postFile);
  };

  return (
    <div className="image-study-upload-card card">
      <div className="card-title-group" style={{ marginBottom: 16 }}>
        <Compass size={22} color="#38bdf8" />
        <div>
          <h2 className="card-heading font-sans" style={{ fontSize: '1.25rem' }}>FLOOD IMAGE STUDY</h2>
          <p className="card-subheading font-mono">Upload dual georeferenced satellite GeoTIFF rasters for change detection & centroid mapping</p>
        </div>
      </div>

      {validationError && (
        <div className="alert-box-error" style={{ marginBottom: 16, display: 'flex', alignItems: 'flex-start', gap: 8 }}>
          <AlertTriangle size={18} color="#ef4444" style={{ flexShrink: 0, marginTop: 2 }} />
          <div>
            <strong>Geospatial Format Error:</strong>
            <p style={{ margin: '4px 0 0 0', fontSize: '0.85rem' }}>{validationError}</p>
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
        <div className="upload-dropzone-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          {/* Before-Flood GeoTIFF Upload */}
          <div className={`dropzone-box ${preFile ? 'has-file' : ''}`}>
            <label className="dropzone-label">
              <input
                type="file"
                accept=".tif,.tiff"
                onChange={handlePreChange}
                disabled={isRunning}
                style={{ display: 'none' }}
              />
              <div className="dropzone-content">
                {preFile ? (
                  <>
                    <FileCheck size={36} color="#10b981" />
                    <span className="file-name">{preFile.name}</span>
                    <span className="file-size font-mono">{(preFile.size / 1024 / 1024).toFixed(2)} MB • GeoTIFF</span>
                  </>
                ) : (
                  <>
                    <Upload size={36} color="#38bdf8" />
                    <span className="drop-title">BEFORE FLOOD IMAGE</span>
                    <span className="drop-sub font-mono">Click or drop .tif / .tiff baseline raster</span>
                  </>
                )}
              </div>
            </label>
          </div>

          {/* After-Flood GeoTIFF Upload */}
          <div className={`dropzone-box ${postFile ? 'has-file' : ''}`}>
            <label className="dropzone-label">
              <input
                type="file"
                accept=".tif,.tiff"
                onChange={handlePostChange}
                disabled={isRunning}
                style={{ display: 'none' }}
              />
              <div className="dropzone-content">
                {postFile ? (
                  <>
                    <FileCheck size={36} color="#10b981" />
                    <span className="file-name">{postFile.name}</span>
                    <span className="file-size font-mono">{(postFile.size / 1024 / 1024).toFixed(2)} MB • GeoTIFF</span>
                  </>
                ) : (
                  <>
                    <Upload size={36} color="#38bdf8" />
                    <span className="drop-title">AFTER/DURING FLOOD IMAGE</span>
                    <span className="drop-sub font-mono">Click or drop .tif / .tiff event raster</span>
                  </>
                )}
              </div>
            </label>
          </div>
        </div>

        <div className="upload-requirements-bar" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', background: 'var(--bg-card-secondary)', borderRadius: 8 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
            <Layers size={15} color="#38bdf8" />
            <span>Requirements: <b>GeoTIFF (.tif/.tiff)</b> with valid CRS & Affine Transform. JPG/PNG without geospatial metadata are rejected.</span>
          </div>

          <button
            type="submit"
            className="btn-primary"
            disabled={!preFile || !postFile || isRunning}
            style={{ display: 'inline-flex', alignItems: 'center', gap: 8, width: 'auto', padding: '10px 24px' }}
          >
            {isRunning ? (
              <span>Running Analysis...</span>
            ) : (
              <>
                <span>Flood Analysis</span>
                <ArrowRight size={16} />
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
