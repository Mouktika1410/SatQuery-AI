/**
 * Asynchronous CesiumJS dynamic loader.
 * Loads CesiumJS and its widget stylesheet on-demand so the main bundle
 * and initial 2D Leaflet map remain 100% lightweight and unaffected.
 */

let cesiumLoadingPromise = null;

export function loadCesium() {
  if (typeof window !== 'undefined' && window.Cesium) {
    return Promise.resolve(window.Cesium);
  }

  if (cesiumLoadingPromise) {
    return cesiumLoadingPromise;
  }

  cesiumLoadingPromise = new Promise((resolve, reject) => {
    // 1. Inject widgets.css if not already present
    if (!document.querySelector('link[data-cesium-widgets]')) {
      const link = document.createElement('link');
      link.rel = 'stylesheet';
      link.href = 'https://cesium.com/downloads/cesiumjs/releases/1.121/Build/Cesium/Widgets/widgets.css';
      link.setAttribute('data-cesium-widgets', 'true');
      document.head.appendChild(link);
    }

    // 2. Set CESIUM_BASE_URL before Cesium.js executes
    window.CESIUM_BASE_URL = 'https://cesium.com/downloads/cesiumjs/releases/1.121/Build/Cesium/';

    // 3. Inject Cesium.js
    const script = document.createElement('script');
    script.src = 'https://cesium.com/downloads/cesiumjs/releases/1.121/Build/Cesium/Cesium.js';
    script.async = true;

    script.onload = () => {
      if (window.Cesium) {
        resolve(window.Cesium);
      } else {
        cesiumLoadingPromise = null;
        reject(new Error('Cesium object not found on window after script load.'));
      }
    };

    script.onerror = (err) => {
      cesiumLoadingPromise = null;
      // Fallback attempt via unpkg
      const fallbackScript = document.createElement('script');
      fallbackScript.src = 'https://unpkg.com/cesium@1.121.0/Build/Cesium/Cesium.js';
      fallbackScript.async = true;
      fallbackScript.onload = () => {
        if (window.Cesium) {
          resolve(window.Cesium);
        } else {
          reject(new Error('Failed to load CesiumJS.'));
        }
      };
      fallbackScript.onerror = () => {
        reject(new Error('Failed to load CesiumJS from both primary and fallback CDN. Check network connectivity.'));
      };
      document.body.appendChild(fallbackScript);
    };

    document.body.appendChild(script);
  });

  return cesiumLoadingPromise;
}
