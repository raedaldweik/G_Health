# Nabd (نبض) — The Demo Storyline, v2

> Google Cloud **AI Customer Engineer** final round · 45 minutes = 30 demo + 15 Q&A.
> This is the choreography: what's on screen, what you say, and why each beat exists.
> Verified against the live product on 2026-09-07. Every number below is computed by the
> app at click time — re-check them the morning of the interview.

---

## 0. What the panel must walk away believing

1. **You think like a CE.** You started from a real regional customer's problem, not from a model.
2. **You build for real.** Real HIE shape, real trained models, real multi-agent orchestration, real MCP — nothing mocked, every claim traceable.
3. **You found a gap in Google's own stack and filled it** — and you can say exactly what already exists, which is the credibility test.

Everything else is supporting detail. If time collapses, protect these three.

---

## 1. Cold open — 60 seconds, landing page on screen

> *Don't introduce yourself first. Let the pulse line draw across the screen, then:*

"It's a Tuesday morning in Doha. Four thousand people with diabetes and heart disease woke up in this registry.
Six hundred and forty-two of them are at very high cardiovascular risk and are not on a statin.
Fifty-eight have atrial fibrillation and no anticoagulant. Nobody is looking for them —
because the Health Information Exchange can find *a* patient, but it can't find *those* patients.

I'm Raed. This is Nabd — the Arabic word for *pulse* — and it is what happens when you put Google's
agentic stack on top of a national exchange and simply let a clinician **ask**."

*(Point at the counters as they finish counting up. Then click **Open the Assistant**.)*

---

## 2. The customer — 2 minutes, stay on the landing page

- **Qatar**: ~17% adult diabetes prevalence; cardiometabolic disease dominates cost and mortality.
  The **National Health Strategy 2024–2030** makes population health a pillar.
- **QHIE already exists** — records are aggregated nationally. The data is not the problem.
- **The gap is intelligence**: the exchange is a record locator, not a reasoning layer. Nobody can ask
  *"who is falling through the cracks, and what should we do?"*
- **Google Cloud opened Doha (me-central1) in 2023.** Sovereign home for exactly this workload.
  Patient data never leaves Qatar. *(Say the region name; it signals you know the map.)*

> Positioning line: **"We're not replacing QHIE. We're the agentic intelligence layer on top of it,
> on sovereign Google infrastructure."**

---

## 3. Architecture — 2 minutes, scroll to the agent constellation

Point at the diagram; name the pieces as they pulse:

- **Gemini supervisor on the Agent Development Kit** — plans, routes, never guesses.
- **Cohort agent** → structured queries over the HIE (the BigQuery stand-in).
- **Guideline agent** → grounded RAG over the MOPH clinical guidelines, page-level citations.
- **Risk agent** → four real models: XGBoost risk (AUC 0.853), segments, similarity, demand forecast.
- **Population-health agent ★** → talks over **MCP** to a server we built — *"hold that thought, that's the reveal."*
- **Action agent** → drafts to a human-in-the-loop queue. Nothing reaches an EMR without a signature.

One line on currency: *"This runs on the Gemini Enterprise Agent Platform — what Google called
Vertex AI until May."* Knowing the rename is a small flex; don't dwell.

---

## 4. Act I — Angelica (clinician persona, ~8 minutes)

Persona: **Dr. Amal Al-Mansoori**, Consultant Endocrinologist. The audience follows one patient.

| Click | What appears | What you say |
|---|---|---|
| **C1 Morning panel briefing** | Live trace: cohort → risk → pop-health MCP; a table of the five highest-risk patients; a 3D chart of open gaps | *"This ran at 6am, not on my command. Watch the agents — every hop is on the record."* Point at the trace. |
| **C2 Patient deep-dive + draft Rx** | **Angelica Bautista**, 55, Filipino, Umm Ghuwailina HC. T1DM, prior stroke, PAD. HbA1c **8.7**, LDL **4.28**, BP **156/92**, ASCVD **51%** — on **aspirin alone**. Model risk **48%**, drivers: LDL, HbA1c, established CVD. Guideline citation. **Atorvastatin 40mg drafted.** Her 36-month HbA1c trajectory as a chart. | *"The registry never flagged her. The model did — and it tells me why: it's her LDL. The guideline page is right there. And nothing was prescribed: it's in my queue."* **This is the emotional centre of the demo. Slow down.** |
| Click a **citation chip** | The retrieved guideline passage + link to the PDF page | *"The agent doesn't memorise medicine. It retrieves the page at query time. Swap the PDF, no retraining."* |
| Open the **agent trace** | 4 steps · 4 agents, with args and results | *"FHIR read → model score → guideline retrieval → draft. Auditable end to end."* |
| **C3 Statin gap panel** | 642 patients; counterfactual: re-score all 629 eligible with statins → **17.7% relative risk reduction, ≈57 events avoided over 24 months, net QAR 1.1M**; recall campaign drafted | *"This is not a canned number. The eligible cohort was re-scored through the same model with the therapy applied. That's what a what-if should mean."* |
| **Queue tab** | Angelica's statin draft, unsigned. Approve it. | *"The agent is an assistant, not an actor. I sign."* The approval lands in the Audit trail — show it later. |

Skip **C4 (AF gap)** unless you're ahead of time — it's a strong backup.

---

## 5. Act II — the ministry (executive persona, ~7 minutes)

Switch persona to **Dr. Khalid Al-Kuwari**, Population Health Executive. Same platform, different altitude.

| Click | What appears | What you say |
|---|---|---|
| **Dashboards → Overview** | KPI strip; HbA1c trend **falling 7.65 → 7.3 over 36 months**; demand forecast **+4.6%**; 3D facility benchmark; risk pyramid | *"Every number here is the same query the assistant runs. One source of truth — the briefing and the conversation can never disagree."* |
| **E1 National picture** (chat) | Facility spread: Mesaimeer 52% controlled vs Hazm Mebaireek 28% | *"Twenty-four points between facilities. That's an operational lever, not a clinical mystery."* |
| **E3 Policy simulation** | Four interventions, 24 months, ranked by net benefit; combined view | *"Statins and anticoagulation pay for themselves. The GLP-1 programme, at list price, does not within 24 months — and I'd rather the model tell the minister that than a slide."* **Honest analytics is a feature.** |
| **E4 Equity** | Mean HbA1c by nationality — Bangladeshi 7.7% vs Qatari 7.1% | *"That gradient tracks access, not biology. Multilingual outreach is the cheapest lever on the board — and it's a National Health Strategy pillar."* |
| **Dashboards → Geography** | The facility map: 18 facilities sized by patients, coloured sand→maroon, gold rings on the 8 flagged ones — **Al Shamal and Al Khor in the north, Hazm Mebaireek in the Industrial Area**. Toggle Qatar → Greater Doha. Click Hazm Mebaireek → its profile (26.8% controlled, highest expat share). | *"Control is a Doha phenomenon. The further from the capital — and the closer to the Industrial Area where the workforce lives — the worse it gets. Distance and the equity gradient are the same line. That's a bus route and a clinic-hours decision, not a drug."* **Then ask the assistant** *"Show me the statin gap on a map"* — the agent draws the same map inside the chat. |
| **Dashboards → Risk & Models** | AUC 0.853 vs legacy 0.774; calibration curve; feature importance; governance cards | *"Four models, versioned, with cards. Click one — intended use, limitations, and what it becomes on Google Cloud."* |

Keep **E5 forecast / E6 quality scorecard** in reserve; the scorecard is the natural bridge to Act III.

---

## 6. Act III — the reveal (~5 minutes)

> Run **E6 Quality scorecard (MCP)** or C3 again and let the trace show the `pophealth_agent` hop.

"Everything the population-health agent just did went over the **Model Context Protocol** to a server
we built. Here's why that matters.

Google now ships more than fifty managed MCP servers. The MCP Toolbox has an official `cloud-healthcare`
source — fifteen tools that **read** FHIR: one patient, one store. And since June, the Agent Platform has
its own MCP server that can **call** any ML endpoint. I used both patterns.

But nowhere — not in Google's catalogue, not in the community — is there an MCP server that lets an agent
reason about a **population**: quality measures, care gaps, cohorts, model-backed stratification,
counterfactual policy, and a *safe* way to act. So we built it. Seven tools. Any MCP client."

*(Switch to a terminal with Gemini CLI, `compute_quality_measure NABD-CV-01` — same server, different client.)*

"And this is the part of the job description I care about most: **improve product offerings by feeding
back to Product and Engineering.** This gap analysis is a memo I'd send to the Healthcare API PM on day one."

---

## 7. Free-form + trust — ~4 minutes

- Ask the panel for a question, or type: *"Which facility has the worst BP control among high-risk Qatari
  patients, show me a chart, and what does the guideline say?"* — three agents fire, a 3D chart renders,
  a citation appears. *Kills the "it's scripted" objection.*
- **Audit tab**: point at `CONSENT·DENY` if one exists (ask about patient **QH-1000xx** with restricted consent
  to force one), the `ML·SCORE` entries, and Dr. Al-Mansoori's `HITL·APPROVED` from Act I.
- One sentence on evaluation: *"We regression-test the agent's tool trajectory, not just its words —
  ADK eval sets, and the Gen AI Evaluation Service as the judge."* *(Build the evalset before demo day.)*

---

## 8. Close — 2 minutes

Back to the landing page, scroll to **Built on Google Cloud**:

"Phase 1 is what you saw. Phase 2 is the same contracts on Google-native services: the cohort agent
becomes BigQuery over a streamed Cloud Healthcare API FHIR store; the risk model becomes BigQuery ML
registered into the Model Registry and served on an endpoint, scored through the official `/mcp/predict`
toolset; the forecast becomes `AI.FORECAST` on TimesFM; the guideline corpus becomes RAG Engine; the
agents run on Agent Engine with A2A between them; all of it in me-central1.

I built this in the shape of the job: understand the customer, build on the portfolio, find the gap,
prototype the fix, hand it to the team that ships it."

Stop talking. Let them ask.

---

## 9. Q&A bank — the 15 minutes

**Data & realism**
- *Is the data real?* — No: 4,000 synthetic patients, zero PHI, but the *shape* is real — 8 relational tables, LOINC/ICD-10/SNOMED/ATC-coded, 36 months longitudinal, FHIR R4 export. The architecture is production-shaped.
- *Why 4,000?* — Big enough for models to be honest (AUC on a 1,000-patient hold-out), small enough to run on one container. BigQuery removes the ceiling in phase 2.

**ML**
- *Why XGBoost, not a deep model?* — Tabular clinical data at this scale; explainability via SHAP contributions is non-negotiable for clinicians; BigQuery ML has the same estimator, so phase 2 is a `CREATE MODEL`.
- *How do you know 0.853 isn't overfit?* — Held-out 25%, stratified; calibration by decile is on the dashboard; the Bayes ceiling on this synthetic generator is ~0.89, so we're in the honest zone.
- *Is the counterfactual causal?* — No — it's a model-based what-if with stated assumptions (event cost QAR 32k, therapy costs from the med table). It ranks levers; a trial confirms them. I'd say that to a minister too.

**Agents & MCP**
- *Why ADK over LangGraph/CrewAI?* — Native Gemini function-calling, `McpToolset` as a first-class MCP client, A2A built in, Agent Engine as the managed runtime. Same graph deploys to phase 2 unchanged.
- *Why not just use Google's healthcare MCP tools?* — I do. Ours sits above them: population reasoning, not record retrieval. I can list exactly what theirs cover.
- *How do you stop hallucinated clinical advice?* — Numbers only come from tools; recommendations only with a citation; actions only via the queue. Then eval: trajectory tests + LLM-judge. Then Model Armor on the runtime.
- *Latency?* — Each specialist is a Gemini Flash call; a typical clinician question is 3–5 tool hops. Streaming the trace makes the wait feel like work, not delay.

**Google-specific**
- *What changed at Next '26?* — Vertex AI became the Gemini Enterprise Agent Platform; 50+ managed MCP servers went GA; Agent Engine sessions/memory GA'd. Firebase Studio is sunsetting → AI Studio Build.
- *What's deprecated that you avoided?* — MedLM (Sept 2025), Healthcare NL API (May 2026), Healthcare Data Engine (Sept 2025), Gemini 2.5 (retiring Oct 2026). Gemini + MedGemma is the current medical story.
- *Sovereignty?* — Data at rest in me-central1; open-weight MedGemma can run in-region for the clinical-language pieces; documented processing locations for anything that can't yet.

**Judgment**
- *What would you cut?* — The forecast. It's the weakest model and the least surprising insight. I'd trade it for the AF anticoagulation loop, which saves strokes.
- *What worries you?* — Adoption, not accuracy. The queue exists so clinicians own the decision; the equity view exists so the ministry owns the gap. Tools don't change outcomes; workflows do.

---

## 10. Demo-day checklist

- [ ] Railway deploy green; `/api/health` returns `mode: multi-agent` with a live model name.
- [ ] Run **C2** once at home the morning-of: confirm Angelica is still the hero (`/api/story/hero`) and her numbers match this doc.
- [ ] `FORCE_SCENARIOS=false`; keep the URL with `=true` in a second tab as the parachute.
- [ ] Gemini CLI configured with the MCP server (`backend/pophealth_mcp/README.md`); test one call.
- [ ] Clear the queue and audit trail (`backend/data/runtime/*.json`) so the panel sees only today's story — or leave Dr. Al-Mansoori's one approval for the audit beat.
- [ ] Chrome, 1600×900 or wider, zoom 100%; mic permission granted for the voice moment (EN/AR toggle).
- [ ] Open the Geography tab once before the demo so the map tiles are cached (the outline and circles render even offline).
- [ ] Two laptops or a phone hotspot. The scripted engine works with zero internet after load.

## 11. Failure playbook

| If… | Then… |
|---|---|
| Gemini errors mid-scenario | Nothing to do — the backend falls back to the scripted engine automatically and says so in the trace. Keep talking. |
| Free-form question goes sideways | *"Let me show you the trace of why"* — the details view turns a miss into a transparency beat. Then run a chip. |
| Wi-Fi dies | Scripted mode needs no API; every chip still computes live from the data. |
| A number differs from this doc | Read the screen, not the doc. The screen is the truth; that's the point. |
| They interrupt with a deep question | Answer it, then say *"and that's exactly what the next click shows"* — every act has a natural re-entry. |

## 12. Wow inventory — what makes a technical panel lean forward

1. The **pulse line and count-up** in the first 10 seconds.
2. The **live agent trace** streaming while Gemini works — six agents visibly collaborating.
3. **Angelica** — a named person, a real explanation, a real draft, a real signature.
4. The **3D charts and the facility map** rendered *by the agent* inside a chat answer.
5. **Counterfactual policy** that admits one intervention doesn't pay.
6. **AUC 0.853 vs 0.774** with a calibration curve — real ML, defended.
7. The **MCP reveal** with the exact inventory of what Google already ships.
8. The **same MCP server answering Gemini CLI**.
9. **Arabic voice input** — one click, one question, in the customer's language.
10. The **audit trail** carrying the whole story you just told.
