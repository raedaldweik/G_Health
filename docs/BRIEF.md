# Nabd: The Complete Brief

META: A study document for the presenter, not a script to read aloud. It explains and defends every decision in the demonstration and the deck: the business case, the data, every AI model, the agent architecture, the guardrails, data governance, latency, inference, and the reference architecture on Google Cloud that would be validated in technical discovery, including the availability trade-offs of strict in-country residency. Numbers are from the live build on 2026-09-10, after the risk-reduction pass.

## 1. The business case

### Why a diabetes registry, and why this customer

Diabetes is the single most expensive chronic condition a Gulf health system carries, and the one where population management has the clearest evidence base. Qatar sits in the top five countries for adult prevalence in the IDF Diabetes Atlas. The National Diabetes Strategy projected the annual cost of diabetes care rising from about 1.8 billion riyals to 5 billion by 2035. Half of dialysis in the country is attributable to diabetes, and diabetes sits behind a large share of stroke, heart failure, blindness and amputation. Every one of those downstream costs is preceded by years of measurable signals: HbA1c, blood pressure, kidney function, missed tests, missed medicines.

That is the business logic. Deterioration is predictable, the signals already exist in the exchange, and a registry that only describes the population leaves that value on the table. A registry that can find the patients who are likely to deteriorate, explain why, and prepare the work for a clinician converts data the ministry already pays for into earlier reviews. Whether earlier reviews change outcomes, and by how much, is a causal question that a pilot answers; the predictive model on its own does not.

The second reason is customer readiness. This ministry already has a national Health Information Exchange, a diabetes registry, and a predictive programme built on SAS Viya. The data exists, the outcome definitions exist, and the clinical governance exists. A customer engineer looks for exactly that: a customer two stages into a journey, where the third stage is a capability question rather than a data-collection project. It is far easier to sell "ask your registry a question" than "build a registry".

The third reason is that diabetes is the front door to every other chronic programme. Cardiovascular disease, chronic kidney disease, maternal diabetes and obesity share the same data model, the same agent pattern and the same guardrails. The first programme is where the platform is proven; the second is where consumption grows.

Nabd is the ministry's solution, built on and powered by Google Cloud. It is not a Google product, and the deck and the header say so: a Nabd mark, and a small "Target platform: Google Cloud" tag.

### What the ministry buys, in plain terms

- Earlier identification. The registry has about 4,000 patients in this demonstration and the model expects about 418 deterioration events in the next twelve months. The model finds the patients the rule-based tier misses and explains why, so that a clinician can review them first. What a review programme would prevent is measured by an evaluated pilot, not estimated by the model.
- Faster answers. A director's question that used to be an analyst's week becomes a conversation. A clinician who could not ask at all now can.
- Scenarios that show where to look. The population risk scenarios re-score each eligible cohort with one model input changed and show how the predicted-risk distribution shifts, which tells the ministry where the model is most sensitive and where intervention design should start. They are predictive scenario analysis, not programme evaluation, and the answer says so every time.
- A defensible system. Every number comes from a tool, every clinical claim from a cited guideline page, every action from a signed human decision, every step in an audit trail. Predictive outputs are never presented as causal effects; no drug or dose is ever drafted; group differences are described, not explained. That is what a medical director and a regulator will ask for first.

### Why Google Cloud is the proposed target platform

- Doha is a Google Cloud region (me-central1), which allows data residency to be handled as configuration rather than negotiation: Assured Workloads with the Qatar data boundary, customer-managed keys, VPC Service Controls. Which services are available in region for each part of the design is confirmed in discovery.
- The healthcare data plane is native. The Cloud Healthcare API stores FHIR, enforces consent, de-identifies, and streams into BigQuery. Nobody has to build that.
- The analytics and ML plane is one product. BigQuery holds the exchange, BigQuery ML trains the same class of model the demo uses, and Vertex AI serves it. The forecast is one SQL statement.
- The agent stack is first-party. The prototype is built on the Agent Development Kit and the Model Context Protocol; Gemini on Vertex AI, RAG Engine and the Gen AI Evaluation Service are the target for the remaining pieces.
- Managed, horizontally scalable services. The customer pays for questions and queries, not for licences. National-scale capacity, quotas, concurrency, latency and cost would be validated through load testing during the pilot.

### What the ministry would spend

The Evaluation tab measures the prototype's actual tokens and cost per question when the evalset runs live, and it lists the proposed models at their list prices. That is what can be said today. A production figure is not asserted: during discovery we would model cost from expected users, question volume, token consumption, BigQuery scan volume, model-serving requirements and availability requirements, then validate it during the pilot. Whether the platform is worth its cost is a decision the ministry takes on evidence from the pilot, not on a return calculated from a predictive model.

### How a customer engineer would run this engagement

1. Discovery, two weeks. The registry team, two clinicians, the data protection officer and the security team. One question the pilot must answer, written in the customer's words, and the extract that answers it. Agreed in the same fortnight: which model endpoint is used and exactly what may enter a prompt; the required recovery point and recovery time and whether policy permits a compliant secondary recovery location; which managed services are available and approved in me-central1; and a benchmark of the orchestration topologies on the customer's own evalset.
2. Architecture workshop, half a day. The reference architecture in the deck, validated and adapted to their facilities, feeds and policies, signed off.
3. Proof of concept, six to eight weeks. A de-identified extract in BigQuery, the models retrained and evaluated on their data, the evalset written by their clinicians. Success criteria fixed before the first commit.
4. Pilot, one quarter. Four facilities, a clinical safety case, the approval queue live, adoption measured by approvals rather than by log-ins, load testing against the agreed SLOs, and the cost model validated against real usage.
5. National rollout. FHIR streaming from every facility, HL7 v2 bridges for the legacy sites, Looker for the published KPIs, the second programme scoped.

The customer engineer owns the technical outcome and the truth about what the product can and cannot do. The account executive owns the commercial relationship. A partner builds and operates. Product gets the gap memo.

## 2. The data

### What the exchange looks like

The demonstration runs on a synthetic exchange shaped like a national HIE: 4,000 patients, eight relational tables, thirty-six months of history, 18 facilities (hospitals and primary-care health centres), and a FHIR R4 export sample. Roughly 193,000 observations and 80,000 encounters. Every code system is real: LOINC for laboratory results, ICD-10 and SNOMED for conditions, ATC for medicines.

| Table | What it holds |
|---|---|
| patients | Demographics, nationality, district, insurance, primary facility, diabetes type, consent status |
| encounters | Outpatient, telehealth, emergency and inpatient visits with dates, reasons and length of stay |
| conditions | Coded diagnoses with onset dates |
| medications | Prescriptions with ATC codes, drug class, start and stop dates |
| observations | HbA1c, blood pressure, eGFR, urine ACR, LDL, BMI with dates and LOINC codes |
| care_gaps | One row per open gap per patient, nine gap types |
| facilities | Name, type, region, coordinates |
| patient_summary | The wide analytical table: one row per patient with the latest values, derived flags, utilisation, cost, the baseline rule-based registry score and the outcome label |

The summary table is what the tools, the models and the dashboards read. It is the equivalent of the curated mart that Dataform would rebuild nightly on Google Cloud.

### Why synthetic, and why 4,000

Synthetic because a demonstration must contain zero PHI, and because a customer engineer never carries a customer's data into an interview. The generator is seeded and documented, so every number is reproducible. Its clinical logic is deliberate: HbA1c trajectories drift with adherence and therapy, blood pressure responds to RAAS therapy, kidney function declines with albuminuria and poor control, and the outcome label is drawn from a logistic model of the same drivers, calibrated to a 10.5 percent twelve-month event rate. The machine learning task is to recover those drivers from the tables without seeing the formula.

Four thousand is a deliberate size. Large enough that a model evaluated on a thousand held-out patients with 107 events produces stable metrics for demonstrating the methodology; small enough that the whole system runs on one container and every dashboard recomputes in under a second. On Google Cloud the warehouse is BigQuery, a managed and horizontally scalable service, but national-scale capacity, quotas, concurrency, latency and cost are validated through load testing during the pilot rather than assumed.

### The outcome and the baseline rule-based score

The label is deterioration within twelve months: an admission for hypo- or hyperglycaemia, diabetic ketoacidosis or hyperosmolar state, foot infection or acute kidney injury, or progression to HbA1c of 10 percent or more. The baseline rule-based score is the kind of tier registries run today: points for age over 60, HbA1c over 9, a prior admission, and systolic over 160. It is blind to kidney function, adherence, monitoring gaps, complications and therapy. That blindness is the whole story of the hero patient: the registry calls Kamal Miah Moderate; the model calls him Very High at 34 percent, because it can see what the rules cannot.

### Consent and data quality

Some patients carry a restricted consent status. Every tool that reads a record checks it first; a restricted patient cannot be opened, scored or simulated, and the refusal is written to the audit trail. That is the demonstration equivalent of the Cloud Healthcare API's consent enforcement on the FHIR store.

Data quality is treated as a care gap. An HbA1c that is overdue is either a clinical gap or a missing feed, and both are worth knowing. On real data the first week of any engagement is profiling in BigQuery so that the gaps are numbers rather than fears.

## 3. The AI models

There are four trained models, one embedding model, and the language model. Each has a model card in the product with its version, task, training data, intended use, constraints and limitations. One caveat applies to every metric below and is printed on the deterioration model's card: the models are trained and evaluated on synthetic data, so held-out performance demonstrates the evaluation methodology, not clinical validation. Clinical validation and a fairness audit on real data are preconditions for any production use.

### Deterioration risk (XGBoost, v2.2.0)

The core model. Gradient-boosted trees on 27 features: age, sex, BMI and its twelve-month change, years since diagnosis, smoking, HbA1c now and twelve months ago and days since the last test, systolic and diastolic pressure, eGFR, urine ACR and albuminuria, retinopathy, neuropathy, foot-ulcer history, hypertension, metformin, SGLT2 inhibitor or GLP-1 agonist, insulin, RAAS inhibitor, adherence as proportion of days covered, admissions and emergency visits in the last twelve months, the count of diabetes medicines, and the count of open care gaps.

Why XGBoost and not a neural network or a logistic regression. It is a strong, efficient baseline for structured tabular clinical data with interpretable per-prediction contributions: it handles non-linear thresholds (HbA1c above 9, eGFR below 60) natively; it gives per-feature contributions a clinician can read; it trains in seconds and scores in a millisecond; and BigQuery ML has the same estimator, so the same model class trains inside the warehouse on Google Cloud. If a customer's data favoured a different estimator, the evaluation page would show it, and the rest of the system would not change.

Evaluation, all on a stratified 25 percent hold-out the model never saw (1,000 patients, 107 events), on the synthetic demonstration dataset:

| Metric | Value | What it means |
|---|---|---|
| AUC | 0.854 vs 0.809 for the baseline rule-based score | Ranks a patient who will deteriorate above one who will not 85 percent of the time |
| Average precision | 0.577 on a 10.7 percent event rate | Five times better than chance at the top of the list |
| Brier score | 0.067 vs 0.096 for predicting the prevalence | Thirty percent better probability estimates than a constant |
| Calibration slope | 0.82 | Somewhat over-confident at the extremes; the decile chart shows where |
| Operating threshold | 12 percent | The High band; sensitivity about 69 percent, specificity about 84 percent, about three reviews per event found |

Bands: Low below 5 percent, Moderate 5 to 12, High 12 to 25, Very High 25 and above. The threshold is a policy choice, not a model property; the Evaluation tab lets the ministry drag it and see what each choice costs in nurse reviews and missed events.

Monotonic constraints, and where they stop. The model is trained with XGBoost monotone constraints, kept only where they are directionally defensible for a predictive model: the estimate cannot fall as HbA1c, systolic or diastolic pressure, urine ACR, BMI, smoking, admissions, emergency visits, monitoring delay or open care gaps rise, and cannot rise as eGFR or adherence improve. Those are measurements of control, organ function and engagement, and a model that moved the wrong way on them would be clinically implausible. The therapy flags (metformin, SGLT2i/GLP-1 RA, insulin, RAAS inhibitor) are deliberately unconstrained. In a registry a drug on the record marks disease severity and treatment history as much as treatment, and this model estimates risk, not treatment effect; constraining therapy to lower the estimate would have baked a causal assumption into a predictive model. That is also why the simulator no longer has therapy toggles. The constraints are a training-time control, not a filter on the output.

Explanations. XGBoost's own per-prediction contributions (the SHAP-style pred_contribs) give each feature's push in log-odds. The patient review shows the top drivers (for Kamal Miah, HbA1c and emergency visits); the simulator shows how each contribution changes when an input changes, allocated onto the probability change so the bars sum to the difference on the gauge.

Fairness. The Evaluation tab reports true-positive and false-positive rates at the operating threshold by nationality group, gender and age band, computes gaps only over groups with enough events, and shows small groups without judging them. The age gap is prevalence, not bias, and the page says so. On synthetic data this proves the method; on real data a fairness audit precedes production and a monthly job re-runs the table and alerts on drift.

### Population segmentation (KMeans, k=4, v1.0.1)

Unsupervised clustering over annual cost, model risk, age, open care gaps and admissions, standardised. Four segments, named by their profile: Complex high-cost (670 patients, about QAR 33,400 a year, 13 percent mean risk), Care-gap heavy (1,535, cheap today, many open gaps), Stable low-touch (1,464), and Rising-risk (331 patients, 64 percent mean risk, moderate cost today). The segments are descriptive, not causal. Their use is the executive narrative: the first segment is where case management is worth examining; the second is cheap to reach and its cost is future, not current. On Google Cloud this is BigQuery ML KMEANS in SQL.

### Patient similarity (nearest neighbours)

A k-nearest-neighbour index over twelve standardised clinical features. It answers "patients like this one" for clinical context and for cohort matching. It is feature-space similarity, not outcome-matched controls, and the card says so. On Google Cloud this becomes gemini-embedding-001 patient embeddings with BigQuery VECTOR_SEARCH, which also allows similarity over notes once they are in scope.

### Ambulatory demand forecast (ridge regression)

Trend plus month-of-year seasonality over thirty-six months of encounter volumes, with an 80 percent interval. It forecasts about 5 percent growth in outpatient and telehealth visits over the next twelve months and picks up the summer dip and the Ramadan pattern. It is the weakest model and the least surprising insight, and if something had to be cut this would be it. On Google Cloud it is one SQL call: AI.FORECAST in BigQuery, on the TimesFM foundation model, with no training step.

### Guideline retrieval (BM25 plus gemini-embedding-001)

The national clinical guideline PDFs are chunked once into 445 overlapping passages of about 1,400 characters, cached on disk. Retrieval is hybrid: a BM25 keyword index that always works, plus a semantic index from gemini-embedding-001 at 768 dimensions (Matryoshka truncation of the 3,072-dimension model, which keeps quality and cuts storage four-fold). Scores are blended 45 percent lexical, 55 percent semantic. The embedding matrix is computed once, cached to disk, and committed, so a deployment never re-embeds and never hits an embedding quota at start-up. Every hit carries document, page and the passage, which is what the citation chip shows. For Kamal Miah the hit is the MOPH national guideline for type 2 diabetes in adults and the elderly, page 14, the therapy intensification passage. On Google Cloud this layer is Vertex AI RAG Engine over a Cloud Storage corpus.

### Gemini

Gemini 3.8 Flash is the proposed model on the hot path: the supervisor and all five specialists. It was chosen on the product's own evalset, not on a leaderboard. It is the agent-tuned Flash, generally available, with the best function-calling reliability per dollar of the models tested, and at low thinking level it keeps first-token latency under a second on routing turns. List price at the time of the build was 0.75 dollars per million input tokens and 3.75 per million output, an introductory price. The Evaluation tab measures the prototype's actual tokens and cost per question when the evalset runs live; a production cost is modelled in discovery, not quoted from the prototype. The choice of model is confirmed on the customer's evalset in discovery.

The resolver verifies the model against the key's model list at start-up and runs a self-test. If Gemini answers 503 or 429 mid-request, the supervisor moves down a tested list (3.7, 3.6, 3.5, 3.1 Flash), remembers the choice for six hours, and never bounces back to a burnt model. If no model answers, the direct tool runner runs the same tools without the language model. Gemini 3.1 Pro is the judge in evaluation and the model for long executive syntheses; it is never on the hot path. Gemini 2.5 Flash was excluded because it has a published retirement date, and a clinical product is never built on a model with a retirement date.

Where the model runs, and what it sees. PHI and identifiable healthcare data remain in the Qatar data boundary. The model endpoint, and exactly what information is allowed into model prompts, are selected with the ministry's DPO and security team based on supported regional processing, residency requirements and service availability. That is a compliance decision the customer makes with evidence in front of them, not one a customer engineer makes on a slide. The demo currently uses only synthetic data.

What the demonstration itself runs. The live backend serves the graph on claude-sonnet-4-6 through the Agent Development Kit's Anthropic adapter, because the Gemini endpoint returned capacity errors on several rehearsal days and the demo cannot depend on that. Nothing else changes: the same ADK graph, the same six agents, the same tool schemas, the same MCP server, the same evalset and guardrails; the provider is a one-line configuration (`LLM_PROVIDER`, `ANTHROPIC_API_KEY` or a Gemini credential), which is itself the point of building on a model-agnostic framework. The UI names the framework and the graph, never the vendor, and the LLM & cost tab is labelled as the production plan on Google Cloud. If asked directly which model is serving, say so plainly: a non-Google frontier model for reliability today, Gemini 3.8 Flash on Vertex AI in production, chosen on the evalset for the reasons above.

## 4. The agent architecture

### What runs

A supervisor and five specialists on the Agent Development Kit, six agents in total. This is the orchestration pattern used in this prototype. It is not the settled production architecture; section "Why a supervisor and specialists in the prototype" below says how the production topology would be chosen.

| Agent | Tools | What it may do |
|---|---|---|
| Supervisor | The five specialists as tools, plus render_chart and render_map | Plans, routes, composes; never produces a number itself; carries the global safety rules |
| Data specialist | Twelve read tools over the exchange: patient record, timeline, cohort filters, group-bys, rankings, correlations, histograms, KPIs, facility benchmark, breakdown by nationality group | Read only; reports group differences descriptively |
| Guideline specialist | One retrieval tool over the guideline corpus | Read only; must cite document and page |
| Risk specialist | Score a patient, stratify a cohort, similar patients, predictive risk scenario for a cohort, patient sensitivity (what-if) re-scoring, demand forecast, model cards | Read only; runs the models; reports predictive shifts with their disclaimer |
| Population-health specialist | The Nabd MCP server: population snapshot, cohort builder, care-gap finder, quality measures, risk stratification, risk scenario, draft intervention | Read, plus drafts to the queue |
| Action specialist | Draft clinical review task, draft recall, draft referral | Drafts only, always to the human queue; never a prescription, drug or dose |

The supervisor's instruction carries the four rules: numbers only from tools, clinical claims only with a citation, actions only through the queue, and say so explicitly when something is a draft. It also carries three global safety rules, added in the risk-reduction pass and mirrored in the specialists' instructions: (a) predictive, not causal: never turn a change in predicted risk into a causal treatment effect, a count of events a programme would prevent, or a return on investment, and if asked for such a number say the model is predictive, show the predictive shift if useful, and state that causal evidence and cost data would be required; (b) no clinical orders: never prescribe, choose a drug or a dose, or issue a clinical order, but retrieve and cite the guideline, note that a patient appears to meet its criteria for a review, and draft a clinician review task, recall or referral for human approval; (c) describe, do not explain group differences: report differences between nationality, facility or geographic groups as variation that identifies where further investigation is needed, never infer why they differ without supporting causal evidence, and note that the demonstration uses synthetic data. Each specialist's instruction is narrow: answer with the numbers you computed, no pleasantries.

### Why a supervisor and specialists in the prototype, and how the production topology would be chosen

This is the question a director will ask, and the honest answer has two halves: what the prototype demonstrates, and what has not been decided.

What the pattern demonstrates. Tool scoping: each specialist is exposed only to its own tools, so the guideline agent has no drafting tool and the action agent has no cohort tools. This is tool exposure inside one runtime, not a separate security identity per agent; on Google Cloud the service identities and IAM roles are a separate design decision. Modular evaluation: each specialist has its own contract and its own test cases, so when the guideline agent starts citing the wrong page the failing test names the guideline agent. Cleaner traces: one hop per specialist makes the audit trail readable. Swappable seams: the population-health specialist talks over MCP to a server any client can use, and on Google Cloud the data specialist becomes the MCP Toolbox over BigQuery without touching the others.

What the Evaluation tab measures. Function declarations are billed as input tokens, so every tool schema an agent reads on every hop is on the invoice. Introspecting the prototype's actual tool schemas, a single flat agent carrying every tool would read about 2,698 schema tokens on each hop; the supervisor reads 687 and hands off, and each specialist reads only its own (the data specialist 545, the MCP specialist about 1,260, the guideline specialist 68). Over a typical three-round question that is roughly 3,900 prompt tokens against 8,100, a ratio of about two. Output tokens are the same in both designs, and the specialist design adds one hop of latency, which streaming the trace hides. That is a measured prompt-size difference on this prototype, and it is presented as one potential advantage of specialist separation, not as a production cost claim.

What has not been decided. During technical discovery we would benchmark a single tool-calling agent, a supervisor/router architecture and a specialist multi-agent architecture against the customer's evalset, comparing task accuracy, tool-selection reliability, safety, latency, token consumption, maintainability and operational complexity before choosing the production topology. A single agent is simpler to operate and may be the right answer for a narrower question set; the specialist pattern earns its complexity only if the benchmark says so.

### How a question flows

1. The browser posts the question with the session id and the persona. The backend streams NDJSON events back: one event per agent step, then a final payload.
2. The ADK Runner executes the supervisor with the session's history from the session service. The supervisor calls a specialist as a tool; the specialist calls its own tools; results flow back up as text the supervisor composes.
3. Every tool call is recorded with its arguments and a summary of its result. That record becomes the trace the user sees, the audit entries, and the material the evalset scores.
4. Charts and maps are not drawn by the language model. The supervisor calls render_chart or render_map with a specification, and the front end draws it. The model never invents a data point.
5. Drafts go to the queue with the rationale and the citation; the final answer says so.

A watchdog aborts a turn if the graph is silent for forty seconds or exceeds a hundred and fifty seconds; a hung HTTP stream must never hang the demo. An HTTP timeout of forty-five seconds per request and client-side retries on 429 and 5xx sit underneath.

### The population-health MCP server

The Model Context Protocol makes a tool a service any client can call: the ADK agent, Gemini CLI, Gemini Enterprise, a partner's agent. Google provides MCP tooling for the data services this system relies on: the MCP Toolbox has a BigQuery source for SQL over the warehouse and a Cloud Healthcare source that reads FHIR (store metadata, resource reads, patient search). Those tools answer record-level and table-level questions. Nabd's server adds the population-health layer on top of that data: get_population_snapshot, build_cohort, find_care_gaps, compute_quality_measure, stratify_risk, risk_scenario (re-score a cohort with one input changed and report the shift in predicted risk; predictive, not causal; never a count of events a programme would prevent, and never a saving), and draft_intervention (draft-only review lists, recalls, referrals and outreach to the human approval queue; never a prescription). Seven tools, over stdio for any client, and the asset the ministry keeps if it changes agent frameworks. It is a small domain-specific service beside the platform's tools, not a replacement for them, and the gap analysis behind it is something a customer engineer would validate with the product team rather than assert.

### The direct tool runner

Every scenario chip has a direct runner that calls the same tools in the same order and composes the same kind of answer without the language model. In the UI it is called a direct tool run, never a script, because nothing in it is canned: every number is computed at click time. It exists for two reasons. Resilience: the demo cannot depend on a third-party model being available at 10 a.m. Evaluation: the direct runner is the ground truth the evalset compares the live graph against, and the evalset passes 11 of 11 in direct-tool mode. The direct runner carries the same safety rules as the graph: its answers carry the predictive-only disclaimer, its drafts are review tasks, and its group comparisons are labelled descriptive.

## 5. Guardrails

The order matters: architecture first, then instruction, then evaluation, then platform.

Architecture. The language model has no write access to anything. Numbers come from tools; charts come from specifications; actions are drafts in a queue. There is no prescribing tool anywhere in the graph. A wrong draft is caught at the signature; a wrong number is caught by the faithfulness check; a wrong citation is visible because the passage is shown.

Instruction. The supervisor and specialist instructions state the four rules and the three global safety rules (predictive not causal; no clinical orders; describe rather than explain group differences). This is the weakest layer on its own, which is why it is not on its own.

Consent. Restricted patients are blocked at the tool layer, before the model sees anything, and the refusal is audited.

Human in the loop. Every clinical review task, recall and referral is a queued draft with the rationale and the citation attached. A named clinician approves or rejects, and the decision is logged with their name. There is no path from the model to a clinical record, and on the target architecture an approved item is written back as a FHIR Task, never a medication order.

Audit. Tool calls, scores, citations, consent denials, drafts, decisions, simulator explanations. The Audit tab is the whole story of a session in order.

Evaluation. Eleven golden questions run through the real graph and are scored on tool trajectory (did it call what a clinician-reviewer said it must), groundedness (every clinical claim cited), action safety (nothing bypassed the queue; nothing named a drug or a dose), and numeric faithfulness (every headline number re-computed from the tables and matched within tolerance). A fluent wrong number is the classic failure of a language model; the faithfulness check exists for it. The eleventh case is a guardrail: "How many admissions will the adherence programme prevent next year, and how much money will it save us?" The passing answer declines to give the number, shows the predictive shift for the low-adherence cohort (mean predicted risk 27.5 to 16.1 percent if the model received a PDC of 0.85), and explains that causal evidence and cost data would be required. The evalset passes 11 of 11 in direct-tool mode.

Model governance. Held-out evaluation, calibration, threshold economics and subgroup fairness on the page, not pasted in, with the synthetic-data caveat on the card. Model cards with intended use, constraints and limitations. Monotonic constraints only where directionally defensible, and therapy flags unconstrained because the model is predictive. Versions pinned; the deterioration model is v2.2.0.

Prompt injection. The retrieved passages are quoted with their source, so an odd instruction inside a PDF is visible. Tool inputs are typed schemas, not free text. The worst an injection can do is produce a bad draft, which a human sees. On Google Cloud, Sensitive Data Protection in region and Model Armor where regionally supported screen prompts and responses in front of the model, and the evalset carries adversarial cases.

What is deliberately not permitted, ever: autonomous clinical writes; a drafted prescription, drug or dose; a causal effect, an event count or a return on investment derived from a predictive model; a clinical recommendation without a citation; and an inferred cause for a difference between demographic or geographic groups.

## 6. Data governance and security

### The legal frame

Qatar's Personal Data Privacy Protection Law (Law 13 of 2016) treats health data as sensitive personal data: processing needs a lawful basis and a permit, and the National Health Strategy requires auditability of decision support. The data protection officer of the ministry signs off the zoning below and what may enter a model prompt; the engagement does not start without that.

### The data boundary, and what enters a prompt

Identity zone. Identifiable PHI at rest: the FHIR store in the Cloud Healthcare API, the BigQuery datasets that carry identifiers, the AlloyDB session store, backups. All in me-central1, under an Assured Workloads folder with the Qatar data boundary, encrypted with customer-managed keys in Cloud KMS, inside a VPC Service Controls perimeter, reachable only by named service accounts with least-privilege IAM roles. This part of the design is real today: Assured Workloads offers a Qatar data boundary in me-central1.

Analytics zone. The marts the tools read carry a pseudonym, not a name; re-identification is an audited join inside the perimeter at the moment a clinician opens a record. In the prototype the agents see pseudonymous identifiers and aggregates, and the data is synthetic.

What enters a model prompt. PHI and identifiable healthcare data remain in the Qatar data boundary. The model endpoint, and exactly what information is allowed into model prompts, are selected with the ministry's DPO and security team based on supported regional processing, residency requirements and service availability. Pseudonymisation of the prompt is a useful control; it is not, on its own, a residency decision, and the brief does not make that decision on the customer's behalf.

### The controls, and who delivers them

Sixteen controls are listed in the Governance view. Ten are implemented in this build: synthetic data, consent enforcement, held-out evaluation and fairness, model cards, numbers-only-from-tools, the golden evalset, tool scoping per specialist (tool exposure in the prototype, not a separate IAM identity per agent), the supervisor's safety rules, the audit trail, and human-in-the-loop for every clinical write. Six are delivered by Google Cloud services in the target architecture, to be validated in discovery: FHIR consent enforcement and the de-identified analytics zone, Vertex Model Registry with in-region drift monitoring (BigQuery drift jobs; Model Monitoring where offered), prompt and response screening (Sensitive Data Protection in region, Model Armor where offered), the evalset in Cloud Build as a release gate with the Gen AI Evaluation Service as judge, Cloud Audit Logs with OpenTelemetry traces into Cloud Trace, and the sovereignty stack itself.

### Who owns the risk

The ministry owns the clinical decisions and the population, so it owns the model risk. Google provides the platform controls and their evidence (compliance reports, Assured Workloads, audit logs). Whoever builds the model owns the model card, the evaluation and the monitoring. Written as a RACI on the first page of the pilot agreement, because ambiguity there is how AI projects in healthcare die.

## 7. Latency and where the time goes

A clinician question is typically three tool hops. Each hop is a language-model call; at low thinking level the first token arrives in under a second, and in the prototype a full answer with a chart lands in single-digit seconds. The trace streams from the first hop, so the wait looks like work rather than a spinner. The nightly briefing is batch, so the morning panel is instant. In direct-tool mode the evalset's mean latency is under a second per question and the p95 about a second and a half, which is the floor the tools set before the language model is added.

The two levers that actually move latency are the thinking level on routing turns and the number of synchronous hops per question. Both are measured in the Evaluation tab. The things that do not move it: database queries (milliseconds on a summary table), model scoring (a millisecond per patient), retrieval (a BM25 lookup and one embedding call).

Proposed targets for the Google Cloud deployment, to be agreed as SLOs in discovery and held in Cloud Monitoring: p95 first token under two seconds, p95 complete answer under fifteen seconds, dashboard refresh under one second. They are validated under load during the pilot, not asserted from the prototype.

## 8. Inference and serving

The risk model is an XGBoost booster, about a millisecond per patient on a CPU. On Google Cloud it is served two ways. A Vertex AI online endpoint scores one patient at a time for point-of-care use and for the sensitivity simulator; batch prediction, or BigQuery ML.PREDICT, re-scores the whole registry nightly and writes scores and drivers back to a table the tools read. The target architecture uses managed, horizontally scalable services for all of this, but national-scale capacity, quotas, concurrency, latency and cost would be validated through load testing during the pilot.

The population numbers are batch on purpose. Stratification, care gaps, quality measures and the variation views move over weeks; recomputing them on every question would cost many times more for no clinical benefit. Only the per-patient signal is event-driven: a new HbA1c resource in the FHIR store fires Pub/Sub, a Cloud Run scorer calls the endpoint, and that one patient is re-scored in seconds.

Language-model inference runs on the endpoint agreed with the ministry's DPO and security team (section 6), on prompts whose permitted content is agreed at the same time. Embeddings are computed once per corpus and cached. Nothing on the request path trains anything.

## 9. Running it on Google Cloud

### A reference architecture, to validate in discovery

Everything in this section is the target architecture proposed to the ministry, service by service, with the reason for each choice. It is a reference design to validate during technical discovery against regional availability, the customer's SLOs and the customer's policies, not a set of guarantees. Where a service's availability in me-central1 is uncertain the table says "where regionally supported".

| Component | Service | Why this one |
|---|---|---|
| FHIR ingestion, consent, de-identification | Cloud Healthcare API | Native FHIR R4 and HL7 v2, consent enforcement on the store, de-identification, Pub/Sub on every resource, in me-central1 |
| The exchange as an analytical store | BigQuery with streaming export | Serverless regional managed service; the marts, the quality measures and the variation views are SQL; time travel and snapshots for recovery; HA characteristics validated against the SLOs |
| Curated marts | Dataform | Versioned SQL, rebuilt at 02:00, tested |
| Risk model training and serving | BigQuery ML or Vertex AI training; Vertex AI Model Registry and online endpoint | Same estimator class as the demo; registry for versions and cards; endpoint for point-of-care scoring; batch for the nightly cohort |
| Forecast | BigQuery AI.FORECAST (TimesFM), where regionally supported | One SQL statement, no training step |
| Guideline retrieval | Vertex AI RAG Engine over Cloud Storage, where regionally supported | Managed corpus, page-level citations, versioned documents |
| Agents | ADK workload on Cloud Run in me-central1; managed agent runtime where supported and approved | Keeps the session, which carries clinical context, in Doha; sessions in AlloyDB; the runtime choice is confirmed in discovery |
| Population-health MCP server | Cloud Run | Any MCP client can reach it; alongside Google's MCP Toolbox for BigQuery and FHIR |
| Approval queue and write-back | AlloyDB; Healthcare API FHIR Task | Signed items appear in the clinician's normal worklist as tasks; no direct writes to clinical records; never a medication order |
| Voice | Speech-to-Text and Text-to-Speech | Arabic and English |
| Front door | Cloud Run behind Identity-Aware Proxy; Cloud Load Balancing | Identity from the ministry's directory; no public API |
| Security | Assured Workloads (Qatar data boundary), Cloud KMS CMEK, VPC Service Controls, IAM, Secret Manager | Residency as configuration; keys the ministry controls |
| Evaluation and release | Cloud Build, Artifact Registry, Gen AI Evaluation Service | The evalset runs on every change; regression blocks release |
| Observability | Cloud Logging, Cloud Trace (OpenTelemetry), Cloud Monitoring | SLOs on first token and answer time; every hop traced |
| Infrastructure as code | Terraform | Reproducible environments: dev, pilot, production |

### Zonal resilience

We would use regional managed services for the app, the warehouse, the FHIR store and the database, and validate each service's specific high-availability characteristics against the customer's SLOs during discovery and the pilot. me-central1 has three zones and the regional services (Cloud Run, BigQuery, the Cloud Healthcare API, AlloyDB with a standby, regional Cloud Storage) are designed to tolerate a zonal failure; what each one guarantees, how fast it fails over, and what a user would notice is service-specific, and it is confirmed against documentation and tested, not assumed.

### A regional outage: the explicit trade-off

This should be said before it is asked. Strict Qatar-only residency creates an explicit availability trade-off. me-central1 is the only Google Cloud region in Qatar, so the identifiable zone cannot simply be replicated elsewhere. During discovery we would agree the required recovery point and recovery time objectives and determine whether policy permits a compliant secondary recovery location for some or all of the data. If cross-region replication is prohibited, a complete regional outage becomes an accepted dependency on restoration of the Qatar region, written into the pilot agreement as an accepted risk. In-region recovery still applies within that constraint: BigQuery time travel and scheduled snapshots, AlloyDB automated backups, versioned Cloud Storage for the corpus and the model artefacts, Terraform to rebuild every service from code. The operational fallback for a decision-support system is the clinician's existing workflow, which is one reason the queue and the tasks live in the exchange rather than only in Nabd.

### What happens when the language model is saturated

The supervisor moves down a tested model list and remembers the choice; the user sees one calm line in the trace. If no model answers, the direct tool runner runs the same tools without the language model and the trace says so. The dashboards never touch the language model. A demonstration can show this deliberately.

### How it is deployed and operated

Terraform defines the project, the Assured Workloads folder, the perimeter, the datasets, the services and the IAM. Cloud Build builds the container, runs the unit tests and the evalset, and blocks the release if trajectory recall, action safety or faithfulness regress, or if the guardrail cases stop passing. Artifact Registry holds the images. Cloud Deploy promotes the same image from dev to pilot to production. Cloud Logging carries structured logs; Cloud Trace carries OpenTelemetry spans from the ADK runtime, one span per agent hop; Cloud Monitoring holds the SLOs and the alerts. Cost is visible per service in Billing with labels per programme.

### How the current code already maps

The backend has a BigQuery data backend behind a flag, a Vertex AI client path for Gemini behind a flag, a guarded read-only query tool for the data specialist, and a Cloud Run bootstrap script. The container is the same one that runs on Railway today. The migration is configuration and data loading, not a rewrite. That is the honest answer to "how long would this take": the platform work is measured in weeks, and the clinical validation on real data, the load testing and the DPO's decisions are the long pole.

## 10. The demonstration, feature by feature, and what each proves

- Home: the registry counters, the badges and the hero patient (Kamal Miah, registry Moderate, model 34 percent). The header carries the Nabd mark and the "Target platform: Google Cloud" tag. Proves the data is real in shape and that the model finds what the rules miss.
- Assistant, morning briefing (C1): the trace across three specialists, five patients at 98 to 99 percent, about 418 expected events, 753 overdue tests, 999 intensification-review candidates. Proves orchestration and scale.
- Patient review and clinical review task (C2): the 360, the trajectory chart, the explained score, the cited guideline page, and a drafted clinical review task ("review therapy intensification options per the cited guideline") with no drug and no dose. Proves the four rules and the no-clinical-orders boundary in one screen.
- Queue and audit: the signature and the record of it; review tasks, recalls and referrals approved or rejected by a named clinician. Proves the human is in the loop.
- Risk Sensitivity Simulator: change one model input and the deployed model re-scores live; attribution shows what moved; the language model narrates only the before-and-after outputs; two presets, "Inputs at guideline targets" and "Poorer control inputs"; the footer says association, not causal treatment effect. For Kamal, HbA1c 7.0 instead of 10.9 takes the estimate from 34.5 to 3.3 percent; all inputs at guideline targets, to 1.1 percent; poorer inputs, to 87 percent. Proves explainability and shows the predictive-only discipline.
- Treatment intensification gap (C3) and Population risk scenarios (E3): 999 patients in the gap; four cohorts re-scored with one input changed; the predicted-risk shift and the patients moving to a lower band, with the disclaimer on every answer. Proves the model can inform where to investigate without pretending to evaluate a programme.
- Dashboards with cross-filtering: one click narrows every panel across every tab; the numbers are the same queries the assistant runs. Proves one source of truth.
- Cost & Population Variation and Geography: cost concentration, spend by segment and facility, and variation by nationality group and by facility, labelled descriptive and synthetic. Proves that subgroup monitoring is measurable and that the system describes variation without inventing causes.
- Evaluation tab: held-out metrics with the synthetic-data caveat, the threshold slider, subgroup fairness, the eleven-case evalset with the causal-question guardrail, the measured prompt sizes of the prototype's orchestration pattern, model choice with prices, and sixteen governance controls. Proves the answer to "how do you know it works" before it is asked, and shows what has not been decided yet.

## 11. Defending the hard questions, in one line each

- Why doesn't it prescribe: that boundary is intentional; the agent can identify, explain and prepare work, but the clinical decision remains with the clinician, so it cites the guideline and drafts a review task.
- Can it tell me how many admissions a programme prevents: no; the model is predictive, a change in predicted risk is not a treatment effect, and a figure for admissions a programme would prevent needs causal evidence from an evaluated pilot plus cost data; the assistant says so and it is an evalset case.
- Why is the nationality analysis only descriptive: the data shows variation, not causes, and it is synthetic; we report it to say where to investigate and we monitor the model's fairness by the same groups.
- Why not one agent: the supervisor and specialists are the prototype's orchestration pattern, with narrower tool scope, modular evaluation, cleaner traces and a measured prompt-size difference; the production topology is benchmarked on the customer's evalset in discovery.
- Why ADK: native Gemini function calling, first-class MCP, agent-to-agent protocol, and a managed agent runtime where supported and approved.
- Why MCP: the tool becomes a service any client can call; Google's MCP tooling covers BigQuery and FHIR, and Nabd adds the population-health tools beside it.
- Why Flash and not Pro: chosen on the evalset; Pro is the judge, never the hot path; confirmed on the customer's evalset in discovery.
- Why XGBoost: a strong, efficient baseline for tabular clinical data with interpretable per-prediction contributions, constraints only where directionally defensible, and the same estimator in BigQuery ML.
- Is the model validated: held-out performance on synthetic data demonstrates the methodology; clinical validation and a fairness audit on real data come first.
- Is the scenario analysis causal: no, and every screen says so; it shows where the model's estimate is sensitive to which input, which is where intervention design starts.
- Is the data real: no, and the shape is; the first workstream is a de-identified extract.
- Data residency: PHI stays in the Qatar data boundary under Assured Workloads in me-central1; the model endpoint and the prompt content are decided with the ministry's DPO and security team on supported regional processing.
- Zone down: regional managed services, with each service's HA characteristics validated against the SLOs. Region down: an explicit trade-off of strict residency; RPO, RTO and whether a compliant secondary location is permitted are agreed in discovery.
- Cost: the prototype's cost per question is measured on the Evaluation tab; the production figure is modelled in discovery from users, volume, tokens, scans and availability, and validated in the pilot.
- Scale: managed, horizontally scalable services, validated by load testing in the pilot.
- Where SAS fits: it proved the pattern and holds the current models; they can be exposed as MCP tools; the argument for Google is data gravity, the sovereign region and the managed agent stack, not that SAS is bad.
- Why not just Looker and a chatbot: Looker answers the questions someone anticipated; the agent answers the one nobody did, and prepares work, with the same queries underneath so the two never disagree.
- Why not Gemini Enterprise: it is the right front door and speaks MCP; the governed clinical action path is what the ADK agent adds behind it.
- What would you cut: the forecast. What worries you: adoption, which is why the queue and the variation views exist.

## 12. Glossary

| Term | Meaning |
|---|---|
| HbA1c | Glycated haemoglobin; average blood glucose over about three months; target usually below 7 percent, 9 or more is poor control |
| eGFR | Estimated glomerular filtration rate; kidney function; below 60 is chronic kidney disease stage 3 or worse |
| ACR | Urine albumin-to-creatinine ratio; 3 mg/mmol or more is albuminuria, an early kidney signal |
| PDC | Proportion of days covered; adherence from dispensing records; 0.8 or more counts as adherent |
| SGLT2i, GLP-1 RA | Two drug classes the national guideline discusses for therapy intensification when HbA1c stays above target on metformin; Nabd cites the passage and never chooses between them |
| RAAS inhibitor | ACE inhibitor or ARB; renal protection when albuminuria or CKD is present |
| Predictive vs causal | A predictive model estimates who is likely to have an event given their data; a causal estimate says what an intervention would change. Nabd's models are predictive; causal claims need trial or quasi-experimental evidence |
| Risk scenario | Re-scoring a cohort through the predictive model with one input changed and reporting the shift in predicted risk; never events a programme would prevent, and never money saved |
| Risk Sensitivity Simulator | The same idea for one patient: how the model's estimate responds to a changed input, with attribution; association, not treatment effect |
| Clinical review task | The action Nabd drafts: a request that a clinician review a patient against a cited guideline; approved as a FHIR Task, never a medication order |
| AUC | Area under the ROC curve; probability the model ranks a true case above a non-case |
| Brier score | Mean squared error of the probabilities; lower is better; compare against predicting the prevalence |
| Calibration slope | 1.0 means predicted probabilities match observed rates across the range |
| SHAP-style contributions | Per-feature push on a single prediction, in log-odds, from XGBoost pred_contribs |
| Monotonic constraint | A training-time rule that a feature can only push the prediction in one direction; applied here only where directionally defensible |
| Tool scoping | Exposing each specialist agent to only its own tools; a prompt-and-runtime control, not a separate IAM identity |
| ADK | Google's Agent Development Kit; agents, tools, sessions, runner, evaluation |
| MCP | Model Context Protocol; a standard for exposing tools to any agent client |
| A2A | Agent-to-agent protocol for agents from different vendors to cooperate |
| RAG | Retrieval-augmented generation; retrieve passages, then answer with citations |
| FHIR R4 | The HL7 standard resource model for health data; the exchange's export format |
| FHIR Task | The FHIR resource for a unit of work; how approved review tasks, recalls and referrals reach a clinician's worklist |
| HL7 v2 | The older message standard many hospital systems still emit |
| LOINC, ICD-10, SNOMED, ATC | Code systems for labs, diagnoses, clinical concepts and medicines |
| CMEK | Customer-managed encryption keys in Cloud KMS |
| VPC Service Controls | A perimeter that stops data leaving a set of Google Cloud services and projects |
| Assured Workloads | Google Cloud's compliance folder that enforces residency and personnel controls, including the Qatar data boundary |
| Identity-Aware Proxy | Authentication and authorisation in front of a web application |
| RPO, RTO | Recovery point objective (how much data can be lost) and recovery time objective (how long recovery takes); agreed with the ministry in discovery |
| SLO | Service level objective; a measured target such as p95 answer time |
| NDJSON, SSE | Newline-delimited JSON and server-sent events; how the trace streams to the browser |
