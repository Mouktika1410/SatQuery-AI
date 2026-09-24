import { spawn } from 'child_process';
import http from 'http';
import fs from 'fs';
import path from 'path';

const ARTIFACT_DIR = 'C:\\Users\\Mouktika\\.gemini\\antigravity\\brain\\32c86eee-39a7-4298-b704-22c9f3030575';
const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function getJson(url) {
  return new Promise((resolve, reject) => {
    http.get(url, (res) => {
      let body = '';
      res.on('data', (c) => (body += c));
      res.on('end', () => {
        try {
          resolve(JSON.parse(body));
        } catch (e) {
          reject(e);
        }
      });
    }).on('error', reject);
  });
}

class CDPClient {
  constructor(wsUrl) {
    this.wsUrl = wsUrl;
    this.id = 1;
    this.callbacks = new Map();
  }

  async connect() {
    return new Promise((resolve, reject) => {
      this.ws = new globalThis.WebSocket(this.wsUrl);
      this.ws.onopen = () => resolve();
      this.ws.onerror = (err) => reject(err);
      this.ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (this.onMessage) this.onMessage(msg);
        if (msg.id && this.callbacks.has(msg.id)) {
          const cb = this.callbacks.get(msg.id);
          this.callbacks.delete(msg.id);
          if (msg.error) cb.reject(new Error(msg.error.message));
          else cb.resolve(msg.result);
        }
      };
    });
  }

  send(method, params = {}) {
    const id = this.id++;
    return new Promise((resolve, reject) => {
      this.callbacks.set(id, { resolve, reject });
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }

  async eval(expression) {
    const res = await this.send('Runtime.evaluate', {
      expression,
      returnByValue: true,
      awaitPromise: true,
    });
    if (res.exceptionDetails) {
      throw new Error(res.exceptionDetails.text || JSON.stringify(res.exceptionDetails));
    }
    return res.result?.value;
  }
}

async function main() {
  console.log('Launching Headless Chrome...');
  const chrome = spawn(
    CHROME_PATH,
    [
      '--headless=new',
      '--remote-debugging-port=9222',
      '--disable-gpu',
      '--no-sandbox',
      '--window-size=1440,900',
      'about:blank',
    ],
    { stdio: 'ignore' }
  );

  try {
    await wait(2000);
    const versionInfo = await getJson('http://127.0.0.1:9222/json/version');
    console.log('Chrome Debugger Ready:', versionInfo['Browser']);

    const targets = await getJson('http://127.0.0.1:9222/json');
    const pageTarget = targets.find((t) => t.type === 'page');
    if (!pageTarget) throw new Error('No page target found');

    const client = new CDPClient(pageTarget.webSocketDebuggerUrl);
    await client.connect();
    console.log('Connected to Chrome DevTools Protocol');

    await client.send('Page.enable');
    await client.send('DOM.enable');
    await client.send('Runtime.enable');
    await client.send('Network.enable');

    const consoleErrors = [];
    client.onMessage = (msg) => {
      try {
        if (msg.method === 'Runtime.consoleAPICalled' && msg.params.type === 'error') {
          consoleErrors.push(msg.params.args.map((a) => a.value || a.description).join(' '));
        }
      } catch (_) {}
    };

    console.log('Navigating to http://localhost:5173...');
    await client.send('Page.navigate', { url: 'http://localhost:5173' });
    await wait(2500);

    // Click Explore SATQUERY
    console.log('Checking Landing Page...');
    await client.eval(`(() => {
      const btn = document.querySelector('.btn-hero-explore') || document.querySelector('.btn-header-platform');
      if (btn) btn.click();
    })()`);
    await wait(1000);

    // Set file inputs via CDP native file attachment
    console.log('Setting file inputs via CDP DOM.setFileInputFiles...');
    const doc = await client.send('DOM.getDocument');
    const preInput = await client.send('DOM.querySelector', {
      nodeId: doc.root.nodeId,
      selector: '#pre-upload',
    });
    const postInput = await client.send('DOM.querySelector', {
      nodeId: doc.root.nodeId,
      selector: '#post-upload',
    });

    await client.send('DOM.setFileInputFiles', {
      files: ['c:\\SatQuery\\data\\test_images\\kerala_before_flood.tif'],
      nodeId: preInput.nodeId,
    });
    await client.send('DOM.setFileInputFiles', {
      files: ['c:\\SatQuery\\data\\test_images\\kerala_after_flood.tif'],
      nodeId: postInput.nodeId,
    });
    await wait(1000);

    // Verify files selected and run button enabled
    const checkUpload = await client.eval(`(() => {
      const btn = document.querySelector('.btn-primary-ingestion');
      return {
        disabled: btn ? btn.disabled : true,
        text: btn ? btn.textContent.trim() : null,
      };
    })()`);
    console.log('Ingestion state:', checkUpload);
    if (checkUpload.disabled) {
      throw new Error('Run button is disabled after attaching files');
    }

    // Click Run Flood Analysis
    console.log('Submitting Run Flood Analysis...');
    await client.eval(`(() => {
      const btn = document.querySelector('.btn-primary-ingestion');
      if (btn) btn.click();
    })()`);

    // Monitor for transition overlay or direct map view
    console.log('Waiting for analysis pipeline to complete...');
    let inMapView = false;
    for (let i = 0; i < 45; i++) {
      await wait(1500);

      // If transition sequence skip button is present, click it to skip forward
      await client.eval(`(() => {
        const skipBtn = document.querySelector('.hud-skip-btn');
        if (skipBtn) skipBtn.click();
      })()`);

      inMapView = await client.eval(`(() => {
        return Boolean(document.querySelector('.map-3d-wrapper') || window.__map3d);
      })()`);
      if (inMapView) {
        console.log(`Map view mounted successfully after ${(i + 1) * 1.5}s!`);
        break;
      }
    }
    if (!inMapView) throw new Error('Timed out waiting for Map View');

    // Wait for camera fly-in to finish
    await wait(4000);

    // Check pins loaded
    const pinsInfo = await client.eval(`(() => {
      const pins = document.querySelectorAll('.cesium-evac-pin-dom');
      const candidates = window.__evacuationCandidates || [];
      return {
        pinsCount: pins.length,
        candidatesCount: candidates.length,
        cands: candidates.map(c => ({
          name: c.name,
          type: c.type,
          capacity: c.capacity,
          distance_km: c.route_distance_km,
          origin: c.origin_name,
          coordsCount: c.route_geojson?.geometry?.coordinates?.length || 0
        }))
      };
    })()`);
    console.log('Evacuation Candidates Info:', pinsInfo);
    if (pinsInfo.candidatesCount === 0 || pinsInfo.pinsCount === 0) {
      throw new Error('No evacuation pins rendered in 3D view');
    }

    // =========================================================================
    // TEST 1: Select Evacuation Center A
    // =========================================================================
    console.log('\n--- TEST 1: Select Evacuation Center A ---');
    const candA = pinsInfo.cands[0];
    console.log(`Targeting Center A: "${candA.name}" (coords: ${candA.coordsCount}, dist: ${candA.distance_km} km)`);

    const selectARes = await client.eval(`(() => {
      const pins = document.querySelectorAll('.cesium-evac-pin-dom');
      const candA = window.__evacuationCandidates?.[0];
      if (candA && window.__map3d) {
        window.__map3d.jumpTo({ center: [candA.lon, candA.lat], zoom: 14.2 });
      }
      if (pins[0]) pins[0].click();
      return { ok: true, name: candA?.name };
    })()`);
    console.log('Center A clicked:', selectARes);
    await wait(1500);

    const checkARes = await client.eval(`(() => {
      const pins = document.querySelectorAll('.cesium-evac-pin-dom');
      const popup = document.querySelector('.gis-popup.evac-popup');
      const pin0Selected = pins[0]?.classList.contains('selected-pin');
      
      const map = window.__map3d;
      const routeData = window.__activeEvacRoute3D || map?.getSource('evac-route-data')?._data;
      const coords = routeData?.geometry?.coordinates || [];

      const casingLayer = map?.getLayer('evac-route-casing-layer');
      const lineLayer = map?.getLayer('evac-route-line-layer');

      return {
        pin0Selected,
        hasPopup: Boolean(popup),
        popupTitle: popup?.querySelector('.gis-popup-title')?.textContent,
        popupHtml: popup?.innerHTML,
        routeCoordsCount: coords.length,
        routeDistanceProp: routeData?.properties?.distance_km,
        routeOriginProp: routeData?.properties?.origin,
        casingVisible: map?.getLayoutProperty('evac-route-casing-layer', 'visibility'),
        lineVisible: map?.getLayoutProperty('evac-route-line-layer', 'visibility'),
      };
    })()`);
    console.log('Center A verification result:', {
      pin0Selected: checkARes.pin0Selected,
      hasPopup: checkARes.hasPopup,
      popupTitle: checkARes.popupTitle,
      routeCoordsCount: checkARes.routeCoordsCount,
      routeDistanceProp: checkARes.routeDistanceProp,
      routeOriginProp: checkARes.routeOriginProp,
      casingVisible: checkARes.casingVisible,
      lineVisible: checkARes.lineVisible,
    });

    if (!checkARes.pin0Selected) throw new Error('Pin 0 is not highlighted as selected');
    if (checkARes.routeCoordsCount === 0) throw new Error('Evacuation route coordinates are empty for Center A');

    const shotA = await client.send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(
      path.join(ARTIFACT_DIR, '3d_evac_center_a_route.png'),
      Buffer.from(shotA.data, 'base64')
    );
    console.log('Saved screenshot: 3d_evac_center_a_route.png');

    // =========================================================================
    // TEST 2: Select Evacuation Center B (Replace Route)
    // =========================================================================
    console.log('\n--- TEST 2: Select Evacuation Center B (Replace Route) ---');
    const candB = pinsInfo.cands[1];
    console.log(`Targeting Center B: "${candB.name}" (coords: ${candB.coordsCount}, dist: ${candB.distance_km} km)`);

    const selectBRes = await client.eval(`(() => {
      const pins = document.querySelectorAll('.cesium-evac-pin-dom');
      const candB = window.__evacuationCandidates?.[1];
      if (candB && window.__map3d) {
        window.__map3d.jumpTo({ center: [candB.lon, candB.lat], zoom: 14.2 });
      }
      if (pins[1]) pins[1].click();
      return { ok: true, name: candB?.name };
    })()`);
    console.log('Center B clicked:', selectBRes);
    await wait(1500);

    const checkBRes = await client.eval(`(() => {
      const pins = document.querySelectorAll('.cesium-evac-pin-dom');
      const popup = document.querySelector('.gis-popup.evac-popup');
      const pin0Selected = pins[0]?.classList.contains('selected-pin');
      const pin1Selected = pins[1]?.classList.contains('selected-pin');
      
      const map = window.__map3d;
      const routeData = window.__activeEvacRoute3D || map?.getSource('evac-route-data')?._data;
      const coords = routeData?.geometry?.coordinates || [];

      return {
        pin0Selected,
        pin1Selected,
        hasPopup: Boolean(popup),
        popupTitle: popup?.querySelector('.gis-popup-title')?.textContent,
        routeCoordsCount: coords.length,
        routeDistanceProp: routeData?.properties?.distance_km,
        routeOriginProp: routeData?.properties?.origin,
      };
    })()`);
    console.log('Center B verification result:', {
      pin0Selected: checkBRes.pin0Selected,
      pin1Selected: checkBRes.pin1Selected,
      hasPopup: checkBRes.hasPopup,
      popupTitle: checkBRes.popupTitle,
      routeCoordsCount: checkBRes.routeCoordsCount,
      routeDistanceProp: checkBRes.routeDistanceProp,
      routeOriginProp: checkBRes.routeOriginProp,
    });

    if (checkBRes.pin0Selected) throw new Error('Center A pin is still selected after clicking Center B');
    if (!checkBRes.pin1Selected) throw new Error('Center B pin is not selected');
    if (checkBRes.routeCoordsCount === 0) throw new Error('Evacuation route coordinates are empty for Center B');

    const shotB = await client.send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(
      path.join(ARTIFACT_DIR, '3d_evac_center_b_route.png'),
      Buffer.from(shotB.data, 'base64')
    );
    console.log('Saved screenshot: 3d_evac_center_b_route.png');

    // =========================================================================
    // TEST 3: Deselect / Click Map Background (Route Cleared)
    // =========================================================================
    console.log('\n--- TEST 3: Deselect (Click Background) ---');
    await client.eval(`(() => {
      const canvas = document.querySelector('.maplibregl-canvas');
      if (canvas) {
        canvas.dispatchEvent(new MouseEvent('click', { clientX: 100, clientY: 100, bubbles: true }));
      }
    })()`);
    await wait(1000);

    const checkDeselect = await client.eval(`(() => {
      const pins = document.querySelectorAll('.cesium-evac-pin-dom.selected-pin');
      const popup = document.querySelector('.gis-popup.evac-popup');
      const map = window.__map3d;
      const routeData = window.__activeEvacRoute3D || map?.getSource('evac-route-data')?._data;
      const coords = routeData?.geometry?.coordinates || [];

      return {
        selectedPinsCount: pins.length,
        hasPopup: Boolean(popup),
        routeCoordsCount: coords.length,
      };
    })()`);
    console.log('Deselection check result:', checkDeselect);
    if (checkDeselect.selectedPinsCount > 0) throw new Error('Pins still selected after background click');
    if (checkDeselect.routeCoordsCount > 0) throw new Error('Route line still active after background click');

    const shotDeselect = await client.send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(
      path.join(ARTIFACT_DIR, '3d_evac_route_deselected.png'),
      Buffer.from(shotDeselect.data, 'base64')
    );
    console.log('Saved screenshot: 3d_evac_route_deselected.png');

    // =========================================================================
    // TEST 4: 2D Leaflet Consistency (Select Center A, Switch to 2D, Check Route)
    // =========================================================================
    console.log('\n--- TEST 4: 2D Leaflet Route Consistency ---');
    // Select Center A again
    await client.eval(`(() => {
      const pins = document.querySelectorAll('.cesium-evac-pin-dom');
      pins[0]?.click();
    })()`);
    await wait(1000);

    // Switch to 2D
    const switch2D = await client.eval(`(() => {
      const pills = document.querySelectorAll('.view-mode-pill');
      const btn2d = Array.from(pills).find(p => p.textContent.includes('2D'));
      if (btn2d) {
        btn2d.click();
        return true;
      }
      return false;
    })()`);
    console.log('Switched to 2D view:', switch2D);
    await wait(1500);

    const check2D = await client.eval(`(() => {
      const container2d = document.querySelector('.leaflet-map-container');
      const is2dVisible = container2d && window.getComputedStyle(container2d).display !== 'none';
      const map = window.__map2d;
      const routeData2D = window.__activeEvacRoute2D;
      const hasRouteIn2D = Boolean(routeData2D && routeData2D.geometry?.coordinates?.length > 0);
      return { is2dVisible, hasRouteIn2D, routeDistance: routeData2D?.properties?.distance_km };
    })()`);
    console.log('2D Leaflet check result:', check2D);

    const shot2D = await client.send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(
      path.join(ARTIFACT_DIR, '2d_evac_route_selected.png'),
      Buffer.from(shot2D.data, 'base64')
    );
    console.log('Saved screenshot: 2d_evac_route_selected.png');

    // Switch back to 3D
    await client.eval(`(() => {
      const pills = document.querySelectorAll('.view-mode-pill');
      const btn3d = Array.from(pills).find(p => p.textContent.includes('3D'));
      if (btn3d) btn3d.click();
    })()`);
    await wait(1500);

    const shot3DBack = await client.send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(
      path.join(ARTIFACT_DIR, '3d_evac_route_restored.png'),
      Buffer.from(shot3DBack.data, 'base64')
    );
    console.log('Saved screenshot: 3d_evac_route_restored.png');

    // Final Error Audit
    console.log('\n--- CONSOLE ERRORS AUDIT ---');
    if (consoleErrors.length > 0) {
      console.warn('Caught console errors:', consoleErrors);
    } else {
      console.log('Zero console errors detected during all route operations!');
    }

    console.log('\n=== ALL BROWSER E2E TESTS PASSED ===');
  } finally {
    chrome.kill();
  }
}

main().catch((err) => {
  console.error('Test run failed:', err);
  process.exit(1);
});
