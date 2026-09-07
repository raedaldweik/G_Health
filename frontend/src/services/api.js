const json = async (res) => {
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
};

export const getHealth = () => fetch('/api/health').then(json);
export const getScenarios = (persona) => fetch(`/api/scenarios?persona=${persona}`).then(json);
export const getDashboard = (name) => fetch(`/api/dashboards/${name}`).then(json);
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
export async function streamChat({ message, sessionId, persona, scenarioId }, onEvent) {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message, session_id: sessionId, persona, scenario_id: scenarioId || null,
    }),
  });
  if (!res.ok || !res.body) throw new Error(`chat failed: ${res.status}`);
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
      try { onEvent(JSON.parse(line)); } catch { /* skip malformed line */ }
    }
  }
  if (buf.trim()) {
    try { onEvent(JSON.parse(buf)); } catch { /* ignore */ }
  }
}
