import React, { useState } from 'react';
import {
  BookOpen,
  X,
  Satellite,
  Layers,
  MapPin,
  Route,
  Activity,
  ShieldAlert,
  Brain,
  UploadCloud,
  CheckCircle2,
  ChevronRight,
  Sparkles,
  FileText,
  Compass,
  AlertTriangle,
  ArrowRight,
  Info,
} from 'lucide-react';

const GUIDE_SECTIONS = [
  { id: 'overview', title: '1. What SatQuery Is & Problem Solved', icon: Satellite },
  { id: 'workflow', title: '2. Step-by-Step User Workflow', icon: ChevronRight },
  { id: 'satellite-data', title: '3. Pre & Post-Flood Satellite Data', icon: UploadCloud },
  { id: 'sample-vs-user', title: '4. Sample Data vs User Uploads', icon: Sparkles },
  { id: 'detection', title: '5. Flood Detection & Polygons', icon: Activity },
  { id: 'gis-layers', title: '6. GIS Layers & Spatial Analysis', icon: Layers },
  { id: 'impact', title: '7. Impact Analysis & Risk Scoring', icon: ShieldAlert },
  { id: 'evacuation', title: '8. Evacuation Sites & Road Routing', icon: Route },
  { id: 'map-explorers', title: '9. 2D & 3D Map Explorers', icon: Compass },
  { id: 'ai-assistant', title: '10. AI Contextual Assistant', icon: Brain },
];

export default function UserGuideModal({ isOpen, onClose, onLaunchWorkspace, hasAnalysisData }) {
  const [activeSection, setActiveSection] = useState('overview');

  if (!isOpen) return null;

  return (
    <div className="user-guide-backdrop" onClick={onClose}>
      <div className="user-guide-modal-container" onClick={(e) => e.stopPropagation()}>
        {/* Modal Header */}
        <div className="user-guide-header">
          <div className="user-guide-title-block">
            <div className="user-guide-icon-badge">
              <BookOpen size={20} color="#38bdf8" />
            </div>
            <div>
              <h2 className="user-guide-title font-sans">SatQuery User & Operational Guide</h2>
              <p className="user-guide-subtitle font-mono">
                Comprehensive Reference • Satellite Remote Sensing & Spatial Disaster Intelligence
              </p>
            </div>
          </div>
          <button className="user-guide-close-btn" onClick={onClose} aria-label="Close User Guide">
            <X size={20} />
          </button>
        </div>

        {/* Modal Body: Left Navigation + Right Content */}
        <div className="user-guide-body">
          {/* Left Sidebar Navigation */}
          <nav className="user-guide-nav" aria-label="User Guide Navigation">
            {GUIDE_SECTIONS.map((sec) => {
              const Icon = sec.icon;
              const isActive = activeSection === sec.id;
              return (
                <button
                  key={sec.id}
                  className={`user-guide-nav-item ${isActive ? 'active' : ''}`}
                  onClick={() => setActiveSection(sec.id)}
                >
                  <Icon size={16} className="nav-item-icon" />
                  <span className="nav-item-title">{sec.title}</span>
                </button>
              );
            })}
          </nav>

          {/* Right Scrollable Content Pane */}
          <div className="user-guide-content-pane">
            {/* 1. What SatQuery Is & Problem Solved */}
            {activeSection === 'overview' && (
              <div className="guide-section-block">
                <div className="guide-badge-tag font-mono">SYSTEM OVERVIEW & PURPOSE</div>
                <h3 className="guide-section-heading">What SatQuery Is & The Problem It Solves</h3>

                <p className="guide-paragraph">
                  <strong>SatQuery</strong> is a mission-critical Geospatial AI platform engineered for automated
                  satellite flood surveillance, infrastructure impact quantification, and road-accessible evacuation routing.
                  It bridges the gap between raw multispectral earth-observation rasters and immediate on-the-ground disaster response decisions.
                </p>

                <div className="guide-card-grid">
                  <div className="guide-info-card">
                    <h4 className="guide-card-title text-amber">
                      <AlertTriangle size={16} style={{ marginRight: 6, verticalAlign: 'text-bottom' }} />
                      The Problem in Traditional Disaster Response
                    </h4>
                    <ul className="guide-list">
                      <li><strong>Manual Satellite Delays:</strong> Processing raw satellite GeoTIFFs manually takes hours or days during critical first-response windows.</li>
                      <li><strong>Disconnected GIS Silos:</strong> Cadastral administrative boundaries, road vectors, and building footprints are isolated from flood rasters.</li>
                      <li><strong>Inaccessible Evacuation Planning:</strong> Shelters are often chosen by straight-line proximity without verifying if connecting roads are submerged or passable.</li>
                    </ul>
                  </div>

                  <div className="guide-info-card">
                    <h4 className="guide-card-title text-cyan">
                      <CheckCircle2 size={16} style={{ marginRight: 6, verticalAlign: 'text-bottom' }} />
                      The SatQuery Solution
                    </h4>
                    <ul className="guide-list">
                      <li><strong>Automated Pipeline:</strong> Ingests dual-temporal GeoTIFFs and executes sub-minute NDWI water detection and vector polygonization.</li>
                      <li><strong>Real Spatial Overlays:</strong> Intersects flood extents directly with real local administrative panchayats, OSM roads, and buildings.</li>
                      <li><strong>Road-Network Routing:</strong> Calculates shortest evacuation routes strictly over passable road networks with zero synthetic geometry.</li>
                    </ul>
                  </div>
                </div>
              </div>
            )}

            {/* 2. Step-by-Step User Workflow */}
            {activeSection === 'workflow' && (
              <div className="guide-section-block">
                <div className="guide-badge-tag font-mono">OPERATIONAL PROCEDURE</div>
                <h3 className="guide-section-heading">Step-by-Step User Workflow</h3>

                <div className="guide-steps-list">
                  <div className="guide-step-item">
                    <div className="step-number-circle">01</div>
                    <div className="step-content">
                      <h4 className="step-title">Navigate to Data Ingestion</h4>
                      <p className="step-desc">
                        Click <strong>Data &amp; Upload</strong> in the sidebar or <strong>Upload Data</strong> in the top-right header to access the image ingestion portal.
                      </p>
                    </div>
                  </div>

                  <div className="guide-step-item">
                    <div className="step-number-circle">02</div>
                    <div className="step-content">
                      <h4 className="step-title">Supply Pre-Flood &amp; Post-Flood Imagery</h4>
                      <p className="step-desc">
                        Either drag and drop your own paired georeferenced GeoTIFF files or click the built-in <strong>"Use Kerala Sample"</strong> button inside both boxes to evaluate with verified Sentinel data.
                      </p>
                    </div>
                  </div>

                  <div className="guide-step-item">
                    <div className="step-number-circle">03</div>
                    <div className="step-content">
                      <h4 className="step-title">Configure Options &amp; Run Analysis</h4>
                      <p className="step-desc">
                        Optionally adjust detection algorithm (Auto NDWI/Otsu), morphology noise reduction iterations, and polygon simplification tolerance, then click <strong>Run Flood Analysis</strong>.
                      </p>
                    </div>
                  </div>

                  <div className="guide-step-item">
                    <div className="step-number-circle">04</div>
                    <div className="step-content">
                      <h4 className="step-title">Experience the 3D Map Explorer</h4>
                      <p className="step-desc">
                        The platform transitions directly into the <strong>3D Map Explorer</strong> with a cinematic oblique camera fly-in from regional India down to the Kerala inundation extent with satellite basemap and street context.
                      </p>
                    </div>
                  </div>

                  <div className="guide-step-item">
                    <div className="step-number-circle">05</div>
                    <div className="step-content">
                      <h4 className="step-title">Inspect Impact &amp; Evacuate</h4>
                      <p className="step-desc">
                        Switch between 3D and 2D views, click affected villages and roads for telemetry, review vulnerability rankings in <strong>Impact Analysis</strong>, and click candidate shelters in <strong>Evacuation Sites</strong> to highlight active road routes.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* 3. Pre & Post-Flood Satellite Data */}
            {activeSection === 'satellite-data' && (
              <div className="guide-section-block">
                <div className="guide-badge-tag font-mono">REMOTE SENSING SPECIFICATIONS</div>
                <h3 className="guide-section-heading">Pre-Flood &amp; Post-Flood Satellite Data</h3>

                <p className="guide-paragraph">
                  SatQuery uses a dual-temporal change detection methodology. Accurate flood delineation requires two temporal captures over the same geographic bounding box (AOI):
                </p>

                <div className="guide-specs-table-wrapper">
                  <table className="guide-specs-table">
                    <thead>
                      <tr>
                        <th>Parameter</th>
                        <th>Pre-Flood (Baseline)</th>
                        <th>Post-Flood (Event)</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td><strong>Purpose</strong></td>
                        <td>Establishes dry/normal seasonal baseline water bodies (rivers, lakes, canals).</td>
                        <td>Captures maximum surface water inundation during or immediately after the extreme weather event.</td>
                      </tr>
                      <tr>
                        <td><strong>Supported Formats</strong></td>
                        <td colSpan={2}>GeoTIFF (<code>.tif</code>, <code>.tiff</code>) with georeferenced affine transform metadata (GDAL compatible).</td>
                      </tr>
                      <tr>
                        <td><strong>Coordinate Systems</strong></td>
                        <td colSpan={2}>EPSG:4326 (WGS84 Lat/Lon), UTM projections, or Web Mercator (EPSG:3857). Coordinate matching is automatically verified.</td>
                      </tr>
                      <tr>
                        <td><strong>Sensors / Bands</strong></td>
                        <td colSpan={2}>Multispectral optical (Sentinel-2, Landsat-8/9) with Green &amp; NIR bands, or high-resolution SAR backscatter (Sentinel-1).</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* 4. Sample Data vs User Uploads */}
            {activeSection === 'sample-vs-user' && (
              <div className="guide-section-block">
                <div className="guide-badge-tag font-mono">DATASET OPTIONS & COMPARISON</div>
                <h3 className="guide-section-heading">Sample Data vs. User-Provided Uploads</h3>

                <p className="guide-paragraph">
                  SatQuery accommodates both instant demonstration evaluation and real-world operational user ingestions:
                </p>

                <div className="guide-card-grid">
                  <div className="guide-info-card">
                    <h4 className="guide-card-title text-cyan">
                      <Sparkles size={16} style={{ marginRight: 6, verticalAlign: 'text-bottom' }} />
                      Built-in Kerala Sample Dataset
                    </h4>
                    <p className="guide-card-text">
                      Pre-bundled Sentinel observations from the catastrophic August 2018 Kerala floods covering the
                      Vembanad Lake / Kottayam district corridor:
                    </p>
                    <ul className="guide-list font-mono text-sm">
                      <li><code>data/test_images/kerala_before_flood.tif</code> (Baseline)</li>
                      <li><code>data/test_images/kerala_after_flood.tif</code> (Inundation)</li>
                    </ul>
                    <p className="guide-card-text mt-2">
                      <strong>Designed for:</strong> Instant 1-click evaluation by judges and response planners without requiring local GIS files.
                      Runs through the <em>exact same live backend detection and GIS pipeline</em> as user uploads.
                    </p>
                  </div>

                  <div className="guide-info-card">
                    <h4 className="guide-card-title text-emerald">
                      <UploadCloud size={16} style={{ marginRight: 6, verticalAlign: 'text-bottom' }} />
                      User-Provided Satellite Ingestion
                    </h4>
                    <p className="guide-card-text">
                      Allows emergency response authorities to upload newly acquired satellite imagery from any active flood worldwide:
                    </p>
                    <ul className="guide-list">
                      <li>Upload dual GeoTIFFs directly via drag-and-drop or file browser.</li>
                      <li>Backend validates geospatial bounds, band alignment, and resolution.</li>
                      <li>Generates dynamic bounding boxes and custom regional footprints automatically.</li>
                    </ul>
                  </div>
                </div>
              </div>
            )}

            {/* 5. Flood Detection & Polygons */}
            {activeSection === 'detection' && (
              <div className="guide-section-block">
                <div className="guide-badge-tag font-mono">ALGORITHMIC PIPELINE</div>
                <h3 className="guide-section-heading">Flood Detection &amp; Polygon Generation</h3>

                <p className="guide-paragraph">
                  SatQuery implements an automated optical &amp; SAR water-index change detection engine:
                </p>

                <ul className="guide-feature-bullets">
                  <li>
                    <strong>Normalized Difference Water Index (NDWI):</strong> For multi-band optical imagery, SatQuery calculates
                    <code>NDWI = (Green - NIR) / (Green + NIR)</code>. Water strongly absorbs NIR while reflecting green light, producing positive index values.
                  </li>
                  <li>
                    <strong>Otsu Dynamic Thresholding:</strong> Automatically scans the bimodal histogram of water-index values to determine the optimal mathematical threshold separating land from inundated surfaces without human bias.
                  </li>
                  <li>
                    <strong>Morphological Post-Processing:</strong> Executes opening and closing morphological filters to eliminate single-pixel sensor noise and preserve real flood boundaries.
                  </li>
                  <li>
                    <strong>Vector Polygonization:</strong> Raster mask boundaries are converted into vector GeoJSON MultiPolygons using GDAL/rasterio contour extraction, calculating total inundated area (e.g. <code>41.50 km²</code>).
                  </li>
                </ul>
              </div>
            )}

            {/* 6. GIS Layers & Spatial Analysis */}
            {activeSection === 'gis-layers' && (
              <div className="guide-section-block">
                <div className="guide-badge-tag font-mono">SPATIAL INFRASTRUCTURE</div>
                <h3 className="guide-section-heading">GIS Layers &amp; Spatial Analysis</h3>

                <p className="guide-paragraph">
                  Rather than showing isolated water masks, SatQuery overlays real municipal cadastral boundaries and infrastructure networks:
                </p>

                <div className="guide-layers-breakdown">
                  <div className="layer-row">
                    <span className="layer-badge flood font-mono">Flood Polygon</span>
                    <span className="layer-desc">Translucent electric-blue inundation extent with animated perimeter boundaries.</span>
                  </div>
                  <div className="layer-row">
                    <span className="layer-badge villages font-mono">Cadastral Panchayats</span>
                    <span className="layer-desc">Real administrative village boundaries (Vechoor, Thalayazham, Kallara, etc.) with clickable population and risk telemetry.</span>
                  </div>
                  <div className="layer-row">
                    <span className="layer-badge roads font-mono">Inundated Roads</span>
                    <span className="layer-desc">500+ OpenStreetMap road segments categorized into submerged corridors (dashed red/amber) vs passable routes.</span>
                  </div>
                  <div className="layer-row">
                    <span className="layer-badge buildings font-mono">Building Footprints</span>
                    <span className="layer-desc">Real structural footprints intersected with flood polygons to quantify submerged property risk.</span>
                  </div>
                  <div className="layer-row">
                    <span className="layer-badge dem font-mono">DEM Elevation</span>
                    <span className="layer-desc">Digital Elevation Model data utilized to evaluate slope, run-off patterns, and shelter high-ground safety.</span>
                  </div>
                </div>
              </div>
            )}

            {/* 7. Impact Analysis & Risk Scoring */}
            {activeSection === 'impact' && (
              <div className="guide-section-block">
                <div className="guide-badge-tag font-mono">DECISION METRICS</div>
                <h3 className="guide-section-heading">Impact Analysis &amp; Multi-Criteria Risk Scoring</h3>

                <p className="guide-paragraph">
                  The <strong>Impact Analysis</strong> module ranks affected administrative units by a multi-factor vulnerability score (0 to 100):
                </p>

                <div className="guide-metrics-breakdown-card">
                  <h4 className="guide-card-title text-amber">Vulnerability Calculation Weights:</h4>
                  <ul className="guide-list">
                    <li><strong>Inundation Fraction (35%):</strong> Percentage of village land area submerged by water.</li>
                    <li><strong>Population Exposure (30%):</strong> Estimated number of residents trapped or requiring emergency assistance.</li>
                    <li><strong>Road Network Disruption (20%):</strong> Total kilometers of severed transit corridors within the panchayat.</li>
                    <li><strong>Infrastructure Vulnerability (15%):</strong> Count of submerged residential and commercial building footprints.</li>
                  </ul>
                  <div className="risk-level-chips">
                    <span className="risk-chip high">CRITICAL RISK (&gt;70)</span>
                    <span className="risk-chip med">ELEVATED RISK (40–70)</span>
                    <span className="risk-chip low">MONITORED RISK (&lt;40)</span>
                  </div>
                </div>
              </div>
            )}

            {/* 8. Evacuation Sites & Road Routing */}
            {activeSection === 'evacuation' && (
              <div className="guide-section-block">
                <div className="guide-badge-tag font-mono">LOGISTICS & ROUTING</div>
                <h3 className="guide-section-heading">Evacuation Sites &amp; Real Road Routing</h3>

                <p className="guide-paragraph">
                  SatQuery screens designated emergency shelters (schools, health centers, hospitals) that are strictly outside the flood zone:
                </p>

                <div className="guide-feature-card">
                  <h4 className="guide-card-title text-cyan">
                    <Route size={16} style={{ marginRight: 6, verticalAlign: 'text-bottom' }} />
                    Active Road-Network Route Highlighting
                  </h4>
                  <p className="guide-paragraph">
                    When you click any candidate evacuation center in either 3D or 2D:
                  </p>
                  <ul className="guide-list">
                    <li><strong>No Straight Lines:</strong> The route is computed using NetworkX Dijkstra shortest-path traversal strictly over real OpenStreetMap road segments.</li>
                    <li><strong>Origin Point:</strong> Derived automatically from the flood boundary departure point intersecting the primary affected village (e.g. <code>Flood Boundary (Vechoor Grama Panchayat)</code>).</li>
                    <li><strong>Distinctive High-Contrast Styling:</strong> Vivid electric cyan line (<code>#00e5ff</code>, width 4.5) with a dark slate casing halo (<code>#0f172a</code>, width 7.5) for crisp visibility over satellite terrain.</li>
                    <li><strong>Single Active Route:</strong> Selecting Center B automatically removes Route A and renders Route B; clicking the background clears all active routes.</li>
                    <li><strong>Popup Metrics:</strong> Displays both straight-line flood proximity and actual driving/walking road distance (e.g. <code>0.51 km</code>).</li>
                  </ul>
                </div>
              </div>
            )}

            {/* 9. 2D & 3D Map Explorers */}
            {activeSection === 'map-explorers' && (
              <div className="guide-section-block">
                <div className="guide-badge-tag font-mono">CARTOGRAPHIC VISUALIZATION</div>
                <h3 className="guide-section-heading">2D &amp; 3D Map Explorers</h3>

                <div className="guide-card-grid">
                  <div className="guide-info-card">
                    <h4 className="guide-card-title text-cyan">
                      <Compass size={16} style={{ marginRight: 6, verticalAlign: 'text-bottom' }} />
                      3D MapLibre Satellite Explorer
                    </h4>
                    <ul className="guide-list">
                      <li>High-resolution satellite basemap with authentic Google Earth-style orbital perspective.</li>
                      <li>Google Maps hybrid street and place-label context overlay for immediate landmark recognition.</li>
                      <li>Interactive 3D oblique tilt and rotation (up to 85° pitch) with compass re-centering.</li>
                      <li>Full raycasting click detection on flood polygons, village boundaries, and evacuation pins.</li>
                    </ul>
                  </div>

                  <div className="guide-info-card">
                    <h4 className="guide-card-title text-emerald">
                      <Layers size={16} style={{ marginRight: 6, verticalAlign: 'text-bottom' }} />
                      2D Leaflet Tactical Map
                    </h4>
                    <ul className="guide-list">
                      <li>Top-down tactical overview ideal for precise distance measurement and print exports.</li>
                      <li>Layer switch panel enabling individual toggling of Flood, Villages, Roads, and Evacuation Sites.</li>
                      <li>Full state synchronization with the 3D view: switching preserves selected features and active routes.</li>
                    </ul>
                  </div>
                </div>
              </div>
            )}

            {/* 10. AI Contextual Assistant */}
            {activeSection === 'ai-assistant' && (
              <div className="guide-section-block">
                <div className="guide-badge-tag font-mono">COGNITIVE ASSISTANCE</div>
                <h3 className="guide-section-heading">AI &amp; VLM Disaster Response Assistant</h3>

                <p className="guide-paragraph">
                  SatQuery incorporates a specialized AI assistant accessible via the <strong>AI Assistant</strong> tab.
                  The assistant receives full telemetry from the active session, including:
                </p>

                <ul className="guide-feature-bullets">
                  <li>Total calculated flood surface area and percentage change.</li>
                  <li>Specific names, population counts, and vulnerability tiers of affected Panchayats.</li>
                  <li>Passable road corridors vs. submerged routes.</li>
                  <li>Screened evacuation shelters, capacities, and calculated road route distances.</li>
                </ul>

                <p className="guide-paragraph mt-3">
                  Responders can ask natural language operational queries like:
                  <em> "Which village has the highest vulnerability score?", "What is the closest high-capacity evacuation school?",</em> or
                  <em> "Provide an executive situation report for the Kottayam district."</em>
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Modal Footer */}
        <div className="user-guide-footer">
          <div className="guide-footer-telemetry font-mono">
            SATQUERY DISASTER INTELLIGENCE SYSTEM • REAL SENTINEL-2 &amp; OSM DATA ENGINE
          </div>
          <div className="guide-footer-actions">
            <button className="btn-guide-close font-sans" onClick={onClose}>
              Close Guide
            </button>
            <button
              className="btn-guide-launch font-sans"
              onClick={() => {
                onClose();
                onLaunchWorkspace && onLaunchWorkspace(hasAnalysisData ? 'map' : 'upload');
              }}
            >
              <span>{hasAnalysisData ? 'Explore SATQUERY Map' : 'Launch Workspace'}</span>
              <ArrowRight size={15} style={{ marginLeft: 6 }} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
