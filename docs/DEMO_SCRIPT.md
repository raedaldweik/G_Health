# Nabd — Final Round Script

META: Google Cloud AI Customer Engineer, final round · 45 minutes · deck 10 min · live demo 20 min · Q&A 15 min. Verified against the live build on 2026-09-09. Every number in this script is what the app computed on that day. If the screen shows something different on the day, read the screen. The screen is the truth; that is the point of the product.

## 0. What the panel must walk away believing

- **You start from the customer, not the model.** A real ministry, a real registry, a real programme you worked on, and a specific next step.
- **You build for real.** Trained models evaluated on held-out data, a multi-agent graph on ADK, an MCP server, a human-approval queue, an evaluation harness. Nothing mocked.
- **You know the Google portfolio well enough to say what exists, what does not, and what you built in the gap.** That is the credibility test for a customer engineer.

Everything else is supporting detail. If time collapses, protect these three.

## 1. Timing plan

| Clock | Segment | Minutes |
|---|---|---|
| 0:00 | Opening and framing | 1 |
| 1:00 | Deck, nine slides | 9 |
| 10:00 | Demo: landing page | 1 |
| 11:00 | Act I: the clinician's morning (Kamal Miah) | 7 |
| 18:00 | Risk simulator | 3 |
| 21:00 | Act II: the ministry's view | 5 |
| 26:00 | Trust: the Evaluation tab | 3 |
| 29:00 | Close | 1 |
| 30:00 | Q&A | 15 |

RULE: Check the clock at 18:00 and at 26:00. More than two minutes behind at 18:00: drop the C3 intensification beat and the equity beat, keep the simulator and the Evaluation tab. Behind at 26:00: do Evaluation in ninety seconds, risk model and evalset only. Never cut the close.

## 2. Pre-flight, thirty minutes before

- [ ] Tab 1: the Railway URL. The header shows no warning pill. If it shows "Warming up", wait; it takes under a minute. If it shows a key or capacity warning, the scenario chips still run on the scripted engine with live data; only free-form questions need the key.
- [ ] Tab 2: the same URL, already loaded. This is the parachute if tab 1 misbehaves.
- [ ] Persona set to Dr. Amal Al-Mansoori (clinician) in tab 1.
- [ ] Run "Patient review + draft prescription" once. Confirm the hero is Kamal Miah at about 33%. This also warms Gemini.
- [ ] Queue tab: approve or reject anything left over from rehearsal so the panel sees only today's draft.
- [ ] Open Dashboards → Geography once so the map tiles are cached.
- [ ] Open Simulator once, press Reset. Kamal is preselected.
- [ ] Dashboards: click a bar once (for example "High" in the registry tiers) and clear it, so the cross-filter is warm and you remember where the Clear button sits.
- [ ] Documents tab: the retrieval line should read hybrid. If it says the semantic index is pending, run `python -m scripts.embed_corpus` locally with your key and commit the cache file before the day (see the README).
- [ ] Deck open in PowerPoint presenter view. Notes on your screen only. Slide 1 showing.
- [ ] Browser at 100% zoom, window at least 1,600 px wide. Close every other tab. Notifications off.
- [ ] Phone hotspot ready as a second network. Water within reach. A clock you can see.

## 3. Opening (0:00, one minute)

SAY: Thank you for the time. I will do this in three parts. About ten minutes of context: a customer problem I care about and the architecture I would propose for it. Then twenty minutes inside a working system I built for that problem. The rest is yours for questions. Please interrupt whenever you like. Everything in the demo is live, so we can go wherever a question takes us.

NOTE: Do not narrate your CV. The first slide is the customer, and the deck says who you are by what you chose to build.

## 4. The deck (1:00 to 10:00)

### Slide 1 — Title (1:00, 45 seconds)

SCREEN: Nabd, the Google colours, the subtitle.

SAY: The customer is the health ministry of a Gulf state with a national Health Information Exchange. They already have a diabetes registry and a predictive programme that was built on SAS Viya. I worked on that programme. What I want to show today is the next step: letting any clinician or any director ask the exchange a question and get an answer that is grounded, governed and actionable, and what that looks like on Google Cloud in Doha.

NOTE: Do not name the ministry or the country's institutions on this slide. Qatar as a country and its public statistics are fine; the client is not.

### Slide 2 — The problem (1:45, 60 seconds)

SCREEN: three numbers across the top, three pains below.

SAY: Three numbers frame it. Qatar is in the top five countries for adult diabetes prevalence. The cost of diabetes care is projected to rise from 1.8 to 5 billion riyals a year by 2035. And half of all dialysis in the country is attributable to diabetes.

SAY: What clinicians and health leaders told us is not about those numbers. It is three frustrations. The patient story is fragmented across facilities, tables and PDFs. Care is reactive: risk is recognised at the admission, not before it. And insight is rationed: a director's question becomes an analyst's week, and a clinician cannot ask at all. The registry can describe the population. It cannot yet tell a nurse who to call this morning.

### Slide 3 — From registry to agentic (2:45, 45 seconds)

SCREEN: three stages, the third highlighted.

SAY: The ministry is two stages into this journey. Stage one is the registry: describe. Stage two is the predictive programme: deterioration prediction, risk profiles, visit forecasts, cost impact. Stage three is what I am proposing: ask and act. Agents query the exchange, cite the national guideline, run the models, and draft actions a human signs. The registry and the models are not replaced; they become tools the agent calls.

### Slide 4 — Solution overview (3:30, 60 seconds)

SCREEN: four capability tiles on the left, the controls column on the right.

SAY: Nabd is the Arabic word for pulse. It is one conversation over the exchange, the guidelines and the models. Four capabilities, deliberately the same four as the programme: a diabetic patient 360, risk stratification and visit prediction, guideline-grounded decision support, and population and cost simulation.

SAY: The right-hand column is what makes it usable in a clinical setting. Four controls, all enforced in code and all visible in the demo. Numbers come only from tools; the model narrates and never invents a value. Clinical claims come only with a citation to a document and a page. Actions come only with a signature; drafts wait in a queue for a named clinician. And every step is audited. Arabic and English, by voice. The scope of this build is type 2 diabetes on a 4,000-patient synthetic exchange with zero PHI.

### Slide 5 — How it works (4:30, 75 seconds)

SCREEN: the question at the top, the supervisor, five specialists, the evidence strip.

SAY: One supervisor, five specialists. The supervisor is Gemini Flash on the Agent Development Kit. It plans, routes and composes; it never produces a number itself. The data specialist queries the exchange; on Google Cloud that is BigQuery through the MCP Toolbox. The guideline specialist retrieves from the national guidelines with page citations; on Google Cloud that is RAG Engine. The risk specialist runs the four models; on Google Cloud, a Vertex AI endpoint. The population-health specialist talks over the Model Context Protocol to a server we built; hold that thought. And the action specialist only drafts, into a human approval queue.

SAY: Why five agents and not one? Least privilege: the guideline agent physically cannot draft a prescription. Independent evaluation: each specialist has its own test set. And cost: a single agent re-reads every tool schema on every hop, and function declarations are billed as input tokens. I will show you that measured, not asserted.

### Slide 6 — Reference architecture A, SAS Viya (5:45, 60 seconds)

SCREEN: the SAS diagram.

SAY: Credit where it is due. This is where the pattern was proven, at a federal health entity in the region, and I was part of that build. An orchestrating agent with guideline grounding over a vector store, and an MCP server exposing four tools: SQL over the in-memory CAS tables, a decision flow, model runs, and chart generation. The pattern is right. The question for the ministry is which platform runs it at national scale, in Doha, with managed services underneath.

### Slide 7 — Reference architecture B, Google Cloud in Doha (6:45, 90 seconds)

SCREEN: ingestion subsystem left, serving subsystem right, sovereignty strip at the bottom.

SAY: Read it left to right, the way Google's own RAG reference architecture is drawn. Ingestion: the FHIR exchange and the hospital feeds land in the Cloud Healthcare API, with consent enforcement, de-identification and Pub/Sub events, and stream into BigQuery. Guidelines go to Cloud Storage and into RAG Engine, which gives page-level citations without building a vector pipeline. Vertex AI trains the risk model on BigQuery data, registers it, and serves it on an endpoint.

SAY: Serving: the app on Cloud Run, with Speech-to-Text and Text-to-Speech for Arabic and English. The same ADK graph on Gemini, calling four tool families: Google's MCP Toolbox for BigQuery and FHIR, our population-health MCP server, the Vertex endpoint, and RAG Engine. Actions go to the approval queue and, once signed, back to the EHR as a FHIR Task.

SAY: Underneath: PHI at rest in me-central1 under an Assured Workloads Qatar data boundary, VPC Service Controls, customer-managed keys. Two Doha decisions I want to name now. Gemini is served from the global endpoint, which is acceptable because the agent only ever sees pseudonymised identifiers and aggregates. And the agent runtime is Cloud Run in Doha, not Agent Engine, because Agent Engine is not yet available in me-central1 and the session state carries clinical context.

### Slide 8 — Technical view (8:15, 75 seconds)

SCREEN: three lanes: request path, data path, resilience.

SAY: For the technical questions, three lanes. The request path: one question is one synchronous path, five hops, streamed to the user, p95 under fifteen seconds. Identity-Aware Proxy in front, Cloud Run for the app, the ADK supervisor on Gemini with sessions in AlloyDB, the specialist tools, and the answer with its trace and citations; drafts go to the queue and signed items leave as FHIR Tasks.

SAY: The data path: population numbers are batch. The FHIR store streams into BigQuery, Dataform rebuilds the marts at two in the morning, BigQuery ML re-scores every patient nightly. Only the per-patient signal is event-driven: a new HbA1c fires Pub/Sub and one patient is re-scored in seconds. Streaming the aggregates would cost many times more for numbers that move over weeks.

SAY: Resilience: every service is regional and zone-redundant inside me-central1, so a zone failure re-routes traffic with no data loss and nobody is paged. A region failure is the honest limit of in-country residency: recovery is in-region from BigQuery time travel and AlloyDB and Storage backups, with a stated RPO of twenty-four hours and RTO of four. If Gemini is saturated, the supervisor moves down a tested model list, and if no model answers, the scripted engine runs the same tools without the language model. You will see that engine exists.

### Slide 9 — The demo agenda and the service mapping (9:30, 30 seconds)

SCREEN: three acts on the left, the component-to-service table on the right.

SAY: The next twenty minutes: a clinician's morning, the ministry's view, and under the hood. On the right, what each demo component is on Google Cloud, one line each, for when you ask. One rule for everything you are about to see: every number is computed live by a tool call. Nothing is pre-rendered.

DO: Switch to the browser. Tab 1, landing page.

## 5. The demo (10:00 to 29:00)

### Landing page (10:00, 60 seconds)

SCREEN: the pulse line draws across, the counters finish: 4,000 patients, 193k observations, 80k encounters, QAR 62.4M a year. Badges: 753 HbA1c tests overdue, 7,699 open care gaps.

SAY: Four thousand people with diabetes are in this registry. Seven hundred and fifty-three of them have not had an HbA1c test in six months. Nine hundred and ninety-nine have an HbA1c above eight on metformin alone and meet the criteria for treatment intensification. Nobody is looking for them, because the exchange can find a patient, but it cannot find those patients.

DO: Click "Open the Assistant".

### Act I, beat 1 — Morning panel briefing (11:00, 90 seconds)

SCREEN: persona Dr. Amal Al-Mansoori, Consultant Endocrinologist. Scenario chips. Click "Morning panel briefing". The trace streams on the left: cohort agent, risk agent, population-health agent over MCP. Then a table of five patients at 98 to 99% and a chart of open care gaps by type.

SAY: (while the trace streams) Watch the left-hand side. The supervisor is calling the cohort agent for the registry KPIs, the risk agent to score everyone, and then the population-health agent over MCP for the care gaps. Every hop is on the record, with its arguments and its result.

SAY: (when the answer lands) Five patients the model wants her to review today, out of four thousand. Across the registry it expects about 418 deterioration events in the next twelve months. This briefing ran at six in the morning, not on her command.

### Act I, beat 2 — Patient review and draft prescription (12:30, three minutes)

DO: Click "Patient review + draft prescription".

SCREEN: Kamal Miah, QH-101795. Type 2 for 13.7 years, Al Rayyan Health Center. HbA1c 10.9%, up from 10.2%. A 36-month HbA1c chart. Model 33%, Very High; registry tier Moderate. Drivers: HbA1c, ED visits. A guideline citation. A draft of Empagliflozin 10 mg, pending approval.

SAY: Kamal Miah, forty-eight, type 2 for fourteen years, seen at Al Rayyan Health Center. His HbA1c has gone from 10.2 to 10.9 in a year, on metformin alone. Adherence is fifty-nine percent of days covered. Blood pressure 143 over 93.

SAY: Two things to notice. The registry's rule-based tier says Moderate. The model says thirty-three percent probability of a deterioration event in twelve months, which is its Very High band, and it tells you why: the HbA1c and the emergency visits carry it. This is the patient the registry does not flag and the model does.

SAY: The guideline agent retrieved the page of the national guideline that recommends adding an SGLT2 inhibitor or a GLP-1 agonist at this point, and the action agent drafted empagliflozin 10 milligrams. Nothing is prescribed. It is waiting for Dr. Amal's signature.

DO: Click the citation chip. The guideline passage opens with the page number and a link to the PDF.

SAY: The agent does not memorise medicine. It retrieves the page at question time. Swap the PDF for next year's guideline and nothing is retrained.

DO: Open the agent trace (the details view).

SAY: FHIR read, model score, guideline retrieval, draft. Four hops, four agents, auditable end to end.

### Act I, beat 3 — The queue (15:30, 45 seconds)

DO: Click Queue. The Empagliflozin draft is there, unsigned. Approve it.

SAY: The agent is an assistant, not an actor. She approves. That approval lands in the audit trail with her name on it, next to the model score and the guideline citation that led to it. If she rejects it, that is recorded too.

### Act I, beat 4 — Treatment intensification gap (16:15, 90 seconds)

NOTE: This is the first beat to drop if you are behind.

DO: Back to Assistant. Click "Treatment intensification gap".

SCREEN: 999 type 2 patients with HbA1c ≥8 and obesity or kidney disease, not on an SGLT2 inhibitor or GLP-1 RA. Counterfactual over 24 months: 975 eligible re-scored, 9% relative risk reduction, about 46 events avoided, QAR 847k avoided against QAR 12.5M of therapy, net minus 11.6M. A chart by registry tier. A review list drafted.

SAY: The same question at population scale. Nine hundred and ninety-nine patients meet the intensification criteria. The model re-scored all 975 eligible patients with the therapy applied: about forty-six deterioration events avoided over twenty-four months. And on cost alone it does not pay back: twelve and a half million riyals of therapy against under a million of avoided episodes.

SAY: I want the model to say that, rather than a slide. The case for this programme is clinical, and now the ministry can see exactly what it is paying for and why.

### Risk simulator (18:00, three minutes)

DO: Click Simulator in the top navigation. Kamal is preselected. If any lever is gold, press Reset.

SCREEN: the levers on the left, the gauge at 33.4% Very High, baseline drivers on the right.

SAY: This is the same deployed model, re-scored live as I move a lever. Nothing here is a canned number.

DO: Drag HbA1c from 10.9 down to 8.0.

SCREEN: the gauge falls to 5.0%, Moderate band. The attribution chart shows HbA1c at about minus 27 points.

SAY: Bring his HbA1c to eight and the estimate falls from thirty-three to five percent. The attribution shows HbA1c carrying almost all of it, which is what a clinician would expect and what a model has to be able to show.

DO: Toggle "SGLT2 inhibitor / GLP-1 RA" on.

SCREEN: 3.0%, Low band. The registry percentile drops from the 90th to the mid 50s. One care gap closed. Expected cost minus QAR 5,600 over twelve months.

SAY: Add the drug the guideline asked for: three percent, the Low band, one care gap closed, about five and a half thousand riyals of expected episode cost avoided in a year.

DO: Press "Explain with Gemini".

SAY: (while it streams) Gemini is handed the before-and-after scores, the attribution and the gaps closed, and asked to narrate them for the clinician. It adds no numbers of its own; every figure in that paragraph is on this screen.

SAY: One engineering detail I am proud of. The model is monotonic by construction. It cannot tell you that lowering blood pressure raises risk, or that better adherence makes things worse. That is a constraint applied at training time, not a filter on the output. When we retrained with those clinical priors the held-out accuracy went up, not down.

IF: You are ahead of time, press "Left untreated". The gauge climbs to about 87%. Say: and this is the trajectory if nothing changes.

### Act II, beat 1 — The national picture (21:00, 90 seconds)

DO: Switch persona to Dr. Khalid Al-Kuwari, Population Health Executive. Click Assistant, then "National picture".

SCREEN: mean HbA1c 7.52%, down 0.12 points year on year. 35.7% well-controlled, 15.2% poorly controlled. Facility spread from 18% (Rawdat Al Khail) to 54% (West Bay). Complication burden: 24.4% retinopathy, 19.2% neuropathy, 14.5% CKD. A map of facilities coloured by control.

SAY: Same platform, different altitude. The national mean HbA1c is 7.52 and falling. But the spread between facilities runs from eighteen percent well-controlled to fifty-four. That is an operational lever, not a clinical mystery.

SAY: And the map, drawn by the agent inside the answer: control is concentrated in Doha. The flagged facilities are in the north and around the Industrial Area, where the expatriate workforce lives. Distance from the capital and the access gradient follow the same line.

### Act II, beat 2 — Programme simulation (22:30, two minutes)

DO: Click "Programme simulation".

SCREEN: five programmes over 24 months. HbA1c recall: 723 eligible, 105 events avoided, net plus QAR 1.4M. Adherence support: 796 eligible, 180 events avoided, net plus 1.4M. Blood-pressure programme: net minus 0.9M. Renal protection: net minus 0.4M. Intensification: net minus 11.6M. All five combined: about 452 events avoided.

SAY: Five candidate programmes. Every eligible patient is re-scored through the same model with the programme applied; these are computed, not assumed.

SAY: The HbA1c recall programme and the pharmacist-led adherence programme pay for themselves within twenty-four months. They are cheap, and they reach the patients the model worries about. Drug intensification does not pay back on cost within the horizon. I would rather the model told the minister that than a slide did. Honest analytics is a feature, not a weakness.

### Act II, beat 3 — Equity (24:30, 60 seconds)

NOTE: Second beat to drop if behind. If you drop it, go straight to Dashboards → Registry for fifteen seconds and then Evaluation.

DO: Click "Equity".

SCREEN: mean HbA1c by nationality, from 7.17% (Qatari) to 8.01% (Nepali).

SAY: Mean HbA1c runs from 7.2 for Qatari patients to 8.0 for Nepali patients, and the control rates follow the same gradient. That tracks access, not biology. Multilingual outreach is the cheapest lever on the board, and it is a pillar of the National Health Strategy.

DO: Click Dashboards → Registry. Click the "High" bar in the registry risk tiers. Every panel narrows to those patients and a chip appears at the top right: Registry tier High, 406 of 4,000 patients. Click Clinical Quality: the filter follows. Click Clear.

SAY: Every number on these dashboards is the same query the assistant runs. The briefing and the conversation can never disagree, because there is one source of truth. And the dashboards filter each other: one click on a bar, and every panel, on every tab, answers for that group.

### Trust — the Evaluation tab (26:00, three minutes)

DO: Click Evaluation. The Risk model view.

SCREEN: AUC 0.854 against the legacy score's 0.809. Average precision 0.573 on a 10.7% event rate. Brier 0.067, thirty percent better than prevalence. Calibration slope 0.83. 1,000 held-out patients, 107 events. ROC, precision-recall and calibration charts. Threshold economics with a slider. Subgroup fairness tables.

SAY: This tab answers "how do you know it works" before you ask. Everything on this page is computed from a thousand patients the model never saw. AUC 0.854 against the registry's rule-based score at 0.809. Calibration by decile. A Brier score thirty percent better than just predicting the prevalence.

DO: Drag the operating-threshold slider. The confusion tiles and "reviews per event found" update.

SAY: The model does not choose the threshold. The ministry does, and now they can see what each choice costs in nurse time and in missed events.

DO: Point at the subgroup fairness table.

SAY: True-positive and false-positive rates at the operating threshold by nationality group, gender and age. Small groups are shown but not judged. The age gap is prevalence, not bias, and the page says so.

DO: Click Agent evalset, then Run evalset.

SAY: Ten real questions go through the real supervisor graph and are scored on four things a clinician would demand. Did it call the right tools. Did every clinical claim carry a citation. Did nothing bypass the human queue. And does every number in the answer match a recomputation from the tables. A fluent wrong number is the classic language-model failure. This catches it.

DO: Click LLM & cost.

SAY: Why Gemini 3.8 Flash: chosen on this evalset, not on a leaderboard. It is GA, agent-tuned, and a third of Pro's price. Pro is the judge in evaluation, never on the hot path. And the multi-agent question, measured: a single flat agent re-reads about two and a half thousand tokens of tool schema on every hop; the supervisor reads under seven hundred. Function declarations are billed as input tokens, so that gap is literally the invoice.

DO: Click Governance. Ten seconds.

SAY: Fifteen controls. Nine implemented in this build, six delivered by Google Cloud services in the target architecture. Zero autonomous writes.

### Close (29:00, 60 seconds)

DO: Click Home.

SAY: What you saw runs today on one container. On Google Cloud the same contracts map to managed services. The cohort agent becomes BigQuery over a streamed Cloud Healthcare API FHIR store. The risk model moves to a Vertex endpoint. The forecast becomes AI.FORECAST in BigQuery. The guideline corpus becomes RAG Engine. The same ADK graph runs on Cloud Run in Doha, and on Agent Engine the day it reaches me-central1. PHI never leaves the Qatar data boundary, and the language model only ever sees pseudonymous data.

SAY: I built this in the shape of the job: understand the customer, build on the portfolio, find the gap, prototype the fix, and hand it to the team that ships it. That is my thirty minutes. Over to you.

NOTE: Stop talking. Do not fill the silence.

## 6. Q&A bank

NOTE: Answer in three moves: the direct answer in one sentence, the evidence in one or two, and where it goes next in one. Then stop. If you do not know, say so and say how you would find out; a director is testing judgment, not recall.

### The solution

Q: How do you stop it hallucinating clinical advice?
A: Three walls and a test. Numbers come only from tools; the model narrates, it never invents a value. Clinical claims come only with a citation to a document and page. Actions go only through the approval queue. Then the evalset re-computes every headline number from the tables and fails the case if it does not match. On Google Cloud the same set runs in Cloud Build on every change and on a sample of production weekly, and Model Armor sits on the runtime once it is in region.

Q: Why five agents instead of one? Isn't that just complexity?
A: Three reasons, and one of them is measured. Least privilege: the guideline agent cannot draft a prescription because it does not have the tool. Independent evaluation: each specialist has its own test set. And cost: a flat agent re-reads about 2,500 tokens of tool schema on every hop, the supervisor reads under 700, and function declarations are billed as input tokens. At scale that is roughly thirty percent cheaper per question. The cost of the design is one extra hop of latency, which streaming hides.

Q: Why ADK and not LangGraph or CrewAI?
A: Native Gemini function calling, a first-class MCP client in McpToolset, agent-to-agent protocol built in, and Agent Engine as the managed runtime, so the same graph deploys to Google Cloud without a rewrite. For a Google Cloud customer the framework the platform evaluates, traces and hosts natively is the right default. LangGraph is a fine choice if the customer is multi-cloud; the tools and the MCP server would not change.

Q: Why MCP? Isn't that just function calling with extra steps?
A: Function calling binds a tool to one agent in one framework. MCP makes the tool a service any client can use: our ADK agent, Gemini CLI, Gemini Enterprise, a partner's agent. The population-health server is the asset the ministry keeps if they change agent frameworks. And Google has committed to it: over fifty managed MCP servers, an MCP Toolbox with a Cloud Healthcare source for FHIR, and an MCP endpoint on the Agent Platform for calling models.

Q: What is the gap you found in Google's catalogue?
A: Google's healthcare MCP tools read FHIR: one patient, one store. The Agent Platform MCP endpoint calls a model. Nothing in the catalogue lets an agent reason about a population: quality measures, care gaps, cohorts, model-backed stratification, counterfactual programme simulation, and a safe way to act. We built that server with seven tools. I would send that gap analysis to the Healthcare API product manager in my first month; feeding back to product is in the job description.

Q: Why Gemini 3.8 Flash and not Pro?
A: It was chosen on our own evalset: trajectory recall, groundedness, faithfulness, latency and cost per question. Flash 3.8 is agent-tuned and matched Pro on tool-structured tasks at a third of the cost, with first-token latency under a second at low thinking. Pro 3.1 is the judge in evaluation and the model for long executive syntheses, never the hot path. And I avoided Gemini 2.5 Flash on purpose: it has a published retirement date, and you never build a clinical product on a model with a retirement date.

Q: Latency. Will a clinician actually wait?
A: A typical clinician question is three tool hops, each a Flash call, so five to eight seconds to the full answer. The trace streams from the first hop, so the wait looks like work rather than a spinner. The two levers that matter are thinking level on routing turns and the number of synchronous hops; the evaluation tab measures both. The nightly briefing runs as a batch, so the morning panel is instant.

Q: Data residency. Gemini is not in Doha.
A: We separate the identity zone from the reasoning zone. PHI at rest, the FHIR store, BigQuery, the session store, sits in me-central1 under an Assured Workloads Qatar data boundary with customer-managed keys and VPC Service Controls. The agents see the pseudonymised analytics zone; re-identification is an audited join inside the perimeter. That makes the language model's region a latency question, not a PHI question. The legal frame is Qatar's Personal Data Privacy Protection Law, and the ministry's DPO signs off the zoning.

Q: Why isn't the agent on Agent Engine?
A: Agent Engine is the right managed runtime, but it is not available in me-central1 today, and the conversation state carries clinical context. So the same ADK graph runs on Cloud Run in Doha with sessions in AlloyDB. The day Agent Engine lands in Qatar it is a deploy-target change. Same story for Model Armor and Model Monitoring: in-region equivalents today, Sensitive Data Protection and BigQuery drift jobs, managed services when they arrive. I would rather name the limits of the region than pretend they are not there.

Q: What does it cost to run?
A: Order of magnitude at list prices: around 1,600 dollars a month for a four-site pilot, and around 12,600 dollars a month at national scale with twenty thousand questions a day, roughly thirty percent of it Gemini tokens. One deterioration episode costs the system about 18,500 riyals, so the national platform costs the equivalent of two or three episodes a month. The programme simulation you saw is how the ministry would decide whether it is worth it.

Q: How did you evaluate it?
A: Two layers. The model: a stratified 25% hold-out the model never saw, discrimination, calibration, threshold economics and subgroup fairness, all computed on the page, not pasted in. The agent: a golden evalset of ten questions run through the real graph, scored on tool trajectory, groundedness, safety and numeric faithfulness against a recomputation. On Google Cloud, the Gen AI Evaluation Service adds Gemini Pro as an LLM judge, in CI and on a production sample.

Q: Is the model fair?
A: We report true-positive and false-positive rates at the operating threshold by nationality group, gender and age band, and compute gaps only over groups with enough events. Small groups are shown but not judged. The age gap is a prevalence difference, and the page says so rather than hiding it. On Google Cloud a monthly job re-runs that table and alerts on drift. Fairness is a monitoring discipline, not a one-time certificate.

Q: Why XGBoost? And why the monotonic constraints?
A: Tabular clinical data at this scale, native per-feature contributions that a clinician can read, and BigQuery ML has the same estimator, so on Google Cloud it is a CREATE MODEL statement. The monotonic constraints encode clinical priors: risk cannot fall as HbA1c rises or rise as adherence improves. Without them a tree model on four thousand patients learns local noise, and a slider would show blood pressure going down and risk going up. With them the held-out AUC went from 0.844 to 0.854. It is a governance control that also improved accuracy.

Q: Is the programme simulation causal?
A: No, and I say that on the screen. It is a model-based what-if with stated assumptions: event cost per episode, therapy costs from the medication table, guideline-average effect sizes. It ranks levers; a trial or a stepped-wedge rollout confirms them. That is exactly how I would say it to a minister. The value is that the ranking is computed on their population, not borrowed from a paper.

Q: Is the data real?
A: No. Four thousand synthetic patients, zero PHI. But the shape is real: eight relational tables, LOINC, ICD-10, SNOMED and ATC codes, thirty-six months longitudinal, a FHIR R4 export. Four thousand is big enough for the models to be honest on a thousand-patient hold-out and small enough to run on one container. BigQuery removes that ceiling, and the first real workstream is loading a de-identified extract from the exchange.

Q: Real-time or batch?
A: Both, deliberately. Per-patient signals stream: a new HbA1c result re-scores that patient in seconds through the FHIR store, Pub/Sub and the endpoint. Population metrics batch nightly: stratification, care gaps, quality measures, equity. Streaming the aggregates would cost many times more for numbers that move over weeks.

Q: How does it integrate with the hospital EHRs?
A: Through the exchange, not around it. The Healthcare API takes FHIR R4 natively and HL7 v2 through its own ingestion, so the legacy sites bridge rather than migrate. Write-back is a FHIR Task, which is how the EHRs already receive work items, so an approved recall or prescription draft appears in the clinician's normal worklist. We never write to a clinical record directly.

Q: How does this scale to a million patients?
A: Compute is not the constraint anywhere in the design. Scoring is a millisecond per patient on a CPU endpoint; BigQuery is serverless; Cloud Run autoscales the app and the agent. The variables that actually move cost and latency are Gemini tokens per question and synchronous hops per question, and the evaluation tab measures both. Scale is a token-budget problem, not an infrastructure problem.

Q: Why build a custom agent instead of using Gemini Enterprise?
A: Gemini Enterprise is the right front door for knowledge workers, and it speaks MCP, so the population-health server plugs into it. What it does not give you out of the box is the governed clinical action path: drafts, the approval queue, FHIR write-back, and evaluation on tool trajectories. So Gemini Enterprise at the front, the ADK agent as the clinical backend behind it.

Q: Why not just BigQuery, Looker and a chatbot?
A: Looker answers the questions someone anticipated; the agent answers the one nobody did, and it can act. But Looker belongs in the target architecture for exactly the governed KPIs a ministry publishes, and the dashboards in the demo run the same queries the agent runs, so the two never disagree. It is not either-or. The chatbot without tools, citations and a queue is the thing I would refuse to ship.

Q: Where does SAS fit? Would you tell the ministry to leave SAS?
A: Not on day one, and not as a rip-and-replace. SAS is where the pattern was proven and where the ministry's current models live; those models can be exposed as MCP tools and called by the same agent. The argument for Google is data gravity in the exchange, a sovereign region in Doha, a managed agent stack, and price at scale, not that SAS is bad. Over time BigQuery ML and Vertex reduce the licence footprint, and the customer decides the pace.

Q: What about MedGemma and clinical notes?
A: Everything in the demo is structured data. Clinical notes are a later workstream, and MedGemma is the right model for them: open weights, so it can run in region, on the unstructured parts of the record. The pattern does not change; it is one more specialist with one more tool. I would not start there, because the structured registry already carries most of the signal for deterioration.

Q: Security. What about prompt injection through a guideline PDF or a record?
A: The agent's tools are read-only against the data and draft-only against actions, so an injected instruction can at most produce a bad draft, which a human sees before anything happens. Tool inputs are validated schemas, not free text. Retrieved passages are quoted with their source so an odd instruction is visible. On Google Cloud, Model Armor screens prompts and responses, and the evalset carries adversarial cases.

Q: Why did you put voice in?
A: Because the customer asked for it in the original programme, and because a clinician between patients does not type. Arabic and English through the Web Speech API today, Chirp 3 through Speech-to-Text on Google Cloud. It is a thirty-second beat in the demo and a real adoption lever in a clinic.

Q: What would you cut? What worries you?
A: I would cut the demand forecast: the weakest model and the least surprising insight. I would trade it for a hypoglycaemia-risk loop on the insulin-treated cohort, which prevents admissions. What worries me is adoption, not accuracy. The queue exists so clinicians own the decision; the equity view exists so the ministry owns the gap. Tools do not change outcomes; workflows do.

### The customer engineer role

Q: How would you run this engagement from first meeting to a signed pilot?
A: Discovery first: two weeks with the registry team, two clinicians and the DPO, to agree the one question the pilot must answer and the data it needs. Then a half-day architecture workshop that ends with the diagram you saw, signed off. A six-to-eight-week PoC on a de-identified extract, with success criteria written before the first commit. Then a pilot at four facilities with a clinical safety case. My job across all of it is to be the technical owner of the outcome and to keep the account team, the partner and product informed of what is blocking.

Q: What are the PoC success criteria?
A: Written down before we start, in the customer's words. For the model: discrimination on their held-out data above the registry's current score, calibration within an agreed slope, fairness gaps reported by nationality. For the agent: the golden evalset at a pass rate they set, with faithfulness at one hundred percent because a wrong number is disqualifying. For adoption: a clinician panel uses it for two weeks and the queue shows approvals. For the platform: data never leaves the boundary, and the DPO signs the zoning. If any of those fail, the PoC failed, and we say so.

Q: The customer says their data is not ready.
A: It never is, and the exchange is more ready than most. I would start with the narrowest extract that answers the pilot question, run the profiling in BigQuery in the first week so the gaps are numbers rather than fears, and put data quality on the dashboard as a measure like any other. The care-gap engine in the demo is partly a data-quality engine: an overdue HbA1c is either a clinical gap or a missing feed, and both are worth knowing.

Q: A senior clinician says they do not trust it.
A: Good, that is the right starting position. I would sit with them and their own patients in the simulator, because trust comes from seeing the model agree with their judgment on cases they know, and disagree in ways they can check. I would show them the citation path and the queue, and I would ask them to write the first evalset questions. Clinicians who wrote the tests defend the system. Clinicians who were shown a demo do not.

Q: The customer wants to skip the approval queue to save time.
A: I would say no, and explain why in their terms: the queue is what makes the system defensible to the regulator, the medical director and the patient. Then I would find where the time actually goes and remove that instead: batch the drafts, route by facility, let a nurse pre-review. Speed inside the guardrail, not by removing it. If they insist, that is an escalation to the account lead and to legal, not something a customer engineer decides alone.

Q: How do you work with the account team and partners?
A: The account executive owns the relationship and the commercial; I own the technical outcome and the truth about what the product can and cannot do. Partners build and run; I make sure the reference architecture and the success criteria are clear enough that a partner can deliver them. And I feed product back what the customer needed and could not get, with evidence, which in this case is the population-health MCP gap.

Q: How do you keep current with Google's product changes?
A: A weekly pass over the release notes for Vertex, BigQuery, the Healthcare API and the Gemini models, plus the region table for me-central1, because for Gulf customers the region is the first question. I keep a short list of deprecations, which is how I knew not to build on Gemini 2.5 Flash, MedLM or the Healthcare Natural Language API. And I build small things constantly; the simulator in this demo was two days ago.

Q: What would you do in your first ninety days?
A: Learn the territory's top ten accounts and the three deals that are actually moving. Shadow two customer engineers on real engagements before I lead one. Build one reference asset the whole team can reuse, which is what this demo is meant to become. And send product one well-evidenced gap memo. By day ninety I should be the technical owner on at least one opportunity and known internally as the person to ask about healthcare on Google Cloud in the region.

Q: Tell me about a time you were wrong with a customer.
A: Use a real one. The shape that works: what you claimed, how you found out you were wrong, what you did within twenty-four hours, and what you changed in your process. The panel is testing whether you correct fast and in the open. Do not pick a story where you were secretly right.

### Curveballs

Q: Isn't this over-engineered for a proof of concept?
A: The engineering is in the guardrails, and those are the parts a health ministry will ask for first. Strip them out and it is a chatbot over a database, which is a demo nobody deploys. Everything else is intentionally thin: one container, one region, four models, ten evalset questions. The reference architecture is a target, and the phases are how we get there without paying for all of it on day one.

Q: What if Gemini suggests the wrong dose?
A: It cannot prescribe, so a wrong dose is a wrong draft, and the clinician sees the dose, the guideline page it came from and the model drivers before signing. The dose in the draft is taken from the retrieved guideline text, not generated. And the evalset carries the case: a draft with a dose outside the cited guideline range fails. If it ever reached a patient, that would be a process failure at the signature, and the audit trail would show exactly where.

Q: Who owns the model risk?
A: The ministry owns it, because they own the clinical decisions and the population. Google provides the platform controls and their evidence. Whoever builds the model, us or a partner, owns the model card, the evaluation and the monitoring. I would write that into the pilot agreement as a RACI on the first page, because ambiguity there is how AI projects in healthcare die.

Q: Would this work for another disease or another country?
A: The pattern transfers; the content does not. The agent graph, the MCP server contracts, the evaluation harness and the queue are disease-agnostic. What changes is the registry schema, the guideline corpus, the outcome label and the quality measures. Cardiovascular disease would be the natural second programme for Qatar. Another Gulf country would reuse the architecture and re-do the data residency work for its own regulator.

Q: How long did this take and how did you build it?
A: About two weeks of evenings and weekends, in Python with FastAPI, the Agent Development Kit and the Gemini SDK, XGBoost for the models, React for the front end, deployed on Railway because it was the fastest path to a URL. I used an AI coding assistant as a pair programmer throughout, and I am happy to say so; the architecture, the clinical framing, the evaluation design and every decision in the deck are mine, and I can walk through any file. That is how I would expect a customer engineer to build in 2026.

Q: What do you need from Google to ship this?
A: Three things. Agent Engine, Model Armor and Model Monitoring in me-central1, with a date I can give the customer. A population-health layer in the Healthcare API catalogue, or a partner programme that recognises one. And a reference architecture for sovereign healthcare AI in the Gulf that a customer engineer can hand over, because today each of us is drawing it from scratch.

## 7. Questions to ask them

- How does the customer engineering team in the region divide healthcare and public sector between people, and where would this kind of asset live so others can reuse it?
- What is the blocker you hear most from Gulf customers right now: sovereignty, skills, or something else?
- How is a customer engineer's first year measured here, beyond the numbers?
- What did the strongest customer engineer you have worked with do differently?

## 8. Failure playbook

| If | Then |
|---|---|
| Gemini errors mid-scenario | Nothing to do. The backend falls back to the scripted engine automatically and says so in the trace. Keep talking. |
| The header shows a key or capacity error | Every scenario chip still runs on live data. Only free-form questions need the key. Say: "the scripted engine is the same tools without the language model in the loop." |
| A free-form question goes sideways | "Let me show you the trace of why." The details view turns a miss into a transparency beat. Then run a chip. |
| The Explain button in the simulator returns the templated text | It is grounded in the same numbers. Say so and move on. |
| Wi-Fi dies | Switch to the hotspot. The scripted engine needs no external call after the page has loaded. |
| A number differs from this script | Read the screen. "The screen is the truth; that is the point of the product." |
| They interrupt with a deep question | Answer it, then say "and that is exactly what the next click shows". Every act has a natural re-entry. |
| You lose your place | The Simulator tab is a safe harbour from anywhere: Kamal, one slider, one explanation, one minute. |

## 9. Numbers to have in your head

| Number | Where it comes from |
|---|---|
| 4,000 patients · 193k observations · 80k encounters · 18 facilities | Landing page counters |
| QAR 62.4M annual cost · top 10% of patients = 26% of spend | Landing, Cost & Equity |
| Mean HbA1c 7.52% · 35.7% well-controlled · 15.2% poorly controlled | KPI strip |
| 753 HbA1c tests overdue · 7,699 open care gaps · 1,203 retinal screening overdue | Landing badges, C4 |
| 999 in the intensification gap · 975 re-scored · 46 events avoided · net −QAR 11.6M over 24 months | C3 |
| 418 expected deterioration events in 12 months | C1 |
| Kamal Miah QH-101795: HbA1c 10.2 → 10.9 · registry Moderate · model 33% Very High | C2, Simulator |
| Simulator: HbA1c 8.0 → 5.0% · plus SGLT2i → 3.0% Low · guideline targets → 0.9% · left untreated → 87% | Simulator |
| Facility control spread 18% (Rawdat Al Khail) to 54% (West Bay) | E1 |
| Equity: HbA1c 7.17% Qatari to 8.01% Nepali | E4 |
| Programmes: recall +1.4M · adherence +1.4M · BP −0.9M · renal −0.4M · intensification −11.6M · combined 452 events | E3 |
| Model: AUC 0.854 vs 0.809 · AP 0.573 · Brier 0.067 vs 0.096 · slope 0.83 · 1,000 held out, 107 events | Evaluation |
| Gemini 3.8 Flash $0.75 / $3.75 per million tokens (intro) · Pro 3.1 judge · 2.5 Flash retiring Oct 2026 | LLM & cost |
| Schema tokens per hop: flat agent ≈2,500 · supervisor ≈700 | LLM & cost |
| Governance: 15 controls · 9 implemented · 6 Google Cloud · 0 autonomous writes | Governance |
| Run cost: ≈$1.6k/month pilot · ≈$12.6k/month national at 20k questions/day · QAR 18,500 per episode | Q&A |
| Google Cloud mapping: BigQuery · RAG Engine · Vertex endpoint · ADK on Cloud Run · AlloyDB · FHIR Task | Slide 9 |
