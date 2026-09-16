const BASE_URL = '/api/v1';

/**
 * Validate a pair of GeoTIFF files.
 */
export async function validateImages(preFile, postFile) {
  const formData = new FormData();
  formData.append('pre_flood', preFile);
  formData.append('post_flood', postFile);

  const res = await fetch(`${BASE_URL}/flood/validate`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Validation failed (${res.status}): ${text}`);
  }
  return res.json();
}

/**
 * Run the complete flood analysis pipeline in one request.
 */
export async function runFullPipeline(preFile, postFile, options = {}) {
  const formData = new FormData();
  formData.append('pre_flood', preFile);
  formData.append('post_flood', postFile);
  formData.append('method', options.method || 'auto');
  formData.append('simplify_tolerance', String(options.simplifyTolerance ?? '0.0001'));
  formData.append('buffer_m', String(options.bufferM ?? '100.0'));

  const res = await fetch(`${BASE_URL}/flood/pipeline`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Pipeline failed (${res.status}): ${text}`);
  }
  return res.json();
}

/**
 * Send a natural-language question to the AI assistant.
 */
export async function sendChatQuery(question, sessionId = null, context = null) {
  const res = await fetch(`${BASE_URL}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, session_id: sessionId, context }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Chat request failed (${res.status}): ${text}`);
  }
  return res.json();
}

/**
 * Get cached session results by session_id.
 */
export async function getSession(sessionId) {
  const res = await fetch(`${BASE_URL}/flood/session/${sessionId}`);
  if (!res.ok) throw new Error(`Session not found: ${sessionId}`);
  return res.json();
}

/**
 * Check backend health.
 */
export async function checkHealth() {
  const res = await fetch('/health');
  if (!res.ok) throw new Error('Backend health check failed');
  return res.json();
}
