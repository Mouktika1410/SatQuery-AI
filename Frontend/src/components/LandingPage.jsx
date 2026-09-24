import React, { useState, useRef, useEffect } from 'react';
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
  Focus,
  Play,
  Pause,
  Volume2,
  VolumeX,
  Maximize2,
  Minimize2,
  BookOpen,
} from 'lucide-react';

export default function LandingPage({ onGetStarted, hasAnalysisData, onOpenGuide }) {
  const [showDemoModal, setShowDemoModal] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);

  const videoRef = useRef(null);
  const playerContainerRef = useRef(null);

  const formatTime = (secs) => {
    if (!secs || isNaN(secs)) return '0:00';
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  const togglePlay = () => {
    if (!videoRef.current) return;
    if (videoRef.current.paused) {
      videoRef.current.play().catch(() => {});
    } else {
      videoRef.current.pause();
    }
  };

  const handleSeek = (e) => {
    const newTime = parseFloat(e.target.value);
    setCurrentTime(newTime);
    if (videoRef.current) {
      videoRef.current.currentTime = newTime;
    }
  };

  const handleVolumeChange = (e) => {
    const newVol = parseFloat(e.target.value);
    setVolume(newVol);
    if (videoRef.current) {
      videoRef.current.volume = newVol;
      videoRef.current.muted = newVol === 0;
      setIsMuted(newVol === 0);
    }
  };

  const toggleMute = () => {
    if (!videoRef.current) return;
    if (isMuted || volume === 0) {
      videoRef.current.muted = false;
      setIsMuted(false);
      if (volume === 0) {
        setVolume(0.5);
        videoRef.current.volume = 0.5;
      }
    } else {
      videoRef.current.muted = true;
      setIsMuted(true);
    }
  };

  const toggleFullscreen = () => {
    const elem = playerContainerRef.current || videoRef.current;
    if (!elem) return;
    if (!document.fullscreenElement) {
      if (elem.requestFullscreen) {
        elem.requestFullscreen().catch(() => {});
      } else if (elem.webkitRequestFullscreen) {
        elem.webkitRequestFullscreen();
      }
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen().catch(() => {});
      }
    }
  };

  const handleCloseModal = () => {
    if (videoRef.current) {
      try {
        videoRef.current.pause();
      } catch (e) {
        // ignore
      }
    }
    setShowDemoModal(false);
  };

  useEffect(() => {
    const onFsChange = () => {
      setIsFullscreen(Boolean(document.fullscreenElement));
    };
    document.addEventListener('fullscreenchange', onFsChange);
    return () => document.removeEventListener('fullscreenchange', onFsChange);
  }, []);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (!showDemoModal) return;
      if (e.key === 'Escape') {
        handleCloseModal();
      } else if (e.key === ' ' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'BUTTON') {
        e.preventDefault();
        togglePlay();
      } else if ((e.key === 'f' || e.key === 'F') && e.target.tagName !== 'INPUT') {
        e.preventDefault();
        toggleFullscreen();
      } else if ((e.key === 'm' || e.key === 'M') && e.target.tagName !== 'INPUT') {
        e.preventDefault();
        toggleMute();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [showDemoModal, isPlaying, isMuted, volume]);

  useEffect(() => {
    if (showDemoModal && videoRef.current) {
      videoRef.current.play().catch(() => {
        setIsPlaying(false);
      });
    }
  }, [showDemoModal]);

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

          <button className="btn-header-guide" onClick={onOpenGuide} title="Open SatQuery User Guide">
            <BookOpen size={14} color="#38bdf8" style={{ marginRight: 6 }} />
            <span>User Guide</span>
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

      {/* 6. System Walkthrough Video Modal */}
      {showDemoModal && (
        <div className="cinematic-modal-overlay video-modal-overlay" onClick={handleCloseModal}>
          <div className="cinematic-modal-card cinematic-video-modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header video-modal-header">
              <div className="modal-title-group">
                <Sparkles size={18} color="#f59e0b" />
                <span className="font-sans font-bold">SatQuery Operational System Walkthrough</span>
                <span className="video-badge font-mono">DEMO • 1080P HD</span>
              </div>
              <button
                className="modal-close-btn"
                onClick={handleCloseModal}
                title="Close Walkthrough (Esc)"
                aria-label="Close Walkthrough"
              >
                <X size={18} />
              </button>
            </div>

            <div className="video-player-container" ref={playerContainerRef}>
              <video
                ref={videoRef}
                src="/satquery-demo.mp4"
                className="cinematic-video-element"
                playsInline
                preload="auto"
                onClick={togglePlay}
                onPlay={() => setIsPlaying(true)}
                onPause={() => setIsPlaying(false)}
                onTimeUpdate={() => setCurrentTime(videoRef.current ? videoRef.current.currentTime : 0)}
                onLoadedMetadata={() => setDuration(videoRef.current ? videoRef.current.duration : 0)}
                onVolumeChange={() => {
                  if (videoRef.current) {
                    setVolume(videoRef.current.volume);
                    setIsMuted(videoRef.current.muted);
                  }
                }}
                onEnded={() => setIsPlaying(false)}
              >
                Your browser does not support HTML5 video playback.
              </video>

              {/* Large Central Play Overlay when paused */}
              {!isPlaying && (
                <div
                  className="video-big-play-overlay"
                  onClick={togglePlay}
                  role="button"
                  aria-label="Play video"
                  title="Play video"
                >
                  <div className="video-big-play-btn">
                    <Play size={36} color="#ffffff" style={{ marginLeft: 4 }} />
                  </div>
                </div>
              )}
            </div>

            {/* Dedicated Player Control Bar: Play/Pause, Timeline, Volume, Fullscreen */}
            <div className="video-custom-controls" role="toolbar" aria-label="Playback controls">
              <button
                type="button"
                className="video-ctrl-btn"
                onClick={togglePlay}
                aria-label={isPlaying ? 'Pause' : 'Play'}
                title={isPlaying ? 'Pause (Space)' : 'Play (Space)'}
              >
                {isPlaying ? <Pause size={17} /> : <Play size={17} />}
                <span className="ctrl-btn-text">{isPlaying ? 'Pause' : 'Play'}</span>
              </button>

              <div className="video-timeline-group">
                <span className="video-time-display font-mono">{formatTime(currentTime)}</span>
                <input
                  type="range"
                  min="0"
                  max={duration || 100}
                  step="0.1"
                  value={currentTime}
                  onChange={handleSeek}
                  className="video-seek-slider"
                  aria-label="Video seek position"
                  title="Seek position"
                />
                <span className="video-time-display font-mono">{formatTime(duration)}</span>
              </div>

              <div className="video-volume-group">
                <button
                  type="button"
                  className="video-ctrl-btn video-mute-btn"
                  onClick={toggleMute}
                  aria-label={isMuted || volume === 0 ? 'Unmute' : 'Mute'}
                  title={isMuted || volume === 0 ? 'Unmute (M)' : 'Mute (M)'}
                >
                  {isMuted || volume === 0 ? <VolumeX size={17} /> : <Volume2 size={17} />}
                </button>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={isMuted ? 0 : volume}
                  onChange={handleVolumeChange}
                  className="video-volume-slider"
                  aria-label="Volume"
                  title="Volume"
                />
              </div>

              <button
                type="button"
                className="video-ctrl-btn"
                onClick={toggleFullscreen}
                aria-label={isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}
                title={isFullscreen ? 'Exit Fullscreen (F)' : 'Fullscreen (F)'}
              >
                {isFullscreen ? <Minimize2 size={17} /> : <Maximize2 size={17} />}
                <span className="ctrl-btn-text">{isFullscreen ? 'Exit' : 'Fullscreen'}</span>
              </button>
            </div>

            <div className="modal-footer video-modal-footer">
              <div className="video-telemetry-status font-mono">
                <span className="video-pulse-dot" />
                <span>OPERATIONAL DEMO • SENTINEL INGESTION &amp; IMPACT ANALYTICS</span>
              </div>

              <div className="video-footer-actions">
                <button className="btn-ghost-sm" onClick={handleCloseModal}>
                  Close
                </button>
                <button
                  className="btn-primary-sm"
                  onClick={() => {
                    handleCloseModal();
                    onGetStarted(hasAnalysisData ? 'map' : 'upload');
                  }}
                >
                  <span>{hasAnalysisData ? 'Explore SATQUERY Map' : 'Launch Workspace'}</span>
                  <ArrowRight size={14} style={{ marginLeft: 6 }} />
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
