# Nabd (نبض) — The Demo Storyline, v3 (diabetes programme)

> Scope: type 1 and type 2 diabetes only. The deck (`deck/Nabd_MOPH_Google_Cloud.pptx`, 8 slides) is presented first; architecture lives in the slides, not in the app.

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

"Four thousand people with diabetes are in this registry. Seven hundred and fifty-three of them have not had an
HbA1c test in six months. Nearly a thousand have an HbA1c above 8 on metformin alone and meet the criteria for
treatment intensification. Nobody is looking for them, because the Health Information Exchange can find *a*
patient but it cannot find *those* patients.

This is Nabd — the Arabic word for *pulse*. It puts Google's agentic stack on top of the exchange so that a
clinician or a director can simply **ask**."

*(You have already presented the 8-slide deck: problem, journey, solution, how it works, the two architectures,
roadmap and demo agenda. The demo starts here.)*

*(Point at the counters as they finish counting up. Then click **Open the Assistant**.)*

---

## 2. The customer — 2 minutes, stay on the landing page

- **Qatar**: among the five highest adult diabetes prevalences in the world (IDF); diabetes care cost projected to rise from QR 1.8bn to QR 5bn a year by 2035; half of all dialysis is diabetes-related.
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

Then click **Architecture** in the nav (30 seconds, no more — the tab is there for Q&A):

- Select the flow **"Clinician asks a question"** — the diagram dims to the synchronous path and the
  arrows animate. *"Six lanes, four kinds of arrows. Per-patient signals stream; per-population numbers
  batch at 02:00. Nothing is streamed because streaming is fashionable."*
- Click the **ADK runtime** node. *"This is the honest bit. Agent Engine is the right managed runtime, but
  its region list doesn't include Doha — and the conversation state carries clinical context. So the same
  ADK tree runs on Cloud Run in me-central1 with sessions in AlloyDB, and moving to Agent Engine is a deploy
  target the day it launches in Qatar. Same story for Model Armor and Model Monitoring: in-region
  equivalents today, managed services when they arrive."*
- *"Every node answers five questions — why, how it scales, what I rejected, what runs today, what it
  costs. Ten decision records behind it. We can go anywhere you like in Q&A."*

---

## 4. Act I — Kamal Miah (clinician persona, ~8 minutes)

Persona: **Dr. Amal Al-Mansoori**, Consultant Endocrinologist. The audience follows one patient.

| Click | What appears | What you say |
|---|---|---|
| **C1 Morning panel briefing** | Live trace: cohort → risk → pop-health MCP; a table of the five highest-risk patients; a 3D chart of open gaps | *"This ran at 6am, not on my command. Watch the agents — every hop is on the record."* Point at the trace. |
| **C2 Patient review + draft prescription** | The hero patient (the landing page names them): type 2 diabetes, HbA1c risen from **10.2 to 10.9** in a year on **metformin alone**, early kidney involvement, adherence recorded. Registry tier **Moderate**; model deterioration risk **36%**, drivers: HbA1c, adherence, eGFR, insulin status. Guideline citation. **Empagliflozin 10mg drafted.** The 36-month HbA1c trajectory as a chart. | *"The registry tier says Moderate. The model says 36% and tells me why: the trajectory, the kidneys, the adherence. The guideline page is right there. And nothing was prescribed — it is in my queue."* **This is the centre of the demo. Slow down.** |
| Click a **citation chip** | The retrieved guideline passage + link to the PDF page | *"The agent doesn't memorise medicine. It retrieves the page at query time. Swap the PDF, no retraining."* |
| Open the **agent trace** | 4 steps · 4 agents, with args and results | *"FHIR read → model score → guideline retrieval → draft. Auditable end to end."* |
| **Simulator** tab (top nav) | Kamal is preselected. Drag HbA1c from 10.9 to 8.0: the estimate falls from about 34% to 5%, the band drops, the attribution bars show HbA1c carrying most of the change. Toggle the SGLT2i/GLP-1 RA on, press **Guideline targets**, then **Explain with Gemini** | *"This is the same model, re-scored live. Nothing here is a canned number. The model is monotonic by construction — it cannot say that lowering blood pressure raises risk — and Gemini is only allowed to narrate the numbers on the screen."* |
| **C3 Treatment intensification gap** | 999 type 2 patients with HbA1c ≥8 and obesity or kidney disease not on an SGLT2i or GLP-1 RA; counterfactual: re-score all 975 eligible with therapy applied → events avoided over 24 months, therapy cost, and a **negative net on cost alone** — the case is clinical; review list drafted | *"This is not a canned number. The eligible cohort was re-scored through the same model with the therapy applied. And I want the model to tell the ministry honestly that this one does not pay back on cost — the case is outcomes."* |
| **Queue tab** | The Empagliflozin draft, unsigned. Approve it. | *"The agent is an assistant, not an actor. The clinician approves."* The approval lands in the Audit trail — show it later. |

Skip **C4 (retinal screening recall)** unless you are ahead of time — it is a strong backup: 1,203 patients overdue, the backlog by facility, a recall drafted for the worst one.

---

## 5. Act II — the ministry (executive persona, ~7 minutes)

Switch persona to **Dr. Khalid Al-Kuwari**, Population Health Executive. Same platform, different altitude.

| Click | What appears | What you say |
|---|---|---|
| **Dashboards → Overview** | KPI strip; HbA1c trend **falling 7.65 → 7.3 over 36 months**; demand forecast **+4.6%**; 3D facility benchmark; risk pyramid | *"Every number here is the same query the assistant runs. One source of truth — the briefing and the conversation can never disagree."* |
| **E1 National picture** (chat) | Facility spread: Mesaimeer 52% controlled vs Hazm Mebaireek 28% | *"Twenty-four points between facilities. That's an operational lever, not a clinical mystery."* |
| **E3 Programme simulation** | Five programmes, 24 months, ranked by net benefit; combined view | *"The HbA1c recall and the adherence programme pay for themselves — they are cheap and they reach the patients the model worries about. Drug intensification does not pay back on cost within 24 months, and I would rather the model tell the minister that than a slide."* **Honest analytics is a feature.** |
| **E4 Equity** | Mean HbA1c by nationality — Bangladeshi 7.7% vs Qatari 7.1% | *"That gradient tracks access, not biology. Multilingual outreach is the cheapest lever on the board — and it's a National Health Strategy pillar."* |
| **Dashboards → Geography** | The facility map: 18 facilities sized by patients, coloured sand→maroon, gold rings on the 8 flagged ones — **Al Shamal and Al Khor in the north, Hazm Mebaireek in the Industrial Area**. Toggle Qatar → Greater Doha. Click Hazm Mebaireek → its profile (26.8% controlled, highest expat share). | *"Control is concentrated in Doha. The further from the capital, and the closer to the Industrial Area where the workforce lives, the worse it gets. Distance and the access gradient follow the same line. That is a clinic-hours and outreach decision, not a drug."* **Then ask the assistant** *"Show me the HbA1c-overdue patients on a map"* — the agent draws the same map inside the chat. |
| **Dashboards → Deterioration Risk** | AUC 0.854 vs the registry tier's 0.809; the high-risk vs low-risk profile table; calibration curve; feature importance; governance cards | *"Four models, versioned, with cards. Click one — intended use, limitations, and what it becomes on Google Cloud."* |

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

## 7. Trust — the Evaluation tab (~3 minutes)

Click **Evaluation**. This is where the panel's "how do you know it works" is answered before it is asked.

- **Risk model** (45 s): *"Everything on this page is computed from 1,000 patients the model never saw."*
  ROC: maroon line is ours (0.853), gold is the registry's legacy points score (0.774). Drag the
  **operating-threshold slider** — the confusion tiles and 'reviews per event found' update live.
  *"The model doesn't choose the threshold. The ministry does — and now they can see what each choice costs
  in nurse time and missed events."* Point at the **fairness table**: TPR gap 3.7 points across nationality
  groups, small groups shown but not judged; the age gap is prevalence, not bias, and I say so on the page.
- **Agent evalset** (60 s): press **Run evalset**. Ten real questions go through the real supervisor graph
  and are scored on four things a clinician would demand: did it call the right tools, did every clinical
  claim carry a citation, did nothing bypass the human queue, and does every number in the answer match a
  recomputation from the tables. *"A fluent wrong number is the classic LLM failure — this catches it."*
  With the Gemini key on, tokens and cost per question appear too.
- **LLM & cost** (45 s): *"Why Flash 3.8 — chosen on this evalset, not a leaderboard; GA; a year from
  deprecation; a third of Pro's price. Pro is the judge, never the hot path."* Then the arithmetic:
  *"Did I just add many agents? A flat agent re-reads 2.5k schema tokens on every hop; the supervisor reads
  700. Since Gemini 3.5 function declarations are billed as input tokens, so that gap is literally the
  invoice — about $1,700 a month at 20k questions a day — and the specialists are also how the guideline
  agent is physically unable to draft a prescription."*
- **Governance** (15 s): nine controls implemented, six delivered by the platform, zero autonomous writes.

## 7b. Free-form — ~2 minutes

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
agents run as the same ADK graph on Cloud Run in Doha — Agent Engine the day it reaches me-central1 — with
PHI never leaving the Qatar Data Boundary and the LLM seeing pseudonymous data only.

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
- *Latency?* — Each specialist is a Gemini Flash call; a typical clinician question is 3 tool hops. `thinking_level LOW` on routing turns keeps first token under a second; streaming the trace makes the wait feel like work, not delay.

**Architecture (the "deploy, not demo" questions)**
- *Real-time or batch?* — Both, deliberately. Per-patient signals stream (a new HbA1c re-scores that patient in seconds via FHIR store → Pub/Sub → endpoint). Per-population metrics batch at 02:00 (stratification, gaps, quality measures, equity). Streaming the aggregates would cost ~100× for numbers that move over weeks. The Real-time vs batch view lists every path with its budget.
- *How does it scale?* — Compute isn't the constraint anywhere: one scorer replica covers 50× the national peak, BigQuery is serverless, ingest autoscales on backlog. The variables that actually move cost and latency are Gemini tokens per question and synchronous hops — which is why the eval tab measures both.
- *Where does inference run?* — Risk: XGBoost on a Vertex online endpoint in Doha (~1 ms CPU per score, p50 < 10 ms) plus nightly batch for the cohort. LLM: Gemini 3.8 Flash on the global endpoint — acceptable because the prompt only ever carries pseudonymous ids and aggregates (ADR-01). Retrieval: RAG Engine. Voice: Chirp 3 for Arabic.
- *Data residency with Gemini?* — Identity zone and reasoning zone are separated. PHI (FHIR, BigQuery, AlloyDB, Feature Store) sits in me-central1 under an Assured Workloads Qatar Data Boundary with CMEK and VPC-SC. The agents see the pseudonymised analytics zone; re-identification is an audited app-layer join inside the perimeter. That makes the LLM's region a latency question, not a PHI question.
- *Why isn't the agent on Agent Engine?* — Its region list doesn't include Doha, and conversation state carries clinical context. So ADK runs on Cloud Run in me-central1 with sessions in AlloyDB. Deploy-target change when Agent Engine lands in Qatar — same for Model Armor and Model Monitoring, which I replaced with Sensitive Data Protection and BigQuery drift jobs in-region.
- *What does it cost to run?* — Order of magnitude at Doha list prices: ~$1.6k/month for a 4-site pilot, ~$12.6k/month national at 20k questions a day, 30% of it Gemini tokens. One avoided complication admission is QAR 32k, so the national platform costs about 1.4 admissions a month.

**Evaluation (the "is this AI garbage?" questions)**
- *How did you choose the LLM?* — On our own evalset: trajectory recall, groundedness, faithfulness, latency and cost per question across Flash 3.8, Flash 3.5 and Pro 3.1. Flash 3.8 matched Pro on tool-structured tasks at a third of the cost; it's GA and a year from deprecation; 2.5 Flash was excluded because it retires in October. Pro is the judge and the monthly synthesis — never the hot path.
- *Is this the most cost-effective way, or did you just add agents?* — Measured, not asserted: flat agent 2,555 schema tokens per hop × 3 hops vs supervisor 687 + one specialist each. Function declarations are billed as input tokens since Gemini 3.5, so it's ~30% cheaper per question at scale — and least privilege, independent evaluation and a swappable MCP agent come with it. The one cost is ~0.7 s of extra hop, hidden by streaming the trace.
- *How do you know the agent isn't hallucinating?* — Three walls and a test. Numbers only from tools; clinical claims only with a citation; actions only through the queue. Then the golden evalset re-computes every headline number from the tables and fails the case if it doesn't match. Phase 2 runs the same set in Cloud Build on every PR and on 2% of production weekly, with Gemini 3.1 Pro as an LLM judge for tone and Arabic fidelity.
- *Is the model fair?* — Subgroup TPR/FPR at the operating threshold, by nationality group, gender and age; gaps computed only over groups with enough events; small groups shown but not judged. The age gap is prevalence (24% vs 5%), and the page says so. Monthly drift jobs re-run this table in phase 2.

**Google-specific**
- *What changed at Next '26?* — Vertex AI became the Gemini Enterprise Agent Platform; 50+ managed MCP servers went GA; Agent Engine sessions/memory GA'd. Firebase Studio is sunsetting → AI Studio Build.
- *What's deprecated that you avoided?* — MedLM (Sept 2025), Healthcare NL API (May 2026), Healthcare Data Engine (Sept 2025), Gemini 2.5 (retiring Oct 2026). Gemini + MedGemma is the current medical story.
- *Sovereignty?* — PHI and the agent runtime in me-central1 under the Qatar Data Boundary; the LLM sees pseudonymous aggregates only; open-weight MedGemma can run in-region later for the clinical-language pieces. PDPPL (Law 13/2016) is the frame.

**Judgment**
- *What would you cut?* — The forecast. It is the weakest model and the least surprising insight. I would trade it for a hypoglycaemia-risk loop on the insulin-treated cohort, which prevents admissions.
- *What worries you?* — Adoption, not accuracy. The queue exists so clinicians own the decision; the equity view exists so the ministry owns the gap. Tools don't change outcomes; workflows do.

---

## 10. Demo-day checklist

- [ ] Railway deploy green; `/api/health` returns `mode: multi-agent` with a live model name.
- [ ] Run **C2** once at home the morning-of: confirm Kamal Miah is still the hero (`/api/story/hero`) and his numbers match this doc.
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
3. **One named patient** — a real trajectory, a real explanation, a real draft, a real approval.
4. The **3D charts and the facility map** rendered *by the agent* inside a chat answer.
5. **Programme simulation** that admits drug intensification does not pay back on cost alone.
6. **AUC 0.854 vs 0.809** with a calibration curve and a high-vs-low risk profile — real ML, defended.
7. **The risk simulator** — sliders re-score the deployed model live, attribution shows what moved, Gemini explains it, and monotonic constraints mean no lever ever moves the wrong way.
7. The **MCP reveal** with the exact inventory of what Google already ships.
8. The **same MCP server answering Gemini CLI**.
9. **Arabic voice input** — one click, one question, in the customer's language.
10. The **audit trail** carrying the whole story you just told.
11. **Run evalset** — ten real questions through the real graph, scored live, including "does every number match a recomputation".
12. The **threshold slider** — the ministry choosing its own trade-off between nurse time and missed events.
13. The **architecture slide that admits Doha's limits** — Agent Engine, Model Armor and Model Monitoring are not in me-central1, and the design names what replaces them today.
