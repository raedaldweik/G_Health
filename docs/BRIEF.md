# Nabd: The Complete Brief

META: A study document for the presenter, not a script to read aloud. It explains and defends every decision in the demonstration and the deck: the business case, the data, every AI model, the agent architecture, the guardrails, data governance, latency, inference, and how the whole thing runs on Google Cloud, including what happens when a zone or a region fails. Numbers are from the live build on 2026-09-10.

## 1. The business case

### Why a diabetes registry, and why this customer

Diabetes is the single most expensive chronic condition a Gulf health system carries, and the one where population management has the clearest evidence base. Qatar sits in the top five countries for adult prevalence in the IDF Diabetes Atlas. The National Diabetes Strategy projected the annual cost of diabetes care rising from about 1.8 billion riyals to 5 billion by 2035. Half of dialysis in the country is attributable to diabetes, and diabetes sits behind a large share of stroke, heart failure, blindness and amputation. Every one of those downstream costs is preceded by years of measurable signals: HbA1c, blood pressure, kidney function, missed tests, missed medicines.

That is the business logic. Deterioration is predictable and expensive, prevention is cheap and slow, and the signals already exist in the exchange. A registry that only describes the population leaves that value on the table. A registry that can find the patients who are about to deteriorate, and can tell someone what to do about them, converts data the ministry already pays for into admissions it does not.

The second reason is customer readiness. This ministry already has a national Health Information Exchange, a diabetes registry, and a predictive programme built on SAS Viya. The data exists, the outcome definitions exist, and the clinical governance exists. A customer engineer looks for exactly that: a customer two stages into a journey, where the third stage is a capability question rather than a data-collection project. It is far easier to sell "ask your registry a question" than "build a registry".

The third reason is that diabetes is the front door to every other chronic programme. Cardiovascular disease, chronic kidney disease, maternal diabetes and obesity share the same data model, the same agent pattern and the same guardrails. The first programme is where the platform is proven; the second is where consumption grows.

### What the ministry buys, in plain terms

- Fewer deterioration episodes. The registry has about 4,000 patients in this demonstration and the model expects about 418 deterioration events in the next twelve months. Each episode costs the system about QAR 18,500 in admission and follow-up. Avoiding a fraction of them pays for the platform many times over.
- Faster answers. A director's question that used to be an analyst's week becomes a conversation. A clinician who could not ask at all now can.
- Programmes chosen on evidence. The simulator prices five candidate programmes on the ministry's own population before budget is committed. Two of them pay back inside twenty-four months; three do not, on cost alone. That is a decision the ministry could not make quantitatively before.
- A defensible system. Every number comes from a tool, every clinical claim from a cited guideline page, every action from a signed human decision, every step in an audit trail. That is what a medical director and a regulator will ask for first.

### Why Google Cloud is the right platform for it

- Doha is a Google Cloud region (me-central1), which turns data residency from a negotiation into a configuration: Assured Workloads with the Qatar data boundary, customer-managed keys, VPC Service Controls.
- The healthcare data plane is native. The Cloud Healthcare API stores FHIR, enforces consent, de-identifies, and streams into BigQuery. Nobody has to build that.
- The analytics and ML plane is one product. BigQuery holds the exchange, BigQuery ML trains the same class of model the demo uses, and Vertex AI serves it. The forecast is one SQL statement.
- The agent stack is first-party. Gemini, the Agent Development Kit, MCP support in the platform, RAG Engine, the evaluation service. The demo already runs on those.
- Price and scale. The customer pays for questions and queries, not for licences, and nothing in the design has a compute ceiling.

### What the ministry would actually spend

Order of magnitude at list prices: around 1,600 dollars a month for a four-site pilot and around 12,600 dollars a month at national scale with twenty thousand questions a day, roughly thirty percent of that in Gemini tokens. At QAR 18,500 per deterioration episode, the national platform costs the equivalent of two to three avoided episodes a month. The programme simulator is how the ministry decides whether that is worth it; the answer in this population is yes by a wide margin.

### How a customer engineer would run this engagement

1. Discovery, two weeks. The registry team, two clinicians, the data protection officer. One question the pilot must answer, written in the customer's words, and the extract that answers it.
2. Architecture workshop, half a day. The diagram in the deck, adapted to their facilities and feeds, signed off. The zoning of identifiable versus pseudonymised data agreed with the DPO.
3. Proof of concept, six to eight weeks. A de-identified extract in BigQuery, the models retrained on their data, the evalset written by their clinicians. Success criteria fixed before the first commit.
4. Pilot, one quarter. Four facilities, a clinical safety case, the approval queue live, adoption measured by approvals rather than by log-ins.
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
| patient_summary | The wide analytical table: one row per patient with the latest values, derived flags, utilisation, cost, the legacy registry score and the outcome label |

The summary table is what the tools, the models and the dashboards read. It is the equivalent of the curated mart that Dataform would rebuild nightly on Google Cloud.

### Why synthetic, and why 4,000

Synthetic because a demonstration must contain zero PHI, and because a customer engineer never carries a customer's data into an interview. The generator is seeded and documented, so every number is reproducible. Its clinical logic is deliberate: HbA1c trajectories drift with adherence and therapy, blood pressure responds to RAAS therapy, kidney function declines with albuminuria and poor control, and the outcome label is drawn from a logistic model of the same drivers, calibrated to a 10.5 percent twelve-month event rate. The machine learning task is to recover those drivers from the tables without seeing the formula.

Four thousand is a deliberate size. Large enough that a model evaluated on a thousand held-out patients with 107 events produces stable metrics; small enough that the whole system runs on one container and every dashboard recomputes in under a second. On Google Cloud the ceiling disappears: BigQuery does not care whether the summary table has four thousand rows or four million.

### The outcome and the legacy score

The label is deterioration within twelve months: an admission for hypo- or hyperglycaemia, diabetic ketoacidosis or hyperosmolar state, foot infection or acute kidney injury, or progression to HbA1c of 10 percent or more. The legacy registry score is the kind of rule-based tier registries run today: points for age over 60, HbA1c over 9, a prior admission, and systolic over 160. It is blind to kidney function, adherence, monitoring gaps, complications and therapy. That blindness is the whole story of the hero patient: the registry calls Kamal Miah Moderate; the model calls him Very High, because it can see what the rules cannot.

### Consent and data quality

Some patients carry a restricted consent status. Every tool that reads a record checks it first; a restricted patient cannot be opened, scored or simulated, and the refusal is written to the audit trail. That is the demonstration equivalent of the Cloud Healthcare API's consent enforcement on the FHIR store.

Data quality is treated as a care gap. An HbA1c that is overdue is either a clinical gap or a missing feed, and both are worth knowing. On real data the first week of any engagement is profiling in BigQuery so that the gaps are numbers rather than fears.

## 3. The AI models

There are four trained models, one embedding model, and the language model. Each has a model card in the product with its version, task, training data, intended use, constraints and limitations.

### Deterioration risk (XGBoost, v2.1.0)

The core model. Gradient-boosted trees, 600 rounds, depth 3, learning rate 0.035, on 27 features: age, sex, BMI and its twelve-month change, years since diagnosis, smoking, HbA1c now and twelve months ago and days since the last test, systolic and diastolic pressure, eGFR, urine ACR and albuminuria, retinopathy, neuropathy, foot-ulcer history, hypertension, metformin, SGLT2 inhibitor or GLP-1 agonist, insulin, RAAS inhibitor, adherence as proportion of days covered, admissions and emergency visits in the last twelve months, the count of diabetes medicines, and the count of open care gaps.

Why XGBoost and not a neural network or a logistic regression. Tabular clinical data at this scale is where gradient-boosted trees are the state of the art; they handle non-linear thresholds (HbA1c above 9, eGFR below 60) natively; they give per-feature contributions a clinician can read; they train in seconds and score in a millisecond; and BigQuery ML has the same estimator, so the same model class trains inside the warehouse on Google Cloud.

Evaluation, all on a stratified 25 percent hold-out the model never saw:

| Metric | Value | What it means |
|---|---|---|
| AUC | 0.854 vs 0.809 for the legacy score | Ranks a patient who will deteriorate above one who will not 85 percent of the time |
| Average precision | 0.573 on a 10.7 percent event rate | Five times better than chance at the top of the list |
| Brier score | 0.067 vs 0.096 for predicting the prevalence | Thirty percent better probability estimates than a constant |
| Calibration slope | 0.83 | Slightly over-confident at the extremes; the decile chart shows where |
| Operating threshold | 12 percent | The High band; sensitivity about 69 percent, specificity about 84 percent, about three reviews per event found |

Bands: Low below 5 percent, Moderate 5 to 12, High 12 to 25, Very High 25 and above. The threshold is a policy choice, not a model property; the Evaluation tab lets the ministry drag it and see what each choice costs in nurse reviews and missed events.

Monotonic constraints. The model is trained with XGBoost monotone constraints that encode clinical priors: the estimate cannot fall as HbA1c, blood pressure, urine ACR, BMI, smoking, admissions, emergency visits, monitoring delay or open gaps rise, and cannot rise as eGFR, adherence, metformin, SGLT2i/GLP-1 or RAAS therapy improve. Without them, a tree model on four thousand patients learns local noise, and the simulator showed blood pressure going down and risk going up for one patient. With them, no lever moves the wrong way for any patient in the registry, and the held-out AUC went from 0.844 to 0.854. It is a governance control that also improved accuracy, and it is the right answer to "how do you know the model is clinically plausible".

Explanations. XGBoost's own per-prediction contributions (the SHAP-style pred_contribs) give each feature's push in log-odds. The patient review shows the top drivers; the simulator shows how each contribution changes when a lever moves, allocated onto the probability change so the bars sum to the difference on the gauge.

Fairness. The Evaluation tab reports true-positive and false-positive rates at the operating threshold by nationality group, gender and age band, computes gaps only over groups with enough events, and shows small groups without judging them. The age gap is prevalence, not bias, and the page says so. On Google Cloud a monthly job re-runs the table and alerts on drift.

### Population segmentation (KMeans, k=4)

Unsupervised clustering over annual cost, model risk, age, open care gaps and admissions, standardised. Four segments, named by their profile: Complex high-cost (672 patients, about QAR 33,000 a year, 13 percent risk), Care-gap heavy (1,535, cheap today, many open gaps), Stable low-touch (1,474), and Rising-risk (319 patients, 65 percent mean risk, moderate cost today). The segments are descriptive, not causal. Their use is the executive narrative: case management pays for itself in the first segment; the second is cheap to fix and its cost is future, not current. On Google Cloud this is BigQuery ML KMEANS in SQL.

### Patient similarity (nearest neighbours)

A k-nearest-neighbour index over twelve standardised clinical features. It answers "patients like this one" for clinical context and for cohort matching. It is feature-space similarity, not outcome-matched controls, and the card says so. On Google Cloud this becomes gemini-embedding-001 patient embeddings with BigQuery VECTOR_SEARCH, which also allows similarity over notes once they are in scope.

### Ambulatory demand forecast (ridge regression)

Trend plus month-of-year seasonality over thirty-six months of encounter volumes, with an 80 percent interval. It forecasts about 5 percent growth in outpatient and telehealth visits over the next twelve months and picks up the summer dip and the Ramadan pattern. It is the weakest model and the least surprising insight, and if something had to be cut this would be it. On Google Cloud it is one SQL call: AI.FORECAST in BigQuery, on the TimesFM foundation model, with no training step.

### Guideline retrieval (BM25 plus gemini-embedding-001)

The national clinical guideline PDFs are chunked once into 445 overlapping passages of about 1,400 characters, cached on disk. Retrieval is hybrid: a BM25 keyword index that always works, plus a semantic index from gemini-embedding-001 at 768 dimensions (Matryoshka truncation of the 3,072-dimension model, which keeps quality and cuts storage four-fold). Scores are blended 45 percent lexical, 55 percent semantic. The embedding matrix is computed once, cached to disk, and committed, so a deployment never re-embeds and never hits an embedding quota at start-up. Every hit carries document, page and the passage, which is what the citation chip shows. On Google Cloud this layer is Vertex AI RAG Engine over a Cloud Storage corpus.

### Gemini

Gemini 3.8 Flash is the model on the hot path: the supervisor and all five specialists. It was chosen on the product's own evalset, not on a leaderboard. It is the agent-tuned Flash, generally available, with the best function-calling reliability per dollar of the models tested, and at low thinking level it keeps first-token latency under a second on routing turns. List price at the time of the build was 0.75 dollars per million input tokens and 3.75 per million output. A three-hop question stays under a cent.

The resolver verifies the model against the key's model list at start-up and runs a self-test. If Gemini answers 503 or 429 mid-request, the supervisor moves down a tested list (3.7, 3.6, 3.5, 3.1 Flash), remembers the choice for six hours, and never bounces back to a burnt model. If no model answers, the scripted engine runs the same tools without the language model. Gemini 3.1 Pro is the judge in evaluation and the model for long executive syntheses; it is never on the hot path. Gemini 2.5 Flash was excluded because it has a published retirement date, and a clinical product is never built on a model with a retirement date.

The prompt only ever carries pseudonymous identifiers and aggregates. That is what makes serving Gemini from the global endpoint acceptable for a Doha customer.

## 4. The agent architecture

### What runs

A supervisor and five specialists on the Agent Development Kit, six agents in total.

| Agent | Tools | What it may do |
|---|---|---|
| Supervisor | The five specialists as tools, plus render_chart and render_map | Plans, routes, composes; never produces a number itself |
| Data specialist | Twelve read tools over the exchange: patient record, timeline, cohort filters, group-bys, rankings, correlations, histograms, KPIs, facility benchmark, equity breakdown | Read only |
| Guideline specialist | One retrieval tool over the guideline corpus | Read only; must cite document and page |
| Risk specialist | Score a patient, stratify a cohort, similar patients, programme simulation, patient what-if, demand forecast, model cards | Read only; runs the models |
| Population-health specialist | The Nabd MCP server: population snapshot, cohort builder, care-gap finder, quality measures, risk stratification, programme simulation, draft intervention | Read, plus drafts to the queue |
| Action specialist | Draft prescription, draft recall, draft referral | Drafts only, always to the human queue |

The supervisor's instruction carries the four rules: numbers only from tools, clinical claims only with a citation, actions only through the queue, and say so explicitly when something is a draft. Each specialist's instruction is narrow: answer with the numbers you computed, no pleasantries.

### Why six agents and not one

This is the question a director will ask, and the answer has four parts. Three are qualitative and one is measured.

Least privilege. Tools are permissions. The guideline agent cannot draft a prescription because it does not have the tool; the action agent cannot read a cohort because it does not have that tool. A single agent with all twenty-plus tools has every permission on every turn, and a prompt injection in one retrieved passage could reach any of them. With specialists, the blast radius of a bad turn is one specialist's tool set.

Independent evaluation. Each specialist has its own contract and its own test cases. When the guideline agent starts citing the wrong page, the failing test names the guideline agent. In a single agent, every regression is a regression of the whole.

Swappability. The population-health specialist talks over MCP to a server that any client can use. On Google Cloud the data specialist becomes the MCP Toolbox over BigQuery without touching the others. Specialists are the seams where managed services are swapped in.

Cost, measured. Since Gemini 3.5, function declarations are billed as input tokens, so every tool schema the model reads on every hop is on the invoice. A single flat agent re-reads all twenty-plus schemas on every hop, about 2,500 tokens; the supervisor reads five agent-tool declarations, under 700, and each specialist reads only its own. At three hops per question that is roughly thirty percent cheaper per question at national scale, and the Evaluation tab shows the arithmetic. The one cost of the design is one extra hop of latency, which streaming the trace hides.

What a single agent would be better at: nothing that matters here. It is simpler to write and slightly faster on trivial questions. For a clinical product the governance properties win.

### How a question flows

1. The browser posts the question with the session id and the persona. The backend streams NDJSON events back: one event per agent step, then a final payload.
2. The ADK Runner executes the supervisor with the session's history from the session service. The supervisor calls a specialist as a tool; the specialist calls its own tools; results flow back up as text the supervisor composes.
3. Every tool call is recorded with its arguments and a summary of its result. That record becomes the trace the user sees, the audit entries, and the material the evalset scores.
4. Charts and maps are not drawn by the language model. The supervisor calls render_chart or render_map with a specification, and the front end draws it. The model never invents a data point.
5. Drafts go to the queue with the rationale and the citation; the final answer says so.

A watchdog aborts a turn if the graph is silent for forty seconds or exceeds a hundred and fifty seconds; a hung HTTP stream must never hang the demo. An HTTP timeout of forty-five seconds per request and client-side retries on 429 and 5xx sit underneath.

### The population-health MCP server

The Model Context Protocol makes a tool a service any client can call: the ADK agent, Gemini CLI, Gemini Enterprise, a partner's agent. Google ships more than fifty managed MCP servers. The MCP Toolbox has a Cloud Healthcare source that reads FHIR, one patient and one store at a time, and the Agent Platform exposes an MCP endpoint that calls a model. What does not exist in that catalogue is a server that lets an agent reason about a population: quality measures, care gaps, cohorts, model-backed stratification, counterfactual programme simulation, and a safe way to act. Nabd's server has those seven tools, runs over stdio for any client, and is the asset the ministry keeps if it changes agent frameworks. It is also the gap memo a customer engineer would send to product in the first month.

### The scripted engine

Every scenario chip has a scripted runner that calls the same tools in the same order and composes the same kind of answer without the language model. It exists for two reasons. Resilience: the demo cannot depend on a third-party model being available at 10 a.m. Evaluation: the scripted runner is the ground truth the evalset compares the live graph against. Nothing in it is a canned number; every figure is computed from the tables at click time.

## 5. Guardrails

The order matters: architecture first, then instruction, then evaluation, then platform.

Architecture. The language model has no write access to anything. Numbers come from tools; charts come from specifications; actions are drafts in a queue. A wrong draft is caught at the signature; a wrong number is caught by the faithfulness check; a wrong citation is visible because the passage is shown.

Instruction. The supervisor and specialist instructions state the four rules. This is the weakest layer on its own, which is why it is not on its own.

Consent. Restricted patients are blocked at the tool layer, before the model sees anything, and the refusal is audited.

Human in the loop. Every prescription, recall and referral is a queued draft with the rationale and the citation attached. A named clinician approves or rejects, and the decision is logged with their name. There is no path from the model to a clinical record.

Audit. Tool calls, scores, citations, consent denials, drafts, decisions, simulator explanations. The Audit tab is the whole story of a session in order.

Evaluation. Ten golden questions run through the real graph and are scored on tool trajectory (did it call what a clinician-reviewer said it must), groundedness (every clinical claim cited), action safety (nothing bypassed the queue), and numeric faithfulness (every headline number re-computed from the tables and matched within tolerance). A fluent wrong number is the classic failure of a language model; the faithfulness check exists for it.

Model governance. Held-out evaluation, calibration, threshold economics and subgroup fairness on the page, not pasted in. Model cards with intended use, constraints and limitations. Monotonic constraints so the model cannot learn implausible directions. Versions pinned.

Prompt injection. The retrieved passages are quoted with their source, so an odd instruction inside a PDF is visible. Tool inputs are typed schemas, not free text. The worst an injection can do is produce a bad draft, which a human sees. On Google Cloud, Model Armor screens prompts and responses in front of the model, and the evalset carries adversarial cases.

What is deliberately not permitted, ever: autonomous clinical writes, and any answer that carries a clinical recommendation without a citation.

## 6. Data governance and security

### The legal frame

Qatar's Personal Data Privacy Protection Law (Law 13 of 2016) treats health data as sensitive personal data: processing needs a lawful basis and a permit, and the National Health Strategy requires auditability of decision support. The data protection officer of the ministry signs off the zoning below; the engagement does not start without that.

### Two zones

Identity zone. Identifiable PHI at rest: the FHIR store in the Cloud Healthcare API, the BigQuery datasets that carry identifiers, the AlloyDB session store, backups. All in me-central1, under an Assured Workloads folder with the Qatar data boundary, encrypted with customer-managed keys in Cloud KMS, inside a VPC Service Controls perimeter, reachable only by named service accounts with least-privilege IAM roles.

Reasoning zone. What the agents see: pseudonymised identifiers and aggregates. The analytics marts carry a pseudonym, not a name; re-identification is an audited join inside the perimeter at the moment a clinician opens a record. This is what makes the language model's region a latency question rather than a PHI question, and it is why Gemini can be served from the global endpoint.

### The controls, and who delivers them

Fifteen controls are listed in the Governance view. Nine are implemented in this build: synthetic data, consent enforcement, held-out evaluation and fairness, model cards, numbers-only-from-tools, the golden evalset, least-privilege tools per specialist, the audit trail, and human-in-the-loop for every clinical write. Six are delivered by Google Cloud services in the target architecture: FHIR consent enforcement and the de-identified analytics zone, Vertex Model Registry with in-region drift monitoring, prompt and response screening (Sensitive Data Protection in region, Model Armor where offered), the evalset in Cloud Build as a release gate with the Gen AI Evaluation Service as judge, Cloud Audit Logs with OpenTelemetry traces into Cloud Trace, and the sovereignty stack itself.

### Who owns the risk

The ministry owns the clinical decisions and the population, so it owns the model risk. Google provides the platform controls and their evidence (compliance reports, Assured Workloads, audit logs). Whoever builds the model owns the model card, the evaluation and the monitoring. Written as a RACI on the first page of the pilot agreement, because ambiguity there is how AI projects in healthcare die.

## 7. Latency and where the time goes

A clinician question is typically three tool hops. Each hop is a Gemini Flash call; at low thinking level the first token arrives in under a second, and a full answer with a chart lands in five to eight seconds. The trace streams from the first hop, so the wait looks like work rather than a spinner. The nightly briefing is batch, so the morning panel is instant.

The two levers that actually move latency are the thinking level on routing turns and the number of synchronous hops per question. Both are measured in the Evaluation tab. The things that do not move it: database queries (milliseconds on a summary table), model scoring (a millisecond per patient), retrieval (a BM25 lookup and one embedding call).

Targets for the Google Cloud deployment, stated as SLOs in Cloud Monitoring: p95 first token under two seconds, p95 complete answer under fifteen seconds, dashboard refresh under one second. The demonstration meets all three on one container.

## 8. Inference and serving

The risk model is an XGBoost booster, about a millisecond per patient on a CPU. On Google Cloud it is served two ways. A Vertex AI online endpoint scores one patient at a time for point-of-care use and for the what-if simulator; batch prediction, or BigQuery ML.PREDICT, re-scores the whole registry nightly and writes scores and drivers back to a table the tools read. One small CPU replica covers fifty times the national peak; the constraint is never compute.

The population numbers are batch on purpose. Stratification, care gaps, quality measures and equity move over weeks; recomputing them on every question would cost many times more for no clinical benefit. Only the per-patient signal is event-driven: a new HbA1c resource in the FHIR store fires Pub/Sub, a Cloud Run scorer calls the endpoint, and that one patient is re-scored in seconds.

Gemini inference runs on the global endpoint on pseudonymous prompts. Embeddings are computed once per corpus and cached. Nothing on the request path trains anything.

## 9. Running it on Google Cloud

### The target architecture, service by service, and why

| Component | Service | Why this one |
|---|---|---|
| FHIR ingestion, consent, de-identification | Cloud Healthcare API | Native FHIR R4 and HL7 v2, consent enforcement on the store, de-identification, Pub/Sub on every resource, in me-central1 |
| The exchange as an analytical store | BigQuery with streaming export | Serverless, regional, zone-redundant; the marts, the quality measures and the equity views are SQL; time travel and snapshots for recovery |
| Curated marts | Dataform | Versioned SQL, rebuilt at 02:00, tested |
| Risk model training and serving | BigQuery ML or Vertex AI training; Vertex AI Model Registry and online endpoint | Same estimator class as the demo; registry for versions and cards; endpoint for point-of-care scoring; batch for the nightly cohort |
| Forecast | BigQuery AI.FORECAST (TimesFM) | One SQL statement, no training step |
| Guideline retrieval | Vertex AI RAG Engine over Cloud Storage | Managed corpus, page-level citations, versioned documents |
| Agents | ADK on Cloud Run in me-central1 | Agent Engine is not yet in region and the session carries clinical context; Cloud Run keeps it in Doha; sessions in AlloyDB |
| Population-health MCP server | Cloud Run | Any MCP client can reach it; alongside Google's MCP Toolbox for BigQuery and FHIR |
| Approval queue and write-back | AlloyDB; Healthcare API FHIR Task | Signed items appear in the clinician's normal worklist; no direct writes to clinical records |
| Voice | Speech-to-Text and Text-to-Speech | Arabic and English |
| Front door | Cloud Run behind Identity-Aware Proxy; Cloud Load Balancing | Identity from the ministry's directory; no public API |
| Security | Assured Workloads (Qatar), Cloud KMS CMEK, VPC Service Controls, IAM, Secret Manager | Residency as configuration; keys the ministry controls |
| Evaluation and release | Cloud Build, Artifact Registry, Gen AI Evaluation Service | The evalset runs on every change; regression blocks release |
| Observability | Cloud Logging, Cloud Trace (OpenTelemetry), Cloud Monitoring | SLOs on first token and answer time; every hop traced |
| Infrastructure as code | Terraform | Reproducible environments: dev, pilot, production |

### What happens when a zone goes down

Nothing that anyone notices. me-central1 has three zones. Cloud Run is a regional service that spreads replicas across zones and re-routes traffic automatically. BigQuery stores data replicated across zones within the region. The Cloud Healthcare API is regional. AlloyDB runs a highly available primary with a standby in another zone and fails over in about a minute. Cloud Storage regional buckets are zone-redundant. No data is lost, because replication is synchronous within the region, and nobody is paged; the on-call sees an event in Cloud Monitoring after the fact.

### What happens when the region goes down

This is the honest limit, and it should be said before it is asked. Qatar's residency rules keep the data in country, and me-central1 is the only Google Cloud region in Qatar, so cross-region disaster recovery is not available for the identifiable zone. Recovery is in-region: BigQuery time travel (seven days) and scheduled snapshots, AlloyDB automated backups, versioned Cloud Storage for the corpus and the model artefacts, Terraform to rebuild every service from code. The stated targets are a recovery point of 24 hours and a recovery time of 4 hours, agreed with the ministry as an accepted risk. For the pseudonymised aggregates a second copy in another region could be discussed with the DPO, but the default position is that it is not needed for a decision-support system whose fallback is the clinician's existing workflow.

### What happens when Gemini is saturated

The supervisor moves down a tested model list and remembers the choice; the user sees one calm line in the trace. If no model answers, the scripted engine runs the same tools without the language model and the trace says so. The dashboards never touch the language model. A demonstration can show this deliberately.

### How it is deployed and operated

Terraform defines the project, the Assured Workloads folder, the perimeter, the datasets, the services and the IAM. Cloud Build builds the container, runs the unit tests and the evalset, and blocks the release if trajectory recall, action safety or faithfulness regress. Artifact Registry holds the images. Cloud Deploy promotes the same image from dev to pilot to production. Cloud Logging carries structured logs; Cloud Trace carries OpenTelemetry spans from the ADK runtime, one span per agent hop; Cloud Monitoring holds the SLOs and the alerts. Cost is visible per service in Billing with labels per programme.

### How the current code already maps

The backend has a BigQuery data backend behind a flag, a Vertex AI client path for Gemini behind a flag, a guarded read-only query tool for the data specialist, and a Cloud Run bootstrap script. The container is the same one that runs on Railway today. The migration is configuration and data loading, not a rewrite. That is the honest answer to "how long would this take": the platform work is weeks, the clinical validation on real data is the long pole.

## 10. The demonstration, feature by feature, and what each proves

- Landing page: the registry counters and the hero patient. Proves the data is real in shape and that the model finds what the rules miss.
- Assistant, morning briefing: the trace across three specialists, five patients at 98 to 99 percent, 418 expected events. Proves orchestration and scale.
- Patient review: the 360, the trajectory chart, the explained score, the cited guideline page, the draft prescription. Proves the four rules in one screen.
- Queue and audit: the signature and the record of it. Proves the human is in the loop.
- Simulator: sliders re-score the deployed model live; attribution shows what moved; Gemini narrates only the numbers on screen; monotonic constraints keep every lever plausible. Proves explainability and clinical sense.
- Intensification gap and programme simulation: 999 patients, counterfactual re-scoring, honest economics. Proves the model can inform budget, and that the system tells the truth when a programme does not pay back.
- Dashboards with cross-filtering: one click narrows every panel across every tab; the numbers are the same queries the assistant runs. Proves one source of truth.
- Geography: control is concentrated in the capital; the flagged facilities are where the expatriate workforce lives. Proves the equity story is measurable.
- Evaluation tab: held-out metrics, the threshold slider, subgroup fairness, the evalset runner, model choice with prices, governance. Proves the answer to "how do you know it works" before it is asked.

## 11. Defending the hard questions, in one line each

- Why not one agent: least privilege, independent evaluation, swappable seams, and thirty percent cheaper per question because tool schemas are billed tokens.
- Why ADK: native Gemini function calling, first-class MCP, agent-to-agent protocol, and Agent Engine as the managed runtime when it reaches the region.
- Why MCP: the tool becomes a service any client can call; the ministry keeps it if the framework changes.
- Why Flash and not Pro: chosen on the evalset; Pro is the judge, never the hot path.
- Why XGBoost: tabular data, readable contributions, monotonic constraints, and the same estimator in BigQuery ML.
- Is the simulation causal: no, and the screen says so; it ranks levers on the ministry's own population, a trial confirms them.
- Is the data real: no, and the shape is; the first workstream is a de-identified extract.
- Data residency with Gemini: PHI in Doha under the Qatar boundary; the model sees pseudonyms and aggregates.
- Zone down: invisible by construction. Region down: in-region recovery with stated RPO and RTO, because residency forbids the alternative.
- Cost: cents per question; two to three avoided episodes a month pay for the national platform.
- Where SAS fits: it proved the pattern and holds the current models; they can be exposed as MCP tools; the argument for Google is data gravity, the sovereign region, the managed agent stack and price, not that SAS is bad.
- Why not just Looker and a chatbot: Looker answers the questions someone anticipated; the agent answers the one nobody did, and acts, with the same queries underneath so the two never disagree.
- Why not Gemini Enterprise: it is the right front door and speaks MCP; the governed clinical action path is what the ADK agent adds behind it.
- What would you cut: the forecast. What worries you: adoption, which is why the queue and the equity view exist.

## 12. Glossary

| Term | Meaning |
|---|---|
| HbA1c | Glycated haemoglobin; average blood glucose over about three months; target usually below 7 percent, 9 or more is poor control |
| eGFR | Estimated glomerular filtration rate; kidney function; below 60 is chronic kidney disease stage 3 or worse |
| ACR | Urine albumin-to-creatinine ratio; 3 mg/mmol or more is albuminuria, an early kidney signal |
| PDC | Proportion of days covered; adherence from dispensing records; 0.8 or more counts as adherent |
| SGLT2i, GLP-1 RA | Two drug classes with cardiovascular and renal benefit recommended when HbA1c stays above target on metformin |
| RAAS inhibitor | ACE inhibitor or ARB; renal protection when albuminuria or CKD is present |
| AUC | Area under the ROC curve; probability the model ranks a true case above a non-case |
| Brier score | Mean squared error of the probabilities; lower is better; compare against predicting the prevalence |
| Calibration slope | 1.0 means predicted probabilities match observed rates across the range |
| SHAP-style contributions | Per-feature push on a single prediction, in log-odds, from XGBoost pred_contribs |
| Monotonic constraint | A training-time rule that a feature can only push the prediction in one direction |
| ADK | Google's Agent Development Kit; agents, tools, sessions, runner, evaluation |
| MCP | Model Context Protocol; a standard for exposing tools to any agent client |
| A2A | Agent-to-agent protocol for agents from different vendors to cooperate |
| RAG | Retrieval-augmented generation; retrieve passages, then answer with citations |
| FHIR R4 | The HL7 standard resource model for health data; the exchange's export format |
| HL7 v2 | The older message standard many hospital systems still emit |
| LOINC, ICD-10, SNOMED, ATC | Code systems for labs, diagnoses, clinical concepts and medicines |
| CMEK | Customer-managed encryption keys in Cloud KMS |
| VPC Service Controls | A perimeter that stops data leaving a set of Google Cloud services and projects |
| Assured Workloads | Google Cloud's compliance folder that enforces residency and personnel controls, including the Qatar data boundary |
| Identity-Aware Proxy | Authentication and authorisation in front of a web application |
| RPO, RTO | Recovery point objective (how much data can be lost) and recovery time objective (how long recovery takes) |
| SLO | Service level objective; a measured target such as p95 answer time |
| NDJSON, SSE | Newline-delimited JSON and server-sent events; how the trace streams to the browser |
