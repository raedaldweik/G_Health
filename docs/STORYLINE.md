# Population Health AI on Google Cloud — Interview Demo Storyline

> Final-round presentation for Google Cloud **AI Customer Engineer** (45 min = 30 min demo + 15 min Q&A).
> A ground-up, Google-native rebuild of the QHIE population-health demo — with real ML, real
> multi-agent orchestration, and one genuinely new contribution to the Google ecosystem.
>
> Status: **proposal for alignment** — nothing is built yet. Research verified as of 2026-09-07.

---

## 1. The one-sentence pitch

> *"An agentic population-health platform on top of Qatar's Health Information Exchange, built
> entirely on Google Cloud in the Doha region — FHIR-native data, five real machine-learning
> models, a multi-agent system with grounded RAG and human-in-the-loop safety, and the first
> population-health MCP server in the Google ecosystem."*

---

## 2. Why this storyline wins the interview

Map every beat of the demo to the job description — say these mappings out loud during the close:

| Job description asks for | Where the demo proves it |
|---|---|
| "Assembling, debugging and spinning up rapid, real-time prototypes and interactive demos" | The entire product, built in days, live on Cloud Run |
| "Showcase the art of the possible across the full Google Cloud portfolio" | Healthcare API + BigQuery + BQML + Gemini + ADK + Agent Engine + RAG Engine + Cloud Run + me-central1 |
| "LLM APIs, prompt engineering, vector databases, RAG, conversational agents" | RAG Engine citations, BigQuery VECTOR_SEARCH patient similarity, ADK multi-agent chat |
| "Improve product feature offerings by providing customer feedback to Product/Engineering" | **The MCP gap analysis + the server we built to fill it** — this is literally the CE behavior, demonstrated |
| "Communicating technical concepts clearly to different audiences" | Two-persona demo: clinician view vs. ministry-executive view of the same platform |
| "Strong debugging skills, Docker/Linux" | One-container Cloud Run deploy; mention casually |
| "English and Arabic fluently, local clients in the region" | Qatar MOPH storyline, National Health Strategy 2024–2030, Arabic roadmap beat |

The meta-message: **you didn't demo a chatbot — you did the CE job end-to-end**: understood a
regional customer, mapped their environment, built on the portfolio, found a product gap, and
prototyped the fix.

---

## 3. The customer story (minutes 0–3)

Open with the customer, not the tech:

- Qatar has one of the world's highest diabetes burdens (~17% adult prevalence); cardiometabolic
  disease dominates cost and mortality. The **National Health Strategy 2024–2030** makes
  prevention and population health a pillar.
- Qatar already runs a national **Health Information Exchange (QHIE)** under the National
  E-Health & Data Program — the data exists, aggregated, today.
- The gap: QHIE is a *record locator*, not an *intelligence layer*. Clinicians can look up one
  patient; nobody can ask *"who is falling through the cracks, and what should we do about it?"*
- Google Cloud opened the **Doha region (me-central1) in 2023** — a sovereign home for exactly
  this workload. Patient data never leaves Qatar.

> Positioning sentence: *"We're not replacing QHIE — we're the agentic intelligence layer on top
> of it, on sovereign Google infrastructure."*

**Product name options** (pick one — see §12 open decisions):
1. **Afiya** (عافية, "wellness/health") — Population Health Intelligence
2. **Nabd** (نبض, "pulse") — the national health pulse
3. Keep it descriptive: **QHIE Copilot**

---

## 4. Architecture (Google-native, minute 3–6, one slide)

```
                        ┌──────────────────────────────────────────────────────┐
                        │  React glass UI (Roads_RAM_UI aesthetic) · Cloud Run │
                        │  Chat · Dashboards · HITL Queue · Audit · Documents  │
                        └───────────────────────────┬──────────────────────────┘
                                                    │
                 ┌──────────────────────────────────▼───────────────────────────────────┐
                 │        SUPERVISOR AGENT — ADK (Python) · Gemini 3.8 Flash            │
                 │        deployed on Agent Engine (Agent Platform Runtime)             │
                 └──┬───────────┬───────────────┬───────────────┬───────────────┬──────┘
                    │           │               │               │               │
             ┌──────▼─────┐ ┌───▼─────────┐ ┌───▼──────────┐ ┌──▼───────────┐ ┌─▼──────────┐
             │ Cohort &   │ │ Guideline   │ │ Risk & ML    │ │ Care-Gap     │ │ Action     │
             │ Data Agent │ │ RAG Agent   │ │ Agent        │ │ Agent        │ │ Agent      │
             │            │ │             │ │              │ │              │ │ (HITL)     │
             │ Google's   │ │ Vertex RAG  │ │ BQML models  │ │ ★ OUR MCP    │ │ FHIR draft │
             │ official   │ │ Engine over │ │ + endpoint   │ │ SERVER ★     │ │ resources, │
             │ BigQuery   │ │ MOPH PDFs   │ │ via official │ │ (the first   │ │ approval   │
             │ MCP server │ │ (gemini-    │ │ /mcp/predict │ │ pop-health   │ │ queue,     │
             │ + Toolbox  │ │ embedding-  │ │              │ │ MCP server   │ │ audit log  │
             │ healthcare │ │ 001)        │ │              │ │ on GCP)      │ │            │
             └──────┬─────┘ └─────────────┘ └───┬──────────┘ └──┬───────────┘ └────────────┘
                    │                           │               │
        ┌───────────▼───────────────────────────▼───────────────▼───────────────────────┐
        │                     DATA & ML LAYER — me-central1 (Doha)                      │
        │  Cloud Healthcare API FHIR R4 store  ──streaming──▶  BigQuery (ANALYTICS_V2)  │
        │  BQML: risk models · TimesFM AI.FORECAST · VECTOR_SEARCH patient similarity   │
        │  Model Registry → online endpoint (real-time scoring)                          │
        └────────────────────────────────────────────────────────────────────────────────┘
```

Naming currency (say it once, casually): *"the Gemini Enterprise Agent Platform — what was
called Vertex AI until this May."* Knowing the rebrand, and knowing what died (MedLM,
Healthcare NL API, Healthcare Data Engine, Firebase Studio) is itself a credibility signal.

### What each Google product does here

| Layer | Product | Role |
|---|---|---|
| System of record | **Cloud Healthcare API — FHIR R4 store** | The 3,000-patient synthetic QHIE cohort as real FHIR resources (Patient, Condition, Observation, MedicationRequest). Consent enforcement + de-identification talking points. |
| Analytics | **BigQuery** (streaming FHIR export, ANALYTICS_V2) | Real-time SQL over FHIR with zero ETL. One source of truth for chat AND dashboards. |
| ML | **BigQuery ML + Model Registry + online endpoint** | Five real models (below). BQML `model_registry="vertex_ai"` auto-registers → one-click endpoint deploy, no serving container. |
| LLM | **Gemini 3.8 Flash** (agent loops) + **Gemini 3.1 Pro** (synthesis/judge) | 3.8 Flash is days old, agent-tuned, cheap — using it well is a flex. |
| Agents | **ADK (Python) on Agent Engine** | Real multi-agent hierarchy, sessions, memory, OTel tracing. Free tier covers the demo. |
| RAG | **Vertex AI RAG Engine** | Managed corpus over the MOPH guideline PDFs; grounded, cited answers. |
| Tools | **MCP** — Google's official servers + **ours** | See §6. |
| A2A | **ADK `RemoteA2aAgent`** | One specialist agent exposed over A2A — "MCP is agent↔tool, A2A is agent↔agent" in one line of config. |
| Eval | **ADK eval + Gen AI Evaluation Service** | Golden-session trajectory regression tests + LLM-judge scoring. |
| Serving | **Cloud Run** | One container, public URL, free tier. |
| Sovereignty | **me-central1 (Doha)** | Data at rest in Qatar. Open-weight **MedGemma 1.5** deployable in-region — roadmap beat. |

---

## 5. The ML story — five real models (no mocks this time)

The old demo's weakest link was `risk_simulate` returning hardcoded numbers. Every model below
is genuinely trained/served — and each is one SQL statement to show on screen:

| # | Model | How | Demo moment |
|---|---|---|---|
| 1 | **Complication-risk classifier** | BQML `boosted_tree_classifier` (XGBoost) on the 61-column cohort → Model Registry → **online endpoint** | Patient deep-dive: agent scores the patient in real time via the endpoint and shows `ML.EXPLAIN_PREDICT` top drivers ("her risk is driven by HbA1c 9.1, eGFR 48, 2 admissions") |
| 2 | **Statin-benefit / care-gap propensity** | BQML `logistic_reg` (interpretable coefficients) | Statin-gap scenario: rank the 494 untreated high-risk patients by expected benefit |
| 3 | **Demand forecast** | **`AI.FORECAST` (TimesFM)** — zero-training foundation-model forecasting | Executive: "forecast outpatient visits next quarter" — one SQL call, chart renders |
| 4 | **Patient similarity** | `AI.EMBED` + `CREATE VECTOR INDEX` + **`VECTOR_SEARCH`** | Clinician: "find patients like QHIE-100847 and what worked for them" |
| 5 | **Cohort segmentation** | BQML `KMEANS` on cost/risk/utilization | Executive: the four spend-risk segments behind the cost-concentration story |
| ★ | **Counterfactual policy simulation** | Re-score the cohort through model #1 with the gap closed (flip `On_Statin` for the gap cohort → aggregate predicted event reduction) | **Replaces the mocked SAS Viya simulation with real math**: "close the statin gap → X% predicted event reduction → QAR Y saved" — an honest, defensible what-if |

---

## 6. The MCP wow moment (the centerpiece)

### What the research established (verified 2026-09-07)

Google's MCP ecosystem is now big — and we use it *correctly* before we extend it:

- **50+ Google-managed remote MCP servers went GA at Next '26** (BigQuery, Cloud Run, GKE,
  Workspace, …). We consume the **official BigQuery MCP server** in the Cohort agent.
- **MCP Toolbox for Databases** has an official **`cloud-healthcare` source** (Nov 2025): 15
  read-only tools — FHIR store metadata, `get_fhir_resource`, `fhir_patient_search`,
  `fhir_patient_everything`, DICOM search. We consume these too.
- The **Agent Platform remote MCP server** (June 2026, GA) already exposes `/mcp/predict`
  (endpoint scoring), `/mcp/models` (registry), `/mcp/evaluation`… → **our original idea
  ("Vertex real-time-scoring MCP") already exists — we must not claim it.**
- Community FHIR MCP servers exist (wso2, the-momentum, …) → "first FHIR MCP" is also dead.

### The verified gap

Searched GitHub (google, googleapis, GoogleCloudPlatform orgs), PulseMCP (22k+ servers),
mcpservers.org, mcpmarket, and the Next '26 managed-server list: **zero MCP servers exist for
population-health reasoning** — care-gap detection, quality-measure computation, cohort
building, or model-backed risk stratification. Google's healthcare MCP tools stop at
single-patient reads; its ML MCP tools stop at generic plumbing.

### Our contribution: `population-health-mcp` — the first population-health MCP server on Google Cloud

| Tool | What it does | Backed by |
|---|---|---|
| `build_cohort(criteria)` | Declarative cohort from clinical criteria | BigQuery over FHIR export |
| `find_care_gaps(measure, cohort)` | Statin gap, HbA1c-overdue, retinal screening, ACR monitoring… | SQL measure library |
| `compute_quality_measure(measure_id)` | HEDIS-style numerator/denominator with drill-down | SQL measure library |
| `stratify_risk(cohort, model)` | Score a whole cohort through the deployed model | BQML / online endpoint |
| `simulate_policy(intervention, cohort)` | Counterfactual re-scoring (the real what-if) | Model #1 |
| `draft_intervention(patient_ids, action)` | Draft FHIR `Task`/`CarePlan` resources — **draft-only, HITL** | Healthcare API (fills gap #2: all official tools are read-only) |

**The stage line:**
> *"Google gives agents MCP tools to **read** FHIR and to **call** ML endpoints — but there is
> no MCP server that lets an agent **reason about a population**: measures, gaps, cohorts,
> risk. So we built the first population-health MCP server on Google Cloud."*

This phrasing survives interviewer scrutiny **because it names exactly what already exists.**

**Interoperability beat:** connect the same server to **Gemini CLI** (or any MCP client) live —
"one server, any agent" — then note it's built on Google's own open-source **MCP Toolbox**
framework, so it slots into the ecosystem the way Google intends. Close the loop with the job
description: *"and this gap analysis is a product-feedback memo I'd send to the BigQuery/
Healthcare API PM as a CE."*

---

## 7. What we reuse (so the build is fast)

| From | Reused |
|---|---|
| `health` repo | The 3,000 × 61 synthetic cardiometabolic cohort (→ BigQuery + FHIR conversion) · MOPH guideline PDFs (→ RAG Engine corpus) · the two-persona script structure · scenario beats (morning briefing, deep-dive, statin gap, cost, equity) · HITL queue + audit concepts |
| `Roads_RAM_UI` repo | The glass-panel/bokeh/Manrope aesthetic · source-chip citations · collapsible tool-call trace · **full-trace details popup** (tool calls, LLM calls, retrieval calls, token cost) · live agent-activity indicator while a query runs |
| New palette | Re-skin from SAS blue to a Google-flavored scheme (Google Blue #4285F4 / deep navy, with the four Google colors as chart accents) + MOPH maroon accent as a nod to the customer |

The trace-transparency UI is the perfect vehicle for a technical panel: every answer visibly
decomposes into FHIR queries, RAG retrievals, MCP tool calls, and model scores.

---

## 8. Run of show — 30 minutes

| Time | Beat | What happens |
|---|---|---|
| 0–3 | **Customer story** | Qatar burden → QHIE exists → missing intelligence layer → Doha region. No product names yet. |
| 3–6 | **Architecture slide** | One slide (§4). Name the capabilities to watch for: multi-agent, RAG, 5 real ML models, MCP, A2A, evals, HITL, sovereignty. |
| 6–13 | **Act 1 — Clinician** | Morning briefing (proactive scan). Patient deep-dive: trace shows FHIR → RAG citation → **live endpoint score with explanation** → drafted action into HITL queue. Statin-gap panel ranked by model #2. |
| 13–18 | **Act 2 — Executive** | Same platform, different persona. Cost concentration (KMEANS segments). TimesFM demand forecast. **Counterfactual policy simulation** — close the statin gap, re-score the cohort, show predicted event reduction and QAR savings. |
| 18–23 | **The MCP moment** | Gap slide (what Google ships → what's missing). Our server's tools fire in the trace. Same server attached to Gemini CLI live. *"First population-health MCP server on Google Cloud — and this is the feedback loop a CE runs."* |
| 23–25 | **Free-form query** | Panel suggests a question, or type: *"Which facility has the worst BP control in high-CV-risk Qataris, show a chart, and what does the guideline say?"* Kills the "scripted demo" objection. |
| 25–28 | **Trust & engineering rigor** | `adk eval` run on a golden session (trajectory regression test) · audit trail with a consent-denial entry · HITL queue with the unsigned draft. *"We test the agent's tool calls, not just its words."* |
| 28–30 | **Close** | Job-description mapping (§2) + roadmap: Agent Search for Healthcare over clinical notes, MedGemma 1.5 in-region, Arabic UX + MedASR dictation, A2A across ministry systems. |

**Presentation format:** ~4 slides total (customer, architecture, MCP gap, roadmap/close);
everything else live in the product. CEs demo, they don't lecture.

---

## 9. Q&A preparation (the 15 minutes)

Likely questions and the prepared line:

- **"Is the data real?"** — Synthetic, 3,000 patients, zero PHI. The architecture is real:
  actual FHIR R4 store, actual streaming export, actual trained models.
- **"Why BQML and not custom training?"** — Right tool for tabular clinical data at this scale;
  registered into the same Model Registry, served on the same endpoints. For imaging/genomics
  I'd go custom training or MedGemma via Model Garden.
- **"Why didn't you use the official healthcare MCP tools?"** — We did (name them). Ours sits
  *above* them: population reasoning, not record retrieval.
- **"How do you stop hallucinated clinical advice?"** — Grounding chain: numbers only from
  tools, recommendations only with RAG citations, actions only through HITL. Plus eval:
  trajectory tests + LLM-judge scoring; Model Armor on the runtime.
- **"Scalability?"** — BigQuery does this at national scale today; Agent Engine autoscales;
  the FHIR store streams — the demo IS the production shape, minus hardening.
- **"Cost of running this for MOPH?"** — Storage/query pennies at this size; the endpoint is
  the only always-on cost; Gemini Flash pricing makes the agent loop cheap. Offer to whiteboard.
- **"What would you do next?"** — Roadmap beats + *"file the MCP gap as product feedback —
  that's the CE feedback loop in the JD."*
- **"Arabic?"** — Gemini is natively multilingual; UX localization + Arabic SNOMED mapping is
  the roadmap; MedASR for dictation (note: English-heavy training — be honest).
- **Deprecation trap questions** — know the dead list cold: MedLM (Sept 2025), Healthcare NL
  API (May 2026), Healthcare Data Engine (Sept 2025), Firebase Studio (sunsetting), Gemini 2.5
  retiring Oct 2026. Never mention them as live.

---

## 10. Build plan

### Phase 1 — the working product (build first)
1. `g_health` scaffold: FastAPI backend + React/Vite/Tailwind frontend in the Roads_RAM_UI
   aesthetic, Google-flavored palette. Single Dockerfile → Cloud Run.
2. Data: load cohort to BigQuery; script to convert rows → FHIR R4 bundles → Healthcare API
   store (me-central1); enable streaming export.
3. Models: the five BQML statements + registry + endpoint deploy script.
4. Agents: ADK supervisor + 5 sub-agents (Gemini 3.8 Flash), tool-call trace streamed to UI.
5. RAG Engine corpus from the MOPH PDFs; citations rendered as source chips.
6. **`population-health-mcp`** server (MCP Toolbox-based or FastMCP) + wire into the Care-Gap
   agent via `McpToolset`.
7. Dashboards (same queries as chat), HITL queue, audit trail.

### Phase 2 — the polish that wins
8. `adk eval` golden-session evalset + a small Gen AI Eval Service judge run (screenshot-able).
9. A2A: expose the Action agent via `RemoteA2aAgent`.
10. Gemini CLI hookup of our MCP server (the interop beat).
11. Agent Engine deployment of the supervisor (free tier) — or keep agents in the Cloud Run
    backend if time is short (both are defensible; Agent Engine is the better story).
12. Demo-day resilience: scripted-scenario fallback mode (like the old demo), recorded backup
    video, seed data script for a fresh project.

### Stretch (only if time allows)
- Voice moment via Gemini Live API (GA) — ask the morning briefing out loud.
- MedGemma 1.5 4B deployed from Model Garden in-region for the sovereignty beat (costly per
  hour — deploy demo-day only, or keep as a slide).

### What I need from you
- A GCP project with billing (free trial $300 credit is plenty) + `me-central1` enabled APIs:
  Healthcare, BigQuery, aiplatform (Agent Platform), Run, Storage.
- Confirm caveat: some GEAP/Gemini serving may not be in-region in me-central1 — pattern is
  "data at rest in Doha, model inference in nearest supported region" unless console says
  otherwise. We verify week-of and phrase accordingly.
- Rough costs: BQML training on 3k rows ≈ cents; endpoint ≈ ~$1–2/day of a small machine
  (deploy day-of); Gemini Flash calls ≈ dollars; everything else free tier.

---

## 11. Open decisions (need your call before building)

1. **Product name** — Afiya / Nabd / QHIE Copilot / other?
2. **Agents runtime** — Agent Engine (better story, more moving parts) vs. in-process ADK in
   the Cloud Run backend (simpler, still real ADK)? Recommendation: build in-process first,
   promote to Agent Engine in Phase 2.
3. **Voice moment** — include the Live API beat or keep it as a roadmap slide?
4. **MedGemma** — deploy it (cost + time) or present as roadmap? Recommendation: roadmap.
5. **Presentation deck** — I can generate the 4-slide deck (Gamma or hand-built) once the
   storyline is locked.

---

## 12. Landmines checklist (never say these are live)

| Dead product | Died | Say instead |
|---|---|---|
| MedLM / Med-PaLM 2 | Sept 2025 | Gemini 3.x + MedGemma 1.5 |
| Healthcare NL API | May 2026 | Gemini structured extraction |
| Healthcare Data Engine | Sept 2025 | Healthcare API + BigQuery streaming |
| Firebase Studio | sunsetting → Mar 2027 | AI Studio Build mode |
| Gemini 2.5 family | retiring Oct 2026 | Gemini 3.5/3.8 Flash, 3.1 Pro |
| "Vertex AI" (name) | rebranded May 2026 | Gemini Enterprise Agent Platform ("formerly Vertex AI") |

And re-verify the week of the interview: model IDs shift monthly; re-run the MCP gap searches
(GitHub + PulseMCP + mcpservers.org for "care gap", "HEDIS", "population health", "CQL") so
"first" is still true on stage.
