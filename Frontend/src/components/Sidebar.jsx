import React from 'react';
import { Home, Map, BarChart2, ShieldAlert, Upload, Bot, Satellite } from 'lucide-react';

const NAV_ITEMS = [
  { id: 'home', icon: Home, label: 'Home' },
  { id: 'map', icon: Map, label: 'Map Explorer' },
  { id: 'impact', icon: BarChart2, label: 'Impact Analysis' },
  { id: 'evacuation', icon: ShieldAlert, label: 'Evacuation Sites' },
  { id: 'upload', icon: Upload, label: 'Data & Upload' },
  { id: 'ai', icon: Bot, label: 'AI Assistant' },
];

export default function Sidebar({ activeTab, onSelectTab, onGoHome, hasData }) {
  return (
    <aside className="sidebar-nav">
      <div className="sidebar-top">
        <button
          className="sidebar-home-logo"
          onClick={onGoHome}
          title="Return to Landing Page"
        >
          <Satellite size={22} color="#38bdf8" />
        </button>
      </div>

      <nav className="sidebar-menu">
        {NAV_ITEMS.map((item) => {
          const IconComponent = item.icon;
          if (item.id === 'home') {
            return (
              <button
                key={item.id}
                className="sidebar-item"
                onClick={onGoHome}
                title={item.label}
              >
                <IconComponent size={20} className="item-icon" />
                <span className="item-label">{item.label}</span>
              </button>
            );
          }

          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              className={`sidebar-item ${isActive ? 'active' : ''}`}
              onClick={() => onSelectTab(item.id)}
              title={item.label}
            >
              <IconComponent size={20} className="item-icon" />
              <span className="item-label">{item.label}</span>
              {hasData && (item.id === 'map' || item.id === 'impact' || item.id === 'evacuation') && (
                <span className="badge-dot" />
              )}
            </button>
          );
        })}
      </nav>

      <div className="sidebar-bottom">
        <div className="sidebar-status-chip">
          <span className={`status-indicator-dot ${hasData ? 'ready' : 'idle'}`} />
          <span className="status-chip-text">{hasData ? 'Active Data' : 'No Data'}</span>
        </div>
      </div>
    </aside>
  );
}
