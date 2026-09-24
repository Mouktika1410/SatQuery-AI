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
    const targets = await getJson('http://127.0.0.1:9222/json');
    const pageTarget = targets.find((t) => t.type === 'page');
    if (!pageTarget) throw new Error('No page target found');

    const client = new CDPClient(pageTarget.webSocketDebuggerUrl);
    await client.connect();
    console.log('Connected to Chrome DevTools Protocol');

    await client.send('Page.enable');
    await client.send('DOM.enable');
    await client.send('Runtime.enable');

    console.log('Navigating to http://localhost:5173...');
    await client.send('Page.navigate', { url: 'http://localhost:5173' });
    await wait(2500);

    // =========================================================================
    // TEST 1: User Guide Button on Landing Page
    // =========================================================================
    console.log('\n--- TEST 1: User Guide Button on Landing Page ---');
    const landingGuideBtn = await client.eval(`(() => {
      const btn = document.querySelector('.btn-header-guide');
      const oldBtn = document.querySelector('.btn-header-platform');
      return {
        hasGuideBtn: Boolean(btn),
        guideBtnText: btn ? btn.textContent.trim() : null,
        hasOldPlatformBtn: Boolean(oldBtn),
      };
    })()`);
    console.log('Landing Page header check:', landingGuideBtn);

    if (!landingGuideBtn.hasGuideBtn) {
      throw new Error('User Guide button missing in Landing Page header');
    }
    if (landingGuideBtn.hasOldPlatformBtn) {
      throw new Error('Old Open Platform button still present in header');
    }

    // Click User Guide button
    console.log('Opening User Guide Modal...');
    await client.eval(`(() => {
      document.querySelector('.btn-header-guide').click();
    })()`);
    await wait(800);

    const guideModalCheck = await client.eval(`(() => {
      const modal = document.querySelector('.user-guide-modal-container');
      const title = modal ? modal.querySelector('.user-guide-title')?.textContent : null;
      const navItems = modal ? Array.from(modal.querySelectorAll('.user-guide-nav-item')).map(n => n.textContent.trim()) : [];
      return {
        isOpen: Boolean(modal),
        title,
        navCount: navItems.length,
        navItems,
      };
    })()`);
    console.log('User Guide Modal check:', guideModalCheck);

    if (!guideModalCheck.isOpen || guideModalCheck.navCount < 8) {
      throw new Error('User Guide modal failed to render properly');
    }

    // Take screenshot of User Guide modal
    const shotGuide = await client.send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(
      path.join(ARTIFACT_DIR, 'user_guide_modal_landing.png'),
      Buffer.from(shotGuide.data, 'base64')
    );
    console.log('Saved screenshot: user_guide_modal_landing.png');

    // Close User Guide modal
    await client.eval(`(() => {
      const closeBtn = document.querySelector('.user-guide-close-btn') || document.querySelector('.btn-guide-close');
      if (closeBtn) closeBtn.click();
    })()`);
    await wait(600);

    // =========================================================================
    // TEST 2: Enter Workspace & Check Header User Guide Button
    // =========================================================================
    console.log('\n--- TEST 2: Workspace Header User Guide Button ---');
    await client.eval(`(() => {
      const exploreBtn = document.querySelector('.btn-hero-explore');
      if (exploreBtn) exploreBtn.click();
    })()`);
    await wait(1000);

    const workspaceGuideBtn = await client.eval(`(() => {
      const btn = document.querySelector('.header-cta-guide');
      return {
        hasWorkspaceGuideBtn: Boolean(btn),
        guideBtnText: btn ? btn.textContent.trim() : null,
      };
    })()`);
    console.log('Workspace header check:', workspaceGuideBtn);

    if (!workspaceGuideBtn.hasWorkspaceGuideBtn) {
      throw new Error('User Guide button missing in workspace header');
    }

    // =========================================================================
    // TEST 3: Sample Data inside Data & Upload Page
    // =========================================================================
    console.log('\n--- TEST 3: Sample Data Inside Upload Boxes ---');
    const uploadBoxesCheck = await client.eval(`(() => {
      const dropzones = document.querySelectorAll('.ingestion-dropzone-box');
      const sampleButtons = document.querySelectorAll('.btn-use-sample-inside');
      const quickBothBtn = document.querySelector('.btn-quick-sample-load');
      return {
        dropzonesCount: dropzones.length,
        sampleButtonsCount: sampleButtons.length,
        buttonTexts: Array.from(sampleButtons).map(b => b.textContent.trim()),
        hasQuickBothBtn: Boolean(quickBothBtn),
      };
    })()`);
    console.log('Upload boxes sample check:', uploadBoxesCheck);

    if (uploadBoxesCheck.sampleButtonsCount !== 2) {
      throw new Error(`Expected 2 "Use Kerala Sample" buttons inside upload boxes, found ${uploadBoxesCheck.sampleButtonsCount}`);
    }

    const shotUploadEmpty = await client.send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(
      path.join(ARTIFACT_DIR, 'upload_boxes_with_sample_buttons.png'),
      Buffer.from(shotUploadEmpty.data, 'base64')
    );
    console.log('Saved screenshot: upload_boxes_with_sample_buttons.png');

    // Click "Use Kerala Sample" in Pre-Flood box
    console.log('Clicking "Use Kerala Sample" for Pre-Flood...');
    await client.eval(`(() => {
      const sampleButtons = document.querySelectorAll('.btn-use-sample-inside');
      if (sampleButtons[0]) sampleButtons[0].click();
    })()`);
    await wait(1500);

    const preLoadedCheck = await client.eval(`(() => {
      const dropzones = document.querySelectorAll('.ingestion-dropzone-box');
      const preBox = dropzones[0];
      const selected = preBox?.querySelector('.file-selected-info');
      const name = selected?.querySelector('.file-upload-name')?.textContent;
      const size = selected?.querySelector('.file-upload-size')?.textContent;
      const btn = document.querySelector('.btn-primary-ingestion');
      return {
        hasPreSelected: Boolean(selected),
        name,
        size,
        btnDisabled: btn ? btn.disabled : true,
      };
    })()`);
    console.log('Pre-Flood loaded check:', preLoadedCheck);
    if (!preLoadedCheck.hasPreSelected || preLoadedCheck.name !== 'kerala_before_flood.tif') {
      throw new Error('Pre-Flood sample failed to load into upload box');
    }

    // Click "Use Kerala Sample" in Post-Flood box
    console.log('Clicking "Use Kerala Sample" for Post-Flood...');
    await client.eval(`(() => {
      const sampleButtons = document.querySelectorAll('.btn-use-sample-inside');
      // pre is already selected, so post is either sampleButtons[0] or sampleButtons[1]
      const postBtn = document.querySelectorAll('.btn-use-sample-inside')[0];
      if (postBtn) postBtn.click();
    })()`);
    await wait(1500);

    const postLoadedCheck = await client.eval(`(() => {
      const dropzones = document.querySelectorAll('.ingestion-dropzone-box');
      const postBox = dropzones[1];
      const selected = postBox?.querySelector('.file-selected-info');
      const name = selected?.querySelector('.file-upload-name')?.textContent;
      const size = selected?.querySelector('.file-upload-size')?.textContent;
      const btn = document.querySelector('.btn-primary-ingestion');
      return {
        hasPostSelected: Boolean(selected),
        name,
        size,
        btnDisabled: btn ? btn.disabled : true,
        btnText: btn ? btn.textContent.trim() : null,
      };
    })()`);
    console.log('Post-Flood loaded check:', postLoadedCheck);
    if (!postLoadedCheck.hasPostSelected || postLoadedCheck.name !== 'kerala_after_flood.tif') {
      throw new Error('Post-Flood sample failed to load into upload box');
    }
    if (postLoadedCheck.btnDisabled) {
      throw new Error('"Run Flood Analysis" button is not enabled after loading both samples');
    }

    const shotBothLoaded = await client.send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(
      path.join(ARTIFACT_DIR, 'upload_both_samples_populated.png'),
      Buffer.from(shotBothLoaded.data, 'base64')
    );
    console.log('Saved screenshot: upload_both_samples_populated.png');

    // =========================================================================
    // TEST 4: Run Analysis with Sample Data through Live Pipeline
    // =========================================================================
    console.log('\n--- TEST 4: Running Analysis Pipeline with Sample Data ---');
    await client.eval(`(() => {
      const btn = document.querySelector('.btn-primary-ingestion');
      if (btn) btn.click();
    })()`);

    // Wait for transition or map view
    console.log('Waiting for pipeline and Map Explorer...');
    let inMapView = false;
    for (let i = 0; i < 45; i++) {
      await wait(1500);
      await client.eval(`(() => {
        const skipBtn = document.querySelector('.hud-skip-btn');
        if (skipBtn) skipBtn.click();
      })()`);

      inMapView = await client.eval(`(() => {
        return Boolean(document.querySelector('.map-3d-wrapper') || window.__map3d);
      })()`);
      if (inMapView) {
        console.log(`Map view loaded successfully with sample data after ${(i + 1) * 1.5}s!`);
        break;
      }
    }
    if (!inMapView) throw new Error('Timed out waiting for Map Explorer');

    await wait(3000);

    const mapResults = await client.eval(`(() => {
      const candidates = window.__evacuationCandidates || [];
      const floodGeo = window.__floodGeoJSON;
      return {
        hasFloodGeo: Boolean(floodGeo),
        featuresCount: floodGeo?.features?.length || 0,
        candidatesCount: candidates.length,
      };
    })()`);
    console.log('Pipeline Map Result with Sample Data:', mapResults);

    if (!mapResults.hasFloodGeo || mapResults.candidatesCount === 0) {
      throw new Error('Pipeline results missing after running with sample data');
    }

    const shotMapLoaded = await client.send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(
      path.join(ARTIFACT_DIR, 'map_explorer_after_sample_analysis.png'),
      Buffer.from(shotMapLoaded.data, 'base64')
    );
    console.log('Saved screenshot: map_explorer_after_sample_analysis.png');

    console.log('\n=== ALL USER GUIDE & SAMPLE DATA TESTS PASSED ===');
  } finally {
    chrome.kill();
  }
}

main().catch((err) => {
  console.error('Test run failed:', err);
  process.exit(1);
});
