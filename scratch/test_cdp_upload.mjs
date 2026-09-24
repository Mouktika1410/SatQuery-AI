import { spawn } from 'child_process';
import http from 'http';
import fs from 'fs';
import path from 'path';

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

async function run() {
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
    const client = new CDPClient(pageTarget.webSocketDebuggerUrl);
    await client.connect();

    await client.send('Page.enable');
    await client.send('DOM.enable');
    await client.send('Runtime.enable');

    console.log('Navigating to http://localhost:5173...');
    await client.send('Page.navigate', { url: 'http://localhost:5173' });
    await wait(2500);

    // Click Explore SATQUERY
    await client.eval(`(() => {
      const btn = document.querySelector('.btn-hero-explore') || document.querySelector('.btn-header-platform');
      if (btn) btn.click();
    })()`);
    await wait(1000);

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

    console.log('Found nodes:', { pre: preInput.nodeId, post: postInput.nodeId });

    await client.send('DOM.setFileInputFiles', {
      files: ['c:\\SatQuery\\data\\test_images\\kerala_before_flood.tif'],
      nodeId: preInput.nodeId,
    });
    await client.send('DOM.setFileInputFiles', {
      files: ['c:\\SatQuery\\data\\test_images\\kerala_after_flood.tif'],
      nodeId: postInput.nodeId,
    });
    await wait(1000);

    const checkUpload = await client.eval(`(() => {
      const btn = document.querySelector('.btn-primary-ingestion');
      const filesSelected = document.querySelectorAll('.file-selected-info');
      return {
        filesSelectedCount: filesSelected.length,
        btnDisabled: btn ? btn.disabled : true,
        btnText: btn ? btn.textContent.trim() : null
      };
    })()`);
    console.log('Upload check result:', checkUpload);
  } finally {
    chrome.kill();
  }
}

run().catch((e) => {
  console.error(e);
  process.exit(1);
});
