/* Nabd — customer-engineering deck. Google Cloud visual language: white canvas, big left-aligned
   headlines, four-colour icon circles as the motif, light-grey cards, architecture boxes with
   thin outlines grouped in dashed regions. 8 slides + speaker notes. */
const pptxgen = require('pptxgenjs');
const React = require('react');
const RDS = require('react-dom/server');
const sharp = require('sharp');
const md = require('react-icons/md');

const INK = '202124', GREY = '5F6368', FAINT = '9AA0A6', LINE = 'DADCE0', CARD = 'F8F9FA', CARD2 = 'F1F3F4';
const BLUE = '4285F4', RED = 'EA4335', YELLOW = 'FBBC04', GREEN = '34A853', BLUE2 = '1A73E8';
const LBLUE = 'E8F0FE', LGREEN = 'E6F4EA', LYELLOW = 'FEF7E0', LRED = 'FCE8E6';
const FONT = 'Arial';

async function icon(name, color = 'FFFFFF', size = 256) {
  const Comp = md[name];
  if (!Comp) throw new Error('no icon ' + name);
  const svg = RDS.renderToStaticMarkup(React.createElement(Comp, { color: '#' + color, size }));
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return 'image/png;base64,' + buf.toString('base64');
}

const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE';            // 13.33 x 7.5
pres.author = 'Raed Aldweik';
pres.title = 'Nabd — Diabetes population health on Google Cloud';

const T = (s, text, x, y, w, h, o = {}) => s.addText(text, {
  x, y, w, h, fontFace: FONT, fontSize: 12, color: INK, margin: 0, isTextBox: true, valign: 'top', ...o,
});
const rect = (s, x, y, w, h, fill, line = null, r = 0.08) => s.addShape(pres.ShapeType.roundRect, {
  x, y, w, h, fill: { color: fill }, line: line ? { color: line, width: 0.75 } : { color: fill, width: 0 }, rectRadius: r,
});
const dashed = (s, x, y, w, h, color = LINE) => s.addShape(pres.ShapeType.roundRect, {
  x, y, w, h, fill: { color: 'FFFFFF', transparency: 100 }, line: { color, width: 1, dashType: 'dash' }, rectRadius: 0.12,
});
const circle = (s, x, y, d, fill) => s.addShape(pres.ShapeType.ellipse, { x, y, w: d, h: d, fill: { color: fill }, line: { color: fill, width: 0 } });
async function iconCircle(s, x, y, d, fill, name) {
  circle(s, x, y, d, fill);
  const pad = d * 0.24;
  s.addImage({ data: await icon(name, 'FFFFFF'), x: x + pad, y: y + pad, w: d - 2 * pad, h: d - 2 * pad });
}
const arrow = (s, x1, y1, x2, y2, color = GREY, dash = null) => {
  const o = { x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1), h: Math.abs(y2 - y1),
    line: { color, width: 1.25, endArrowType: 'triangle', ...(dash ? { dashType: dash } : {}) } };
  if (x2 < x1) o.flipH = true;
  if (y2 < y1) o.flipV = true;
  s.addShape(pres.ShapeType.line, o);
};
const dots = (s, x, y, d = 0.14, gap = 0.08) => [BLUE, RED, YELLOW, GREEN].forEach((c, i) => circle(s, x + i * (d + gap), y, d, c));
const headline = (s, text, sub = null) => {
  T(s, text, 0.6, 0.5, 12.1, 0.95, { fontSize: 26, bold: true, color: INK, lineSpacingMultiple: 1.05 });
  if (sub) T(s, sub, 0.6, 1.42, 12.1, 0.35, { fontSize: 13, color: GREY });
};
const footer = (s, n, note = 'Nabd نبض · Ministry of Public Health, Qatar · Google Cloud Customer Engineering') => {
  T(s, note, 0.6, 7.05, 10, 0.25, { fontSize: 8.5, color: FAINT });
  T(s, String(n), 12.2, 7.05, 0.5, 0.25, { fontSize: 8.5, color: FAINT, align: 'right' });
};
/* product / component box for architecture diagrams */
async function pbox(s, x, y, w, h, title, sub, { fill = 'FFFFFF', line = LINE, ic = null, icColor = BLUE, titleColor = INK, fs = 10.5, subFs = 8.5 } = {}) {
  rect(s, x, y, w, h, fill, line, 0.06);
  let tx = x + 0.12, tw = w - 0.2;
  if (ic) {
    s.addImage({ data: await icon(ic, icColor), x: x + 0.12, y: y + 0.11, w: 0.26, h: 0.26 });
    tx = x + 0.46; tw = w - 0.54;
  }
  T(s, title, tx, y + 0.08, tw, sub ? 0.3 : h - 0.16, { fontSize: fs, bold: true, color: titleColor, valign: sub ? 'top' : 'middle' });
  if (sub) T(s, sub, x + 0.12, y + 0.36, w - 0.2, Math.max(h - 0.4, 0.2), { fontSize: subFs, color: titleColor === 'FFFFFF' ? 'FFFFFF' : GREY, lineSpacingMultiple: 1.05 });
}
const label = (s, text, x, y, w, color = GREY) => T(s, text.toUpperCase(), x, y, w, 0.22, { fontSize: 8.5, bold: true, color, charSpacing: 1.5 });

(async () => {
  /* ───────────────────────── 1. Title ───────────────────────── */
  {
    const s = pres.addSlide();
    s.background = { color: 'FFFFFF' };
    dots(s, 0.6, 0.62, 0.2, 0.1);
    T(s, 'Google Cloud  ·  Customer Engineering', 1.85, 0.6, 8, 0.3, { fontSize: 11, color: GREY });
    T(s, 'Nabd', 0.6, 1.9, 6, 1.0, { fontSize: 54, bold: true, color: INK });
    T(s, 'نبض', 2.55, 1.98, 3, 1.0, { fontSize: 44, color: BLUE2 });
    T(s, 'Diabetes population health,\nmade intelligible.', 0.6, 3.0, 9, 1.6, { fontSize: 34, bold: true, color: INK, lineSpacingMultiple: 1.05 });
    T(s, 'From the diabetes registry to agentic AI on Google Cloud — a proposal for the Ministry of Public Health, Qatar', 0.6, 4.75, 8.6, 0.7, { fontSize: 15, color: GREY, lineSpacingMultiple: 1.15 });
    T(s, 'Raed Aldweik  ·  AI Customer Engineer  ·  September 2026', 0.6, 6.55, 8, 0.3, { fontSize: 11, color: GREY });
    // motif: a soft four-colour "pulse" of circles on the right
    const cs = [[10.2, 2.2, 1.9, BLUE], [11.55, 3.55, 1.25, RED], [9.55, 4.05, 1.0, YELLOW], [10.75, 4.7, 1.55, GREEN]];
    cs.forEach(([x, y, d, c]) => s.addShape(pres.ShapeType.ellipse, { x, y, w: d, h: d, fill: { color: c, transparency: 12 }, line: { color: c, width: 0 } }));
    s.addNotes('Open with the customer, not the product. "MOPH already has a diabetes registry and a predictive program. What I want to show is the next step: letting any clinician or director ask the exchange a question and get an answer that is grounded, governed and actionable." Then set expectations: 8 slides, then 20 minutes in the live product.');
  }

  /* ───────────────────────── 2. The problem ───────────────────────── */
  {
    const s = pres.addSlide();
    headline(s, 'Qatar carries one of the world\'s heaviest diabetes burdens — and the system still sees it one patient at a time.');
    const stats = [
      ['Top 5', 'global diabetes prevalence among adults (IDF Diabetes Atlas)', BLUE],
      ['QR 1.8bn → 5bn', 'annual cost of diabetes care, 2015 → 2035 projection (National Diabetes Strategy)', RED],
      ['50%', 'of all dialysis in Qatar is attributable to diabetes; ~70% of stroke patients have diabetes or pre-diabetes', YELLOW],
    ];
    stats.forEach(([n, d, c], i) => {
      const x = 0.6 + i * 4.1;
      rect(s, x, 1.75, 3.9, 1.55, CARD);
      T(s, n, x + 0.25, 1.9, 3.5, 0.65, { fontSize: n.length > 6 ? 26 : 34, bold: true, color: c, valign: 'middle' });
      T(s, d, x + 0.25, 2.6, 3.45, 0.62, { fontSize: 10.5, color: GREY, lineSpacingMultiple: 1.1 });
    });
    label(s, 'What clinicians and the ministry told us', 0.6, 3.65, 6);
    const pains = [
      ['MdOutlineGroups', BLUE, 'The patient story is fragmented', '18+ facilities, an HIE with eight relational tables, and guidelines in PDFs. A 360° view exists only after someone builds it.'],
      ['MdOutlineWarningAmber', RED, 'Care is reactive', 'Risk is recognised at the admission, not before it. The registry can describe the population; it cannot yet tell a nurse who to call this morning.'],
      ['MdOutlineChat', GREEN, 'Insight is slow and rationed', 'A director\'s question becomes an analyst\'s week. A clinician cannot ask at all. Dashboards answer the questions someone anticipated.'],
    ];
    for (let i = 0; i < pains.length; i++) {
      const [ic, c, h, d] = pains[i]; const x = 0.6 + i * 4.1;
      await iconCircle(s, x, 4.0, 0.55, c, ic);
      T(s, h, x + 0.72, 4.02, 3.2, 0.3, { fontSize: 14, bold: true, color: INK });
      T(s, d, x, 4.72, 3.85, 1.6, { fontSize: 11.5, color: GREY, lineSpacingMultiple: 1.2 });
    }
    T(s, 'Sources: IDF Diabetes Atlas country profile (Qatar); Qatar National Diabetes Strategy 2016–2022 and MOPH cost projections reported by Gulf Times.', 0.6, 6.6, 12, 0.3, { fontSize: 8.5, color: FAINT });
    footer(s, 2);
    s.addNotes('Anchor on three numbers, then move quickly to the three pains — those are the customer\'s words, not ours. The key line: "the registry can describe the population; it cannot yet tell a nurse who to call this morning." That sentence is the gap the rest of the deck closes.');
  }

  /* ───────────────────────── 3. From registry to intelligence ───────────────────────── */
  {
    const s = pres.addSlide();
    headline(s, 'The journey MOPH is already on — and the step we propose', 'Each stage keeps what the previous one built. Nothing is thrown away.');
    const stages = [
      ['01', 'Registry', 'Describe', BLUE, 'MdOutlineDashboard',
        'Diabetic patient summary, geography of visits, cohorts by nationality and age — the North Carolina and Emirates Health Services pattern.',
        ['Who: analysts, planners', 'Answers: how many, where, who']],
      ['02', 'Predictive program', 'Anticipate', YELLOW, 'MdOutlineAutoGraph',
        'Deterioration prediction, high- vs low-risk profiles, visit forecasting with confidence bands, cost impact — the SAS Viya diabetes program.',
        ['Who: care managers, finance', 'Answers: who will deteriorate, what it will cost']],
      ['03', 'Agentic', 'Ask and act', GREEN, 'MdSmartToy',
        'Any clinician or director asks in plain language. Agents query the exchange, cite the national guideline, run the models, and draft actions a human signs.',
        ['Who: every clinician, every director', 'Answers: the question nobody anticipated']],
    ];
    for (let i = 0; i < stages.length; i++) {
      const [num, name, verb, c, ic, d, meta] = stages[i]; const x = 0.6 + i * 4.1;
      rect(s, x, 1.95, 3.9, 3.6, i === 2 ? LGREEN : CARD);
      await iconCircle(s, x + 0.25, 2.2, 0.6, c, ic);
      T(s, num, x + 1.0, 2.2, 1, 0.25, { fontSize: 10, bold: true, color: c, charSpacing: 2 });
      T(s, name, x + 1.0, 2.42, 2.7, 0.4, { fontSize: 18, bold: true, color: INK });
      T(s, verb, x + 0.25, 3.0, 3.4, 0.3, { fontSize: 12, bold: true, color: c });
      T(s, d, x + 0.25, 3.35, 3.4, 1.6, { fontSize: 11.5, color: GREY, lineSpacingMultiple: 1.2 });
      T(s, meta.map((m, k) => ({ text: m, options: { breakLine: k < meta.length - 1 } })), x + 0.25, 4.75, 3.4, 0.7, { fontSize: 10.5, color: INK, lineSpacingMultiple: 1.3 });
      if (i < 2) arrow(s, x + 3.92, 3.75, x + 4.08, 3.75, GREY);
    }
    T(s, [{ text: 'What changes: ', options: { bold: true, color: INK } }, { text: 'from dashboards people must find, to answers people can ask for — with the same rigour, the same models, and a human signature on every action.', options: { color: GREY } }],
      0.6, 5.9, 12.1, 0.5, { fontSize: 12.5 });
    footer(s, 3);
    s.addNotes('This is the "we respect what you built" slide. Stage 1 and 2 are literally what the panel saw in the SAS program: patient summary, prediction, risk profiles, visit forecasts. Stage 3 is the proposal. Stress "nothing is thrown away": the models and the registry become tools the agent calls.');
  }

  /* ───────────────────────── 4. Solution overview ───────────────────────── */
  {
    const s = pres.addSlide();
    headline(s, 'Nabd: one conversation over the HIE, the guidelines and the models', 'The same four capabilities as the diabetes program — now available to anyone who can ask.');
    const caps = [
      ['MdPerson', BLUE, 'Diabetic patient 360', 'Summary, HbA1c trajectory, comorbidities, medications, open care gaps — assembled on request, with consent enforced.'],
      ['MdOutlineAutoGraph', YELLOW, 'Risk stratification & visit prediction', 'Explainable risk of a 12-month complication, cohort bands, similar patients, and demand forecasts for planning.'],
      ['MdMenuBook', RED, 'Guideline-grounded decision support', 'Recommendations retrieved from MOPH national guidelines and cited to the page. No clinical claim without a source.'],
      ['MdQueryStats', GREEN, 'Population & cost simulation', 'Control rates, care gaps and cost by facility and nationality; what-if simulation of interventions before money is spent.'],
    ];
    for (let i = 0; i < caps.length; i++) {
      const [ic, c, h, d] = caps[i]; const x = 0.6 + (i % 2) * 3.55, y = 1.95 + Math.floor(i / 2) * 2.2;
      rect(s, x, y, 3.35, 2.0, CARD);
      await iconCircle(s, x + 0.22, y + 0.22, 0.5, c, ic);
      T(s, h, x + 0.85, y + 0.24, 2.4, 0.5, { fontSize: 12.5, bold: true, color: INK, lineSpacingMultiple: 1.0 });
      T(s, d, x + 0.22, y + 0.85, 2.95, 1.1, { fontSize: 10.5, color: GREY, lineSpacingMultiple: 1.2 });
    }
    // right: trust column
    rect(s, 8.0, 1.95, 4.7, 4.2, LBLUE);
    T(s, 'Trustworthy by design', 8.3, 2.15, 4.2, 0.35, { fontSize: 14, bold: true, color: BLUE2 });
    const rules = [
      ['MdOutlineFactCheck', 'Numbers only from tools', 'the model narrates; it never invents a value'],
      ['MdOutlineDescription', 'Claims only with a citation', 'document and page from the national guideline'],
      ['MdOutlineHowToReg', 'Actions only with a signature', 'drafts wait in a queue for a named clinician'],
      ['MdOutlineVisibility', 'Every step audited', 'tool calls, scores, citations and decisions'],
      ['MdMic', 'Arabic and English, by voice', 'ask between patients, or from the car'],
    ];
    for (let i = 0; i < rules.length; i++) {
      const [ic, h, d] = rules[i]; const y = 2.65 + i * 0.68;
      s.addImage({ data: await icon(ic, BLUE2), x: 8.3, y: y + 0.03, w: 0.3, h: 0.3 });
      T(s, h, 8.75, y, 3.9, 0.28, { fontSize: 11.5, bold: true, color: INK });
      T(s, d, 8.75, y + 0.28, 3.9, 0.3, { fontSize: 10, color: GREY });
    }
    T(s, [{ text: 'Focus for this engagement: ', options: { bold: true, color: INK } }, { text: 'type 2 diabetes, 4,000-patient synthetic exchange shaped like QHIE (FHIR R4 export, LOINC / ICD-10 / ATC coded, 36 months). Zero PHI.', options: { color: GREY } }],
      0.6, 6.4, 12.1, 0.45, { fontSize: 11 });
    footer(s, 4);
    s.addNotes('Map each tile to something the panel saw in the SAS program so it feels like continuity. Then the right column is the answer to "is this AI garbage?": four rules, all enforced in code, all visible in the demo (trace, citations, queue, audit).');
  }

  /* ───────────────────────── 5. How it works ───────────────────────── */
  {
    const s = pres.addSlide();
    headline(s, 'How it works: one supervisor, five specialists', 'Each specialist carries only the tools it needs; the supervisor plans and composes but never invents a number.');
    // user → supervisor
    rect(s, 4.9, 1.9, 3.55, 0.5, CARD2);
    s.addImage({ data: await icon('MdRecordVoiceOver', GREY), x: 5.05, y: 2.01, w: 0.28, h: 0.28 });
    T(s, '"Who on my panel needs attention today?"', 5.42, 1.9, 3.0, 0.5, { fontSize: 10.5, color: INK, valign: 'middle', italic: true });
    arrow(s, 6.67, 2.42, 6.67, 2.63);
    rect(s, 4.3, 2.65, 4.75, 0.85, BLUE);
    T(s, 'Nabd supervisor', 4.5, 2.71, 4.4, 0.35, { fontSize: 14, bold: true, color: 'FFFFFF' });
    T(s, 'Gemini 3.8 Flash on the Agent Development Kit — plans, routes, composes; never guesses a number', 4.5, 3.05, 4.4, 0.4, { fontSize: 9.5, color: 'FFFFFF' });
    const specs = [
      ['Data specialist', 'MdStorage', BLUE, 'Cohorts, timelines, group-bys over the exchange', 'HIE tables today · BigQuery in phase 2'],
      ['Guideline specialist', 'MdMenuBook', RED, 'Retrieval over MOPH guidelines with page citations', 'Hybrid search · RAG Engine in phase 2'],
      ['Risk specialist', 'MdOutlineAutoGraph', YELLOW, 'Scores, explains, forecasts, simulates', 'XGBoost risk (AUC 0.85) · segments · forecast'],
      ['Population-health MCP', 'MdHub', GREEN, 'Care gaps, quality measures, stratification', 'Nabd MCP server — the gap in Google\'s catalogue'],
      ['Action specialist', 'MdOutlineAssignmentTurnedIn', GREY, 'Drafts prescriptions, recalls, referrals', 'Human-in-the-loop approval queue'],
    ];
    for (let i = 0; i < specs.length; i++) {
      const [name, ic, c, does, via] = specs[i]; const x = 0.6 + i * 2.45, w = 2.3;
      arrow(s, 6.67, 3.5, x + w / 2, 3.92, LINE);
      rect(s, x, 3.95, w, 0.72, 'FFFFFF', LINE);
      await iconCircle(s, x + 0.12, 4.06, 0.5, c, ic);
      T(s, name, x + 0.7, 3.98, w - 0.78, 0.66, { fontSize: 11, bold: true, color: INK, valign: 'middle', lineSpacingMultiple: 1.0 });
      arrow(s, x + w / 2, 4.67, x + w / 2, 4.88, LINE);
      rect(s, x, 4.9, w, 1.25, CARD);
      T(s, does, x + 0.15, 5.0, w - 0.3, 0.65, { fontSize: 10, color: INK, lineSpacingMultiple: 1.15 });
      T(s, via, x + 0.15, 5.62, w - 0.3, 0.5, { fontSize: 9, color: c === YELLOW ? 'B06000' : c, bold: true, lineSpacingMultiple: 1.1 });
    }
    // result strip
    rect(s, 0.6, 6.3, 12.1, 0.62, LGREEN);
    s.addImage({ data: await icon('MdVerifiedUser', GREEN), x: 0.8, y: 6.46, w: 0.3, h: 0.3 });
    T(s, [{ text: 'Every answer ships with its evidence: ', options: { bold: true, color: INK } }, { text: 'the tool trace, guideline citations, model drivers and any drafted action — streamed live so the user watches the agents work. Specialists also mean least privilege (the guideline agent cannot draft a prescription) and ~30% fewer tokens per question than one flat agent.', options: { color: GREY } }],
      1.2, 6.32, 11.4, 0.6, { fontSize: 10, valign: 'middle', lineSpacingMultiple: 1.1 });
    footer(s, 5);
    s.addNotes('Walk top to bottom once: question → supervisor → specialists → tools → evidence. Pre-empt "why five agents": least privilege, independent evaluation, cheaper per question — measured in the evaluation tab. Mention that the MCP specialist is the reveal for later: Google ships MCP servers to read FHIR and query BigQuery, but none that reasons about a population; we built that one.');
  }

  /* ───────────────────────── 6. Architecture A — SAS ───────────────────────── */
  {
    const s = pres.addSlide();
    headline(s, 'Reference architecture A — SAS Viya, the federal-entity MVP', 'What was built and proven first: agentic retrieval over guidelines, structured data in CAS, tools behind an MCP server.');
    // unstructured region
    dashed(s, 0.6, 1.95, 3.1, 2.85, BLUE);
    label(s, 'Unstructured data', 0.8, 2.05, 2.8, BLUE2);
    await pbox(s, 0.8, 2.3, 2.7, 0.78, 'Clinical guidelines & policy', 'national guidelines · care protocols · policy frameworks', { ic: 'MdOutlineDescription', icColor: GREY });
    arrow(s, 2.15, 3.08, 2.15, 3.28);
    await pbox(s, 0.8, 3.3, 2.7, 0.42, 'Embedding model', null, { fill: LBLUE, line: LBLUE });
    arrow(s, 2.15, 3.72, 2.15, 3.92);
    await pbox(s, 0.8, 3.94, 2.7, 0.66, 'Vector store (RAG)', 'agentic retrieval at question time', { fill: BLUE2, line: BLUE2, titleColor: 'FFFFFF' });
    // structured region
    dashed(s, 0.6, 5.0, 3.1, 1.45, BLUE);
    label(s, 'Structured data', 0.8, 5.1, 2.8, BLUE2);
    await pbox(s, 0.8, 5.35, 2.7, 0.95, 'National HIE', 'patients · encounters · diagnoses · facilities (tabular)', { ic: 'MdStorage', icColor: GREY });
    // CAS
    await pbox(s, 4.3, 5.35, 2.7, 0.95, 'CAS table (SAS Viya)', 'in-memory analytics tables · read by the SQL tool', { ic: 'MdDataObject', icColor: BLUE2, fill: CARD, line: CARD });
    arrow(s, 3.5, 5.82, 4.3, 5.82, GREY, 'dash');
    // agent
    rect(s, 4.3, 1.95, 3.0, 2.8, BLUE);
    T(s, 'Health Analytics Agent', 4.5, 2.1, 2.7, 0.35, { fontSize: 13, bold: true, color: 'FFFFFF' });
    T(s, 'Patient-level queries, population insights, cost forecasting, policy simulation — with traceable, cited reasoning', 4.5, 2.5, 2.7, 0.9, { fontSize: 9.5, color: 'FFFFFF', lineSpacingMultiple: 1.15 });
    rect(s, 4.5, 3.5, 2.6, 1.05, 'FFFFFF');
    T(s, [{ text: 'Orchestrator', options: { bullet: true, breakLine: true } }, { text: 'Guideline grounding', options: { bullet: true, breakLine: true } }, { text: 'Audit log', options: { bullet: true } }], 4.6, 3.58, 2.4, 0.9, { fontSize: 10, color: INK, paraSpaceAfter: 2 });
    arrow(s, 3.7, 3.3, 4.3, 3.3, BLUE2);
    // MCP server
    await pbox(s, 7.75, 2.7, 1.55, 1.3, 'MCP server', 'tool gateway', { fill: LBLUE, line: LBLUE, ic: 'MdHub', icColor: BLUE2, titleColor: BLUE2 });
    arrow(s, 7.3, 3.35, 7.75, 3.35, BLUE2);
    // tools
    label(s, 'Tools', 9.75, 1.98, 3, BLUE2);
    const tools = [['Run & build ML model', 'forecasting · simulation', CARD2], ['Run decision flow', 'SAS Intelligent Decisioning', LBLUE], ['Generate charts', 'for the answer', LBLUE], ['Query data (SQL)', 'over the CAS tables', BLUE2]];
    for (let i = 0; i < tools.length; i++) {
      const [t, sub, f] = tools[i]; const y = 2.25 + i * 0.7;
      await pbox(s, 9.75, y, 2.95, 0.6, t, sub, { fill: f, line: f, titleColor: f === BLUE2 ? 'FFFFFF' : INK, subFs: 8, fs: 10 });
      arrow(s, 9.3, 3.35, 9.75, y + 0.3, BLUE2);
    }
    // delivered
    rect(s, 7.75, 5.2, 4.95, 1.25, CARD);
    T(s, 'What it delivered', 7.95, 5.28, 4.5, 0.3, { fontSize: 11.5, bold: true, color: INK });
    T(s, [{ text: 'Natural-language questions → governed analytics, cohorts and charts', options: { bullet: true, breakLine: true } }, { text: 'ML scoring, forecasting and policy simulation on demand', options: { bullet: true, breakLine: true } }, { text: 'Every answer cites national guidelines and shows its tool calls', options: { bullet: true } }],
      7.95, 5.58, 4.6, 0.85, { fontSize: 9.5, color: GREY, paraSpaceAfter: 2 });
    footer(s, 6, 'Reference: SAS Health Analytics Platform, agentic AI MVP at a federal health entity (GCC), 2025');
    s.addNotes('Credit the SAS build honestly: this is where the pattern was proven — an orchestrating agent, guideline grounding, an MCP server exposing SQL, models, decision flows and charts. Then the pivot sentence for the next slide: "the pattern is right; the question for MOPH is which platform runs it at national scale, in Doha, with managed services underneath."');
  }

  /* ───────────────────────── 7. Architecture B — Google Cloud ───────────────────────── */
  {
    const s = pres.addSlide();
    headline(s, 'Reference architecture B — Google Cloud, me-central1 (Doha)', 'The same pattern on managed services, structured as Google\'s RAG reference architecture: a data ingestion subsystem and a serving subsystem.');
    // ingestion region
    dashed(s, 0.6, 1.95, 5.95, 4.35, BLUE);
    label(s, 'Data ingestion subsystem', 0.8, 2.05, 5, BLUE2);
    const srcs = [['QHIE — FHIR R4', 'MdLocalHospital'], ['HMC · PHCC EHRs (HL7v2)', 'MdLocalHospital'], ['Claims · pharmacy (nightly)', 'MdOutlinePayments'], ['MOPH guidelines (PDF)', 'MdOutlineDescription']];
    for (let i = 0; i < srcs.length; i++) {
      await pbox(s, 0.8, 2.35 + i * 0.66, 1.95, 0.56, srcs[i][0], null, { ic: srcs[i][1], icColor: GREY, fs: 9 });
    }
    await pbox(s, 3.05, 2.35, 1.6, 1.22, 'Cloud Healthcare API', 'FHIR store · consent · de-identification · Pub/Sub events', { fill: LBLUE, line: LBLUE, fs: 9.5, subFs: 7.5 });
    await pbox(s, 4.9, 2.35, 1.45, 1.22, 'BigQuery', 'streaming export · curated marts · BigQuery ML', { fill: BLUE2, line: BLUE2, titleColor: 'FFFFFF', fs: 10, subFs: 7.5 });
    [2.63, 3.29].forEach((y) => arrow(s, 2.75, y, 3.05, y, GREY));
    arrow(s, 2.75, 3.95, 3.3, 3.95, GREY, 'dash'); arrow(s, 3.3, 3.95, 3.3, 3.57, GREY, 'dash');
    arrow(s, 4.65, 2.96, 4.9, 2.96, GREY);
    await pbox(s, 3.05, 4.35, 1.6, 0.56, 'Cloud Storage', 'versioned corpus', { fs: 9, subFs: 7.5 });
    await pbox(s, 4.9, 4.0, 1.45, 1.25, 'RAG Engine', 'embeddings · vector index · page-level citations', { fill: LBLUE, line: LBLUE, fs: 9.5, subFs: 7.5 });
    arrow(s, 2.75, 4.61, 3.05, 4.61, GREY); arrow(s, 4.65, 4.61, 4.9, 4.61, GREY);
    await pbox(s, 0.8, 5.05, 5.55, 0.98, 'Vertex AI — models', 'Pipelines train the XGBoost risk model on BigQuery data → Model Registry → online endpoint for point-of-care scoring, batch prediction for the nightly cohort; drift monitoring', { fill: CARD2, line: CARD2, ic: 'MdOutlineAutoGraph', icColor: BLUE2, fs: 9.5, subFs: 7.5 });
    // serving region
    dashed(s, 6.8, 1.95, 5.9, 4.35, GREEN);
    label(s, 'Serving subsystem', 7.0, 2.05, 5, '1E8E3E');
    await pbox(s, 7.0, 2.35, 1.65, 1.0, 'Users', 'clinicians · MOPH directors · web, tablet, voice', { ic: 'MdOutlineGroups', icColor: GREY, fs: 9.5, subFs: 7.5 });
    await pbox(s, 8.9, 2.35, 1.7, 1.0, 'Cloud Run — Nabd app', 'React + API · Speech-to-Text / TTS (Arabic, English)', { fs: 9.5, subFs: 7.5 });
    await pbox(s, 10.85, 2.35, 1.65, 1.0, 'Agent runtime', 'ADK graph · Gemini 3.8 Flash · sessions · traces', { fill: '1E8E3E', line: '1E8E3E', titleColor: 'FFFFFF', fs: 9.5, subFs: 7.5 });
    arrow(s, 8.65, 2.85, 8.9, 2.85, GREY); arrow(s, 10.6, 2.85, 10.85, 2.85, GREY);
    label(s, 'Tools the agent calls', 7.0, 3.55, 4, GREY);
    const tls = [['MCP Toolbox', 'BigQuery · FHIR (Google)'], ['Nabd pop-health MCP', 'care gaps · measures · simulation'], ['Vertex AI endpoint', 'risk score + drivers'], ['RAG Engine retrieval', 'cited guideline passages']];
    for (let i = 0; i < tls.length; i++) {
      const x = 7.0 + (i % 2) * 2.85, y = 3.8 + Math.floor(i / 2) * 0.66;
      await pbox(s, x, y, 2.7, 0.56, tls[i][0], tls[i][1], { fill: LGREEN, line: LGREEN, fs: 9, subFs: 7.5 });
    }
    arrow(s, 11.67, 3.35, 11.67, 3.78, GREY);
    await pbox(s, 7.0, 5.2, 2.7, 0.83, 'Human approval queue', 'drafts signed by a named clinician', { ic: 'MdOutlineHowToReg', icColor: GREEN, fs: 9, subFs: 7.5 });
    await pbox(s, 9.85, 5.2, 2.7, 0.83, 'Write-back', 'approved items posted as FHIR Task to the EHR via Healthcare API', { ic: 'MdOutlineAssignmentTurnedIn', icColor: GREEN, fs: 9, subFs: 7.5 });
    arrow(s, 9.7, 5.6, 9.85, 5.6, GREY);
    // ingestion → serving link
    arrow(s, 6.55, 4.35, 6.8, 4.35, BLUE2, 'dash');
    T(s, 'data & models', 6.35, 4.05, 0.85, 0.25, { fontSize: 7, color: BLUE2, align: 'center' });
    // cross-cutting
    rect(s, 0.6, 6.45, 12.1, 0.5, CARD);
    s.addImage({ data: await icon('MdOutlineLock', GREY), x: 0.78, y: 6.56, w: 0.28, h: 0.28 });
    T(s, [{ text: 'Sovereignty & operations: ', options: { bold: true, color: INK } }, { text: 'PHI at rest in me-central1 under an Assured Workloads Qatar Data Boundary · VPC Service Controls · CMEK · least-privilege service accounts · Cloud Logging & Trace · Gen AI evaluation as a release gate · the LLM only ever sees pseudonymised, aggregated data.', options: { color: GREY } }],
      1.15, 6.45, 11.5, 0.5, { fontSize: 9, valign: 'middle', lineSpacingMultiple: 1.05 });
    footer(s, 7, 'Pattern: Google Cloud Architecture Center — "RAG infrastructure for generative AI using Gemini Enterprise and Agent Platform"');
    s.addNotes('Read it left to right like Google\'s own reference: ingestion on the left (Healthcare API → BigQuery; guidelines → RAG Engine; Vertex trains and serves the risk model), serving on the right (Cloud Run app, the ADK agent on Gemini, the four tool families, the human queue, FHIR write-back). Two Doha-specific decisions to name if asked: Gemini is served from the global endpoint, acceptable because the agent only ever sees pseudonymised aggregates; and the agent runtime is Cloud Run in Doha until Agent Engine reaches me-central1. Both are architecture decisions, not accidents.');
  }

  /* ───────────────────────── 8. Roadmap + demo agenda ───────────────────────── */
  {
    const s = pres.addSlide();
    headline(s, 'Phased delivery — value at every step, and what you will see in the next 20 minutes');
    const phases = [
      ['Phase 1 · today', 'Proof of concept', BLUE, 'Running now on a 4,000-patient synthetic exchange: the agent graph, four models, the population-health MCP server, guideline RAG, the approval queue, voice, and an evaluation harness that grades the models and the agents on held-out data.'],
      ['Phase 2 · 8–12 weeks', 'Google Cloud, Doha', YELLOW, 'Same container on Cloud Run in me-central1; the exchange in BigQuery; Gemini and embeddings through Vertex AI with service-account auth; risk model on a Vertex endpoint; a QHIE test feed through the Cloud Healthcare API. Pilot at four sites.'],
      ['Phase 3 · national', 'Scale and integrate', GREEN, 'FHIR streaming from all facilities, HL7v2 bridges for legacy sites, Looker for governed KPIs, MedGemma for clinical notes, Agent Engine when it lands in Qatar, evaluation gates in CI, MOPH SSO and write-back to the EHR.'],
    ];
    for (let i = 0; i < phases.length; i++) {
      const [when, name, c, d] = phases[i]; const x = 0.6 + i * 4.1;
      rect(s, x, 1.6, 3.9, 2.55, CARD);
      T(s, when, x + 0.25, 1.75, 3.4, 0.25, { fontSize: 9.5, bold: true, color: c === YELLOW ? 'B06000' : c, charSpacing: 1.5 });
      T(s, name, x + 0.25, 2.0, 3.4, 0.4, { fontSize: 16, bold: true, color: INK });
      T(s, d, x + 0.25, 2.45, 3.4, 1.65, { fontSize: 10.5, color: GREY, lineSpacingMultiple: 1.2 });
      if (i < 2) arrow(s, x + 3.92, 2.9, x + 4.08, 2.9, GREY);
    }
    label(s, 'Demo agenda', 0.6, 4.5, 4);
    const acts = [
      ['1', BLUE, 'The clinician\'s morning', 'Dr. Amal asks for her briefing. One patient: 360 view, explained risk, the guideline passage, a draft prescription that waits for her signature.'],
      ['2', RED, 'The ministry\'s view', 'Dr. Khalid asks for the national picture: control rates, care gaps by facility and nationality, cost concentration, and a simulation of closing the SGLT2 / GLP-1 treatment gap before any money is spent.'],
      ['3', GREEN, 'Under the hood', 'The population-health MCP server answering another client, the live agent trace, and the evaluation tab: held-out model accuracy, agent evalset, cost per question.'],
    ];
    for (let i = 0; i < acts.length; i++) {
      const [n, c, h, d] = acts[i]; const x = 0.6 + i * 4.1;
      circle(s, x, 4.85, 0.5, c);
      T(s, n, x, 4.85, 0.5, 0.5, { fontSize: 16, bold: true, color: 'FFFFFF', align: 'center', valign: 'middle' });
      T(s, h, x + 0.65, 4.9, 3.2, 0.4, { fontSize: 13.5, bold: true, color: INK });
      T(s, d, x, 5.5, 3.85, 1.3, { fontSize: 10.5, color: GREY, lineSpacingMultiple: 1.2 });
    }
    T(s, 'Every number in the demo is computed live from the exchange by a tool; nothing is a slide.', 0.6, 6.75, 12, 0.3, { fontSize: 10.5, italic: true, color: INK });
    footer(s, 8);
    s.addNotes('Close the deck by making the demo the proof: three acts, twenty minutes, and the sentence "every number is computed live by a tool; nothing is a slide." Then switch to the browser. If time is short, phase 3 can be one sentence: "national scale is the same contracts on more managed services".');
  }

  await pres.writeFile({ fileName: 'Nabd_MOPH_Google_Cloud.pptx' });
  console.log('written');
})().catch((e) => { console.error(e); process.exit(1); });
