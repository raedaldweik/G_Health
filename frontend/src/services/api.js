const json = async (res) => {
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
};

export const getHealth = () => fetch('/api/health').then(json);
export const getScenarios = (persona) => fetch(`/api/scenarios?persona=${persona}`).then(json);
export const getDashboard = (name, filters) => {
  const q = filters && Object.keys(filters).length ? `?filters=${encodeURIComponent(JSON.stringify(filters))}` : '';
  return fetch(`/api/dashboards/${name}${q}`).then(json);
};
export const getQueue = () => fetch('/api/queue').then(json);
export const decideQueue = (id, decision, decidedBy) =>
  fetch(`/api/queue/${id}/${decision}`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ decided_by: decidedBy }),
  }).then(json);
export const getAudit = () => fetch('/api/audit').then(json);
export const getDocuments = () => fetch('/api/documents').then(json);
export const getDataTables = () => fetch('/api/data/tables').then(json);
export const getDataRows = (table, offset = 0, limit = 50, search = '') =>
  fetch(`/api/data/${table}?offset=${offset}&limit=${limit}&search=${encodeURIComponent(search)}`).then(json);

/**
 * Stream a chat turn. The backend answers NDJSON: {type:"step"...} events while the
 * agents work, then one {type:"final"...} payload. onEvent fires per line.
 */
const STREAM_IDLE_MS = 75000;   // last-resort client guard; the server watchdog fires first

export async function streamChat({ message, sessionId, persona, scenarioId }, onEvent) {
  const ctrl = new AbortController();
  let idle = setTimeout(() => ctrl.abort(), STREAM_IDLE_MS);
  const touch = () => { clearTimeout(idle); idle = setTimeout(() => ctrl.abort(), STREAM_IDLE_MS); };
  let res;
  try {
    res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message, session_id: sessionId, persona, scenario_id: scenarioId || null,
      }),
      signal: ctrl.signal,
    });
  } catch (e) {
    clearTimeout(idle);
    throw new Error(e.name === 'AbortError' ? 'no response from the agent for 75 s, Gemini may be saturated; try again or use a scenario chip' : e.message);
  }
  if (!res.ok || !res.body) { clearTimeout(idle); throw new Error(`chat failed: ${res.status}`); }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = '';
  for (;;) {
    let chunk;
    try { chunk = await reader.read(); } catch (e) {
      clearTimeout(idle);
      throw new Error(e.name === 'AbortError' ? 'the agent went silent for 75 s, Gemini may be saturated; try again or use a scenario chip' : e.message);
    }
    const { done, value } = chunk;
    if (done) { clearTimeout(idle); break; }
    touch();
    buf += decoder.decode(value, { stream: true });
    const lines = buf.split('\n');
    buf = lines.pop();
    for (const line of lines) {
      if (!line.trim()) continue;
      try { onEvent(JSON.parse(line)); } catch { /* skip malformed line */ }
    }
  }
  if (buf.trim()) {
    try { onEvent(JSON.parse(buf)); } catch { /* ignore */ }
  }
}

export const getStoryHero = () => fetch('/api/story/hero').then(json);
export const getPatient = (id) => fetch(`/api/patient/${id}`).then(json);

export const getModelEval = (t = 0.12) => fetch(`/api/evals/model?threshold=${t}`).then(json);
export const getAgentEval = () => fetch('/api/evals/agent').then(json);
export const runAgentEval = (mode = 'auto') => fetch(`/api/evals/agent/run?mode=${mode}`, { method: 'POST' }).then(json);
export const getAgentEvalStatus = () => fetch('/api/evals/agent/status').then(json);
export const getLlmSelection = () => fetch('/api/evals/llm').then(json);
export const getGovernance = () => fetch('/api/evals/governance').then(json).then((d) => d.controls);

// ── What-if simulator ──
export const getSimPatients = (q = '') => fetch(`/api/simulate/patients?q=${encodeURIComponent(q)}`).then(json);
export const getSimBaseline = (id) => fetch(`/api/simulate/baseline/${encodeURIComponent(id)}`).then(json);
export const getSimPreset = (id, preset) => fetch(`/api/simulate/preset/${encodeURIComponent(id)}/${preset}`).then(json);
export const postSimulate = (patientId, overrides, signal) =>
  fetch('/api/simulate', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ patient_id: patientId, overrides }), signal,
  }).then(json);

/** Stream the Gemini explanation of a what-if: NDJSON {type:meta|token|final}. */
export async function streamExplain({ patientId, overrides, actor }, onEvent, signal) {
  const res = await fetch('/api/simulate/explain', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ patient_id: patientId, overrides, actor: actor || 'clinician' }), signal,
  });
  if (!res.ok || !res.body) throw new Error(`explain failed: ${res.status}`);
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = '';
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const lines = buf.split('\n');
    buf = lines.pop();
    for (const line of lines) {
      if (!line.trim()) continue;
      try { onEvent(JSON.parse(line)); } catch { /* partial line */ }
    }
  }
  if (buf.trim()) { try { onEvent(JSON.parse(buf)); } catch { /* ignore */ } }
}
