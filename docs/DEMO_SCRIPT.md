# Nabd: Final Round Script

META: Google Cloud AI Customer Engineer, final round · 45 minutes · deck 10 min · live demo 20 min · Q&A 15 min. Verified against the live build on 2026-09-10, after the risk-reduction pass. Every number in this script is what the app computed on that day. If the screen shows something different on the day, read the screen. The screen is the truth; that is the point of the product.

## 0. What the panel must walk away believing

- **You start from the customer, not the model.** A real ministry, a real registry, a real programme you worked on, and a specific next step. Nabd is the ministry's solution, powered by Google Cloud; it is not a Google product.
- **You build for real.** Trained models evaluated on held-out data, a multi-agent graph on ADK, an MCP server, a human-approval queue, an evaluation harness. Nothing mocked.
- **You know where the boundaries are.** A predictive model is not a causal one. The agent identifies, explains and prepares work; the clinical decision stays with the clinician. Group differences are described, not explained. You say these things before you are asked.
- **You know the Google portfolio well enough to say what exists, what you would validate in discovery, and what you built in the gap.** That is the credibility test for a customer engineer.

Everything else is supporting detail. If time collapses, protect these four.

## 1. Timing plan

| Clock | Segment | Minutes |
|---|---|---|
| 0:00 | Opening and framing | 1 |
| 1:00 | Deck, nine slides | 9 |
| 10:00 | Demo: Home | 1 |
| 11:00 | Assistant: morning briefing (C1) | 2 |
| 13:00 | One patient: 360, risk score and explanation, cited guideline, draft review task (C2) | 4 |
| 17:00 | Human approval queue | 1 |
| 18:00 | Risk Sensitivity Simulator | 3 |
| 21:00 | Population dashboards: Registry, then Cost & Population Variation (or Geography) | 3 |
| 24:00 | Trust: the Evaluation tab | 4 |
| 28:00 | Close | 1 |
| 29:00 | Q&A (one minute of buffer inside it) | 16 |

RULE: Check the clock at 18:00 and at 24:00. More than two minutes behind at 18:00: do the simulator in ninety seconds (one input, one preset, no narration) and show only the Registry dashboard. Behind at 24:00: do Evaluation in ninety seconds, risk model and evalset only. Never cut the close. Everything in section 5b ("If time, if asked") is optional and is never started unless you are ahead or a question leads there.

## 2. Pre-flight, thirty minutes before

- [ ] Tab 1: the Railway URL. The header shows the Nabd pulse mark, the small "Target platform: Google Cloud" tag, and no warning pill. If it shows "Warming up", wait; it takes under a minute. If it shows a credentials or capacity warning, the scenario chips still run the same tools directly on live data; only free-form questions and the simulator's narrated explanation need the model.
- [ ] Know what is behind the graph. The live backend runs claude-sonnet-4-6 through the Agent Development Kit's Anthropic adapter (ANTHROPIC_API_KEY on Railway); the ADK graph, tools, MCP server, evalset and guardrails are identical whichever model serves it. The UI names the framework and the graph, never the vendor, and the LLM & cost tab is explicitly the production plan on Google Cloud. If the director asks directly which model is serving the demo, answer straight: "ADK is model-agnostic; today's demo runs on a non-Google frontier model for reliability, and the production plan on Vertex AI is Gemini 3.8 Flash for the reasons on this tab." Never claim the live model is Gemini.
- [ ] Tab 2: the same URL, already loaded. This is the parachute if tab 1 misbehaves.
- [ ] Persona set to Dr. Amal Al-Mansoori (clinician) in tab 1.
- [ ] Run "Patient review + clinical review task" once. Confirm the hero is Kamal Miah at about 34% and that the draft in the answer is a clinical review task, not a drug. This also warms the model connection.
- [ ] Queue tab: approve or reject anything left over from rehearsal so the panel sees only today's draft.
- [ ] Open Simulator once, press Reset. Kamal is preselected. Confirm the two presets read "Inputs at guideline targets" and "Poorer control inputs" and the footer reads "Predictive sensitivity analysis: association, not causal treatment effect."
- [ ] Dashboards: open Registry, click a bar once (for example "High" in the registry tiers) and clear it, so the cross-filter is warm and you remember where the Clear button sits. Open Cost & Variation once. If you intend to use Geography as the second dashboard, open it once so the map tiles are cached.
- [ ] Evaluation tab: open Agent evalset once and confirm the last run reads 11 of 11.
- [ ] Documents tab: the status pill is green and reads 8 documents, the page count and 445 indexed passages. Open one citation chip from a rehearsal answer so you have seen the source passage open.
- [ ] Deck open in PowerPoint presenter view. Notes on your screen only. Slide 1 showing.
- [ ] Browser at 100% zoom, window at least 1,400 px wide. Close every other tab. Notifications off.
- [ ] Phone hotspot ready as a second network. Water within reach. A clock you can see.

## 3. Opening (0:00, one minute)

SAY: Thank you for the time. I will do this in three parts. About ten minutes of context: a customer problem I care about and the reference architecture I would propose for it, to validate with them in discovery. Then twenty minutes inside a working system I built for that problem. The rest is yours for questions. Please interrupt whenever you like. Everything in the demo is live, so we can go wherever a question takes us.

NOTE: Do not narrate your CV. The first slide is the customer, and the deck says who you are by what you chose to build.

## 4. The deck (1:00 to 10:00)

### Slide 1: Title (1:00, 45 seconds)

SCREEN: the title slide: Nabd, the subtitle, your name.

SAY: The customer is the health ministry of a Gulf state with a national Health Information Exchange. They already have a diabetes registry and a predictive programme that was built on SAS Viya. I worked on that programme. What I want to show today is the next step: letting any clinician or any director ask the exchange a question and get an answer that is grounded, governed and actionable. Nabd is the ministry's solution; the target platform is Google Cloud in Doha, and I will say which service sits behind each box as we go.

NOTE: Do not name the ministry or the country's institutions on this slide. Qatar as a country and its public statistics are fine; the client is not. The slides name no Google product anywhere; every Google service is said out loud, and the speaker notes list them slide by slide.

### Slide 2: The problem (1:45, 60 seconds)

SCREEN: three numbers across the top, three pains below.

SAY: Three numbers frame it. Qatar is in the top five countries for adult diabetes prevalence. The cost of diabetes care is projected to rise from 1.8 to 5 billion riyals a year by 2035. And half of all dialysis in the country is attributable to diabetes.

SAY: What clinicians and health leaders told us is not about those numbers. It is three frustrations. The patient story is fragmented across facilities, tables and PDFs. Care is reactive: risk is recognised at the admission, not before it. And insight is rationed: a director's question becomes an analyst's week, and a clinician cannot ask at all. The registry can describe the population. It cannot yet tell a nurse who to call this morning.

### Slide 3: From registry to agentic (2:45, 45 seconds)

SCREEN: three stages, the third highlighted.

SAY: The ministry is two stages into this journey. Stage one is the registry: describe. Stage two is the predictive programme: deterioration prediction, risk profiles, visit forecasts, cost impact. Stage three is what I am proposing: ask and act. Agents query the exchange, cite the national guideline, run the models, and draft work a human signs. The registry and the models are not replaced; they become tools the agent calls.

### Slide 4: Solution overview (3:30, 60 seconds)

SCREEN: four capability tiles on the left, the controls column on the right.

SAY: Nabd is the Arabic word for pulse. It is one conversation over the exchange, the guidelines and the models. Four capabilities, deliberately the same four as the programme: a diabetic patient 360, risk stratification and visit prediction, guideline-grounded decision support, and a population view with predictive risk scenarios.

SAY: The right-hand column is what makes it usable in a clinical setting. Four controls, all enforced in code and all visible in the demo. Numbers come only from tools; the model narrates and never invents a value. Clinical claims come only with a citation to a document and a page. Actions come only with a signature; drafts wait in a queue for a named clinician. And every step is audited. Arabic and English, by voice. The scope of this build is type 2 diabetes on a 4,000-patient synthetic exchange with zero PHI.

### Slide 5: How it works in the prototype (4:30, 75 seconds)

SCREEN: the question at the top, the supervisor ("a language model inside an agent framework"), five specialists, the evidence strip. No product names on the slide.

SAY: This is the orchestration pattern used in the prototype: one supervisor, five specialists. The supervisor is a language model on the Agent Development Kit; in the production plan that is Gemini Flash on Vertex AI. It plans, routes and composes; it never produces a number itself. The data specialist queries the exchange; on Google Cloud that is BigQuery through the MCP Toolbox. The guideline specialist retrieves from the national guidelines with page citations; on Google Cloud that is RAG Engine. The risk specialist runs the four models; on Google Cloud, a Vertex AI endpoint. The population-health specialist talks over the Model Context Protocol to a server we built; hold that thought. And the action specialist only drafts, into a human approval queue.

SAY: I want to be careful about what this pattern is and is not. Each specialist sees only its own tools, which gives narrower tool scope, modular evaluation and cleaner traces, and the Evaluation tab measures the prompt-size difference rather than asserting it. It is not a settled production architecture. During technical discovery we would benchmark a single tool-calling agent, a supervisor and router, and this specialist pattern against the customer's own evalset, on task accuracy, tool-selection reliability, safety, latency, token consumption, maintainability and operational complexity, before choosing the production topology.

SAY: Three rules sit in the supervisor's instruction and are enforced by the tools underneath. It never turns a change in predicted risk into a treatment effect, an event count or a return on investment. It never prescribes or issues a clinical order; it can retrieve the evidence and draft a clinician review task. And it never explains why demographic or geographic groups differ without causal evidence. You will see all three in the demo.

### Slide 6: Reference architecture A, SAS Viya (5:45, 60 seconds)

SCREEN: the SAS diagram.

SAY: Credit where it is due. This is where the pattern was proven, at a federal health entity in the region, and I was part of that build. An orchestrating agent with guideline grounding over a vector store, and an MCP server exposing four tools: SQL over the in-memory CAS tables, a decision flow, model runs, and chart generation. The pattern is right. The question for the ministry is which platform runs it at national scale, in Doha, with managed services underneath.

### Slide 7: Reference architecture B, the cloud-native target (6:45, 90 seconds)

SCREEN: ingestion subsystem left, serving subsystem right, sovereignty strip at the bottom. The boxes are generic (managed FHIR store, analytical warehouse, managed retrieval, model platform, agent runtime); you name the Google service behind each one as you point at it.

SAY: This is a reference architecture: the target we would validate with the ministry during technical discovery, not a set of guarantees. Read it left to right; it follows the same shape as Google's own RAG reference architecture, an ingestion subsystem and a serving subsystem. Ingestion: the FHIR exchange and the hospital feeds land in a managed FHIR store, which on Google Cloud is the Cloud Healthcare API, with consent enforcement, de-identification and an event on every new resource, and stream into the warehouse, which is BigQuery. Guidelines go to object storage and into a managed retrieval service, Vertex AI RAG Engine, which gives page-level citations without building a vector pipeline. The model platform, Vertex AI, trains the risk model on warehouse data, registers it with its card, and serves it on an endpoint.

SAY: Serving: the app runs serverless, on Cloud Run, with Speech-to-Text and Text-to-Speech for Arabic and English. The same supervisor and specialists, on Gemini with the Agent Development Kit, call four tool families: Google's MCP Toolbox for BigQuery and FHIR, our population-health MCP server, the Vertex AI endpoint, and RAG Engine. The agent runtime is an ADK workload on Cloud Run in me-central1, with a managed agent runtime where supported and approved. Actions go to the approval queue, which lives in AlloyDB, and once signed go back to the EHR as a FHIR Task through the Healthcare API. Never as a medication order.

SAY: Underneath: PHI and identifiable healthcare data remain in the Qatar data boundary, which on Google Cloud means me-central1 in Doha under Assured Workloads, VPC Service Controls, and customer-managed keys in Cloud KMS. Which model endpoint is used, and exactly what information is allowed into a model prompt, is a decision we take with the ministry's data protection officer and security team, based on supported regional processing, residency requirements and service availability. I do not make that decision for them on a slide. The demo today uses only synthetic data.

### Slide 8: Technical view (8:15, 75 seconds)

SCREEN: three lanes: request path, data path, resilience. Generic component names on the slide; the Google names are in your notes and in your mouth.

SAY: For the technical questions, three lanes. The request path: one question is one synchronous path, five hops, streamed to the user, with a proposed p95 under fifteen seconds. Identity-Aware Proxy in front, Cloud Run for the app, the supervisor on Gemini Flash via Vertex AI with sessions in AlloyDB, the specialist tools, and the answer with its trace and citations; drafts go to the queue and signed items leave as FHIR Tasks.

SAY: The data path: population numbers are batch. The Cloud Healthcare API FHIR store streams into BigQuery, Dataform rebuilds the marts at two in the morning, BigQuery ML re-scores every patient nightly. Only the per-patient signal is event-driven: a new HbA1c fires a Pub/Sub event and one patient is re-scored in seconds through the Vertex AI endpoint. Streaming the aggregates would cost many times more for numbers that move over weeks.

SAY: Resilience, honestly. For zonal resilience we would use regional managed services and validate each service's high-availability characteristics against the customer's SLOs. Strict Qatar-only residency creates an explicit availability trade-off: during discovery we would agree the required recovery point and recovery time, and determine whether policy permits a compliant secondary recovery location. If cross-region replication is prohibited, a complete regional outage becomes an accepted dependency on restoration of the Qatar region, and that is written down and signed, not discovered later. If the model endpoint is saturated, the supervisor moves down a tested model list, and if no model answers, the same tools run directly without the language model. You will see that path exists.

### Slide 9: The demo agenda and the service mapping (9:30, 30 seconds)

SCREEN: what you will see in the next twenty minutes on the left; on the right, what each demo component becomes at national scale, in generic terms. Name the Google service for each row as you go, or leave it for Q&A.

SAY: The next twenty minutes: a clinician's morning briefing, one patient end to end, the simulator on that patient, the ministry's dashboards, and the evaluation tab. On the right, what each demo component becomes at national scale; on Google Cloud that is BigQuery fed by the Healthcare API, RAG Engine, a Vertex AI endpoint, the same agents on Cloud Run in Doha, AlloyDB for the queue, and the Gen AI Evaluation Service in the release pipeline. One rule for everything you are about to see: every number is computed live by a tool call. Nothing is pre-rendered.

DO: Switch to the browser. Tab 1, Home.

## 5. The demo (10:00 to 29:00)

### Home (10:00, 60 seconds)

SCREEN: the pulse line draws across, the counters finish: 4,000 patients, 193k observations, 80k encounters, QAR 62.4M a year. Badges: 753 HbA1c tests overdue, 7,699 open care gaps. The hero card: Kamal Miah, registry tier Moderate, model risk 34%. In the header, the Nabd mark and the "Target platform: Google Cloud" tag.

SAY: Four thousand people with diabetes are in this registry. Seven hundred and fifty-three of them have not had an HbA1c test in six months. Nine hundred and ninety-nine have an HbA1c above eight on metformin alone and meet the criteria for a treatment intensification review. Nobody is looking for them, because the exchange can find a patient, but it cannot find those patients.

DO: Click "Open the Assistant".

### Beat 1: Morning panel briefing, C1 (11:00, two minutes)

SCREEN: persona Dr. Amal Al-Mansoori, Consultant Endocrinologist. Scenario chips. Click "Morning panel briefing". The trace streams on the left: cohort agent, risk agent, population-health agent over MCP. Then a table of five patients at 98 to 99% and a chart of open care gaps by type.

SAY: (while the trace streams) Watch the left-hand side. The supervisor is calling the cohort agent for the registry KPIs, the risk agent to score everyone, and then the population-health agent over MCP for the care gaps. Every hop is on the record, with its arguments and its result.

SAY: (when the answer lands) Five patients the model wants her to review today, out of four thousand. Across the registry it expects about 418 deterioration events in the next twelve months. Seven hundred and fifty-three overdue tests, nine hundred and ninety-nine intensification-review candidates, eight hundred and eighteen patients with adherence below sixty percent. This briefing ran at six in the morning, not on her command.

### Beat 2: One patient, end to end, C2 (13:00, four minutes)

DO: Click "Patient review + clinical review task".

SCREEN: Kamal Miah, QH-101795. 48, male, Bangladeshi, type 2 for 13.7 years, Al Rayyan Health Center. HbA1c 10.9%, up from 10.2%. A 36-month HbA1c chart. Model 34%, Very High; registry tier Moderate. Drivers: HbA1c, ED visits. A guideline citation (MOPH NCG T2DM Adults Elderly, page 14). A drafted clinical review task, "review therapy intensification options per the cited guideline", pending approval. The last line reads: Nabd does not choose a drug or a dose; the clinical decision is yours.

SAY: Kamal Miah, forty-eight, type 2 for fourteen years, seen at Al Rayyan Health Center. His HbA1c has gone from 10.2 to 10.9 in a year, on metformin alone. Adherence is fifty-nine percent of days covered. Blood pressure 143 over 93.

SAY: The 360 first. The cohort agent assembled this from the exchange at question time, with consent checked before the record was opened: conditions, the three-year HbA1c trajectory, current therapy, utilisation, open gaps.

SAY: Then the risk score and its explanation. The registry's rule-based tier says Moderate. The model says thirty-four percent probability of a deterioration event in twelve months, which is its Very High band, and it tells you why: the HbA1c and the emergency visits carry it, and each driver is shown with its contribution. This is the patient the registry does not flag and the model does.

SAY: Then the guideline. The guideline agent retrieved the passage of the national guideline that covers therapy intensification when HbA1c stays above target on metformin, and the answer says Kamal appears to meet the cited guideline's criteria for a therapy intensification review. It quotes the passage; it does not paraphrase medicine from memory.

DO: Click the citation chip. The guideline passage opens with the page number and a link to the PDF.

SAY: Swap the PDF for next year's guideline and nothing is retrained.

SAY: And then the action. The action agent drafted a clinical review task: review therapy intensification options per the cited guideline. It has not named a drug and it has not set a dose. That boundary is intentional. The agent can identify, explain and prepare work, but the clinical decision remains with the clinician. Nothing has happened to this patient's record; the task is waiting for Dr. Amal.

DO: Open the agent trace (the details view).

SAY: FHIR read, model score, guideline retrieval, draft. Four hops, four specialists, auditable end to end.

### Beat 3: The human approval queue (17:00, 60 seconds)

DO: Click Queue. The clinical review task for Kamal Miah is there, unsigned, with the model score and the citation attached. Approve it.

SAY: The agent is an assistant, not an actor. The queue holds review tasks, recalls and referrals; she approves or rejects each one. That approval lands in the audit trail with her name on it, next to the model score and the guideline citation that led to it. If she rejects it, that is recorded too. On the target architecture an approved item is written back to the exchange as a FHIR Task, which is how the EHRs already receive work items. Never as a medication order.

### Risk Sensitivity Simulator (18:00, three minutes)

DO: Click Simulator in the top navigation. Kamal is preselected. If any input is gold, press Reset.

SCREEN: the inputs on the left, the gauge at 34.5% Very High, 90th percentile in the registry, baseline drivers on the right. The footer reads: Predictive sensitivity analysis: association, not causal treatment effect. For clinical decision support only. Presets: "Inputs at guideline targets" and "Poorer control inputs".

SAY: This is the same deployed model, re-scored live as I change one of its inputs. It shows how the model's estimate responds to what it is given. It does not tell you what a treatment would do; I will keep saying that, because the screen does.

DO: Drag HbA1c from 10.9 down to 7.0.

SCREEN: the gauge falls to 3.3%, Low band, 56th percentile. The attribution chart shows HbA1c at about minus 31 points.

SAY: If the model received an HbA1c of 7.0 instead of 10.9, its predicted risk changes from thirty-four percent to about three. The attribution shows HbA1c carrying almost all of that change, which is what a clinician would expect and what a model has to be able to show. Notice what I did not say: I did not say that lowering his HbA1c will reduce his risk by that amount. That is a causal claim, and this is a predictive model.

DO: Press "Inputs at guideline targets".

SCREEN: 1.1%, Low band, 33rd percentile. Four care-gap flags clear. HbA1c 7.0, systolic 130, a test recorded today, adherence 0.90.

SAY: With every input at the guideline target the estimate is about one percent. Four of his open gaps would no longer be flagged. Same caveat: this is what the model returns for those inputs.

DO: Press "Explain the change".

SAY: (while it streams) The language model is handed the before-and-after model outputs, the attribution and the gaps closed, and asked to narrate them for the clinician. It adds no numbers of its own, and it does not turn them into a treatment claim; every figure in that paragraph is on this screen.

SAY: One engineering detail. The model carries monotonic constraints, but only where they are directionally defensible for a predictive model: a measurement of worse control or worse organ function cannot lower the estimate, and better adherence or better kidney function cannot raise it. The therapy flags are deliberately unconstrained, because in a registry a drug on the record marks severity and treatment history, and this model estimates risk, not treatment effect. That is a training-time constraint, not a filter on the output.

IF: You are ahead of time, press "Poorer control inputs". The gauge climbs to about 87%. Say: if the model received an HbA1c a point and a half higher, a systolic fifteen higher, adherence a fifth lower and one admission, its estimate is eighty-seven percent. A sensitivity check, not a forecast.

### Population dashboards (21:00, three minutes)

DO: Click Dashboards → Registry. Click the "High" bar in the registry risk tiers. Every panel narrows to those patients and a chip appears at the top right: Registry tier High, 406 of 4,000 patients. Click Clinical Quality: the filter follows. Click Clear.

SAY: Same platform, different altitude. Every number on these dashboards is the same query the assistant runs. The briefing and the conversation can never disagree, because there is one source of truth. And the dashboards filter each other: one click on a bar, and every panel, on every tab, answers for that group.

DO: Click Cost & Variation.

SCREEN: "Cost & Population Variation". Total QAR 62.4M a year; the top 10% of patients drive 26% of spend. Spend by segment and by facility. Mean HbA1c by nationality group, labelled descriptive variation: 7.17% (Qatari) to 8.01% (Nepali). Control, gaps and cost by nationality group, labelled descriptive and synthetic.

SAY: Two things a ministry would look at. Cost is concentrated: the top ten percent of patients carry a quarter of the spend. And outcomes vary by nationality group: mean HbA1c runs from 7.2 to 8.0, and the groups with the highest HbA1c also carry more open care gaps per patient. I will describe that and stop there. This is descriptive variation in synthetic demonstration data. It tells the ministry where to look next, starting with the open gaps; it does not tell them why, and it must not be read as a causal or biological finding about any group. What we do show is the discipline: subgroup monitoring here, and fairness evaluation of the model by the same groups in the Evaluation tab.

IF: You prefer the map, click Geography instead of Cost & Variation: the facility map coloured by control, Doha versus the north and the Industrial Area, with the same words: descriptive variation by facility, a place to investigate, not an explanation.

### Trust: the Evaluation tab (24:00, four minutes)

DO: Click Evaluation. The Risk model view.

SCREEN: model v2.2.0. AUC 0.854 against the baseline rule-based score's 0.809. Average precision 0.577 on a 10.7% event rate. Brier 0.067 against 0.096 for predicting the prevalence. Calibration slope 0.82. 1,000 held-out patients, 107 events. ROC, precision-recall and calibration charts. Threshold sweep with a slider. Subgroup fairness tables. The card's limitations line: trained on synthetic data; held-out metrics demonstrate the evaluation methodology, not clinical validation.

SAY: This tab answers "how do you know it works" before you ask, and it answers it honestly. Everything on this page is computed from a thousand patients the model never saw. AUC 0.854 against the registry's baseline rule-based score at 0.809. Calibration by decile. A Brier score thirty percent better than predicting the prevalence. And the caveat is on the card: this is held-out performance on a synthetic demonstration dataset. It demonstrates the evaluation methodology. It is not clinical validation, and the first workstream on real data is exactly this page, recomputed.

DO: Drag the operating-threshold slider. The confusion tiles and "reviews per event found" update.

SAY: The model does not choose the threshold. At twelve percent it finds sixty-nine percent of the events at about three reviews per event found. The ministry chooses, and now they can see what each choice costs in nurse time and in missed events.

DO: Point at the subgroup fairness table.

SAY: True-positive and false-positive rates at the operating threshold by nationality group, gender and age. Small groups are shown but not judged. The age gap is prevalence, not bias, and the page says so. On real data this table is a monthly job with an alert, not a certificate.

DO: Click Agent evalset. The last run shows 11 of 11.

SAY: Eleven real questions go through the real supervisor graph and are scored on four things a clinician would demand. Did it call the right tools. Did every clinical claim carry a citation. Did nothing bypass the human queue. And does every number in the answer match a recomputation from the tables. A fluent wrong number is the classic language-model failure. This catches it.

DO: Point at the last case, the guardrail.

SAY: The eleventh case is the question a minister will ask: how many admissions will the adherence programme prevent next year, and how much will it save. The assistant declines to give that number. It shows the predictive shift, and it explains that a figure for admissions a programme would prevent, or money it would save, needs causal evidence from an evaluated pilot or published effect estimates, plus cost data from finance. That refusal is a test case, and the build fails if it stops refusing.

DO: Click LLM & cost.

SAY: Two honest measurements. First, the proposed production model: Gemini 3.8 Flash, chosen for function-calling reliability at Flash pricing, with Pro as the judge in evaluation, never on the hot path, and the choice confirmed on the customer's evalset in discovery. Second, the orchestration pattern, measured rather than asserted: the supervisor reads under seven hundred tokens of tool schema per hop; one flat agent with every tool would read about two thousand seven hundred. That is one potential advantage of specialist separation, alongside modular evaluation and cleaner traces. The production topology is still a discovery decision, benchmarked on their evalset.

DO: Click Governance. Ten seconds.

SAY: Sixteen controls. Ten implemented in this build, including the supervisor's safety rules; six delivered by Google Cloud services in the target architecture. Zero autonomous writes.

### Close (28:00, 60 seconds)

DO: Click Home.

SAY: What you saw runs today on one container, on synthetic data. On Google Cloud the same contracts map to managed services, and that mapping is what we would validate in discovery. The cohort agent becomes BigQuery over a streamed Cloud Healthcare API FHIR store. The risk model moves to a Vertex endpoint. The forecast becomes AI.FORECAST in BigQuery. The guideline corpus becomes RAG Engine. The same ADK graph runs on Cloud Run in Doha, on a managed agent runtime where it is supported and approved. PHI stays inside the Qatar data boundary, and what enters a model prompt is agreed with the ministry's DPO, not assumed by me.

SAY: I built this in the shape of the job: understand the customer, build on the portfolio, find the gap, prototype the fix, know where the boundaries are, and hand it to the team that ships it. That is my thirty minutes. Over to you.

NOTE: Stop talking. Do not fill the silence.

## 5b. If time, if asked

NOTE: None of this is in the run of show. Use a beat here only if you are ahead of the clock or a question leads to it. Each one is self-contained and takes sixty to ninety seconds.

### C3: Treatment intensification gap (clinician persona)

DO: Assistant, clinician persona, click "Treatment intensification gap".

SCREEN: 999 type 2 patients with HbA1c ≥8 and obesity or kidney disease, not on an SGLT2 inhibitor or GLP-1 RA. Predictive scenario: if the model received an HbA1c one point lower for the 975 eligible patients, mean predicted risk moves from 26.1% to 18.9% and 346 patients move to a lower predictive band; HbA1c accounts for most of the change. The guideline citation. A priority-ordered clinical review list drafted to the queue.

SAY: The same question at population scale. Nine hundred and ninety-nine patients meet the criteria for a review. The model shows how its estimate responds if their HbA1c were a point lower: the mean predicted risk moves from twenty-six to nineteen percent. That is a sensitivity of the model, not an outcome of a programme, and the answer says so. The guideline passage is cited, which therapy is each clinician's decision, and the review list is in the queue.

### E3: Population risk scenarios, ML (executive persona)

DO: Switch persona to Dr. Khalid Al-Kuwari, Population Health Executive. Click "Population risk scenarios (ML)".

SCREEN: four eligible cohorts, each re-scored with one input changed. Intensification-review cohort, HbA1c one point lower: 975 eligible, 26.1% to 18.9%, 346 to a lower band, HbA1c. Overdue-HbA1c cohort, a test recorded 60 days ago: 723, 16.2% to 8.9%, 288, days since test. Low-adherence cohort, PDC 0.85: 796, 27.5% to 16.1%, 376, adherence. Uncontrolled-hypertension cohort, BP 14/7 lower: 1,229, 18.4% to 15.5%, 196, systolic BP. Then the disclaimer line: predictive scenario analysis only; changes in predicted risk are not estimates of causal treatment effect or of events a programme would prevent.

SAY: Four cohorts, one input changed each, every patient re-scored through the deployed model. The estimate is most responsive in the low-adherence cohort, so that is where I would start investigating and designing an intervention. What this table does not say, on purpose, is how many events a programme would prevent or what it would save. That needs causal evidence and cost data, and the assistant says so in the answer.

### E1: National picture with the map (executive persona)

DO: Click "National glycaemic picture".

SCREEN: mean HbA1c 7.52%, down 0.12 year on year. 35.7% well-controlled, 15.2% poorly controlled. Facility spread from 18% (Rawdat Al Khail) to 54% (West Bay); six facilities below the flag line. Complications: 24.4% retinopathy, 19.2% neuropathy, 14.5% CKD. A map of facilities coloured by control.

SAY: The national mean is 7.52 and falling, but the spread between facilities runs from eighteen percent well-controlled to fifty-four. The map, drawn by the agent inside the answer, shows control concentrated in Doha and the flagged facilities in the north and around the Industrial Area. That is descriptive variation by facility: it says where to investigate, not why.

### E4: Variation by nationality (executive persona)

DO: Click "Variation by nationality".

SCREEN: mean HbA1c by nationality group from 7.17% (Qatari) to 8.01% (Nepali); the highest groups carry 2.5 open gaps per patient against 1.6. The answer is labelled descriptive variation in synthetic data.

SAY: Same words as the dashboard: descriptive, synthetic, a place to look next starting with the open care gaps, and not a causal or biological finding about any group.

### E5, E6 and the Geography dashboard

IF: Asked about forecasting, click "Demand forecast": about 5% growth in outpatient and telehealth visits over twelve months with an 80% interval; on Google Cloud it is one AI.FORECAST statement. Asked about quality measures, click "Diabetes quality scorecard (MCP)": HEDIS-style measures with numerator, denominator and target, computed by the MCP server. Asked about geography, Dashboards → Geography: the map sized by patients and coloured by the chosen metric, the ranked list, and a facility profile on click.

## 6. Q&A bank

NOTE: Answer in three moves: the direct answer in one sentence, the evidence in one or two, and where it goes next in one. Then stop. If you do not know, say so and say how you would find out; a director is testing judgment, not recall.

### The solution

Q: How do you stop it hallucinating clinical advice?
A: Three walls and a test. Numbers come only from tools; the model narrates, it never invents a value. Clinical claims come only with a citation to a document and page. Actions go only through the approval queue. Then the evalset re-computes every headline number from the tables and fails the case if it does not match. On Google Cloud the same set runs in Cloud Build on every change and on a sample of production weekly, with Model Armor in front of the model where regionally supported.

Q: Why doesn't it prescribe?
A: That boundary is intentional. The agent can identify, explain and prepare work, but the clinical decision remains with the clinician. So it retrieves and cites the guideline passage, says the patient appears to meet its criteria for a therapy intensification review, and drafts a clinical review task into the queue. It never names a drug or a dose, and that rule is in the supervisor's instruction, in the action agent's tool set, which has no prescribing tool, and in the evalset. On the target architecture an approved item is a FHIR Task, never a medication order.

Q: Can it tell me how many admissions a programme prevents?
A: No, and it will say so if you ask; that is one of the evalset cases. The deterioration model is predictive: it estimates who is likely to deteriorate given what the exchange knows about them. Re-scoring a cohort with a better input shows how the estimate responds, which is useful for targeting, but a change in a prediction is not a causal treatment effect and cannot be counted as events a programme would prevent or priced as money saved. A figure for admissions a programme would prevent needs causal evidence from an evaluated pilot, ideally randomised or quasi-experimental, or published intervention-effect estimates applied to the eligible cohort, plus episode costs from finance. The agent can draft the pilot cohort and the measures to evaluate it against.

Q: Why is the nationality analysis only descriptive?
A: Because the data cannot support anything else, and neither could real registry data on its own. The registry shows that mean HbA1c and open care gaps vary by nationality group; it does not contain the causes, and in this demonstration the data is synthetic in any case. Inferring why groups differ, whether access, behaviour or biology, without causal evidence is exactly the kind of claim a health ministry should refuse to let a system make, so the supervisor is instructed not to, and the screens are labelled descriptive. What we do show is the discipline that matters: subgroup monitoring of outcomes and fairness evaluation of the model by the same groups, so the ministry can see where to investigate.

Q: Why five specialists instead of one agent? Isn't that just complexity?
A: It is the orchestration pattern I used in the prototype, and I would not call it the production architecture yet. It has potential advantages that the prototype demonstrates: each specialist sees only its own tools, so tool scope is narrower and the prompt per hop is smaller, which the Evaluation tab measures at under seven hundred schema tokens for the supervisor against about two thousand seven hundred for one flat agent; each specialist can be evaluated on its own; and the traces are cleaner. The cost is an extra hop of latency and more moving parts. During technical discovery we would benchmark a single tool-calling agent, a supervisor and router, and this specialist pattern against the customer's evalset on task accuracy, tool-selection reliability, safety, latency, token consumption, maintainability and operational complexity, and choose on the evidence.

Q: Why ADK and not LangGraph or CrewAI?
A: Native Gemini function calling, a first-class MCP client in McpToolset, agent-to-agent protocol built in, and a managed agent runtime on Google Cloud where it is supported and approved, so the same graph deploys without a rewrite. For a Google Cloud customer the framework the platform evaluates, traces and hosts natively is the right default. LangGraph is a fine choice if the customer is multi-cloud; the tools and the MCP server would not change.

Q: Why MCP? Isn't that just function calling with extra steps?
A: Function calling binds a tool to one agent in one framework. MCP makes the tool a service any client can use: our ADK agent, Gemini CLI, Gemini Enterprise, a partner's agent. The population-health server is the asset the ministry keeps if they change agent frameworks. And Google provides MCP tooling for exactly the data services underneath it: the MCP Toolbox has a BigQuery source and a Cloud Healthcare source for FHIR, so Nabd's server sits beside the platform's tools rather than replacing them.

Q: What is the gap you found in Google's catalogue?
A: Google's MCP tooling reads FHIR and queries BigQuery, which answers record-level and table-level questions. What we needed on top of that data was a population-health layer: quality measures, cohort construction, care-gap identification, model-backed stratification, predictive risk scenarios, and a human-approved drafting path. We built that as a small MCP server with seven tools. I would validate that gap analysis with the Healthcare API product team in my first month rather than assume nobody else is working on it; feeding back to product is in the job description.

Q: Why Gemini 3.8 Flash and not Pro?
A: It was chosen on our own evalset: trajectory recall, groundedness, faithfulness, latency and cost per question. Flash 3.8 is agent-tuned and matched Pro on tool-structured tasks at a third of the cost, with first-token latency under a second at low thinking. Pro 3.1 is the judge in evaluation and the model for long executive syntheses, never the hot path. The choice is confirmed on the customer's evalset in discovery. And I avoided Gemini 2.5 Flash on purpose: it has a published retirement date, and you never build a clinical product on a model with a retirement date.

Q: Latency. Will a clinician actually wait?
A: A typical clinician question is three tool hops, each a Flash call, so single-digit seconds to the full answer in the prototype. The trace streams from the first hop, so the wait looks like work rather than a spinner. The two levers that matter are thinking level on routing turns and the number of synchronous hops; the evaluation tab measures both. The nightly briefing runs as a batch, so the morning panel is instant. Production latency is an SLO we agree in discovery and validate under load in the pilot.

Q: Data residency. Where does the model run?
A: PHI and identifiable healthcare data remain in the Qatar data boundary: the FHIR store, BigQuery, the session store and backups sit in me-central1 under an Assured Workloads Qatar data boundary with customer-managed keys and VPC Service Controls. The model endpoint, and exactly what information is allowed into a model prompt, are selected with the ministry's DPO and security team based on supported regional processing, residency requirements and service availability. I do not make that compliance decision for them, and the demo today uses only synthetic data. The legal frame is Qatar's Personal Data Privacy Protection Law.

Q: Where does the agent run? Why not a managed agent runtime?
A: In the reference architecture the agent is an ADK workload on Cloud Run in me-central1, with sessions in AlloyDB, and a managed agent runtime where it is supported and approved for this workload. Regional availability of managed services is one of the first things I would confirm in discovery, with the region table in hand, rather than something I would assert from a slide. The same goes for prompt screening and model monitoring: in-region equivalents today, Sensitive Data Protection and BigQuery drift jobs, and the managed services where offered.

Q: What does it cost to run?
A: I can tell you what the prototype costs, because the Evaluation tab measures actual tokens and cost per question when the evalset runs live, and I can tell you the list prices of the proposed models. I will not give you a production number today. During discovery we would model cost from expected users, question volume, token consumption, BigQuery scan volume, model-serving requirements and availability requirements, then validate it during the pilot. Whether it is worth it is the ministry's call, on evidence from the pilot, not on a return I calculate from a predictive model.

Q: How did you evaluate it?
A: Two layers. The model: a stratified 25% hold-out the model never saw, discrimination, calibration, threshold economics and subgroup fairness, all computed on the page, not pasted in, with the caveat on the card that this is synthetic data demonstrating the methodology rather than clinical validation. The agent: a golden evalset of eleven questions run through the real graph, scored on tool trajectory, groundedness, safety and numeric faithfulness against a recomputation, including a guardrail case where the right answer is a refusal. On Google Cloud, the Gen AI Evaluation Service adds Gemini Pro as an LLM judge, in CI and on a production sample.

Q: Is the model fair?
A: We report true-positive and false-positive rates at the operating threshold by nationality group, gender and age band, and compute gaps only over groups with enough events. Small groups are shown but not judged. The age gap is a prevalence difference, and the page says so rather than hiding it. On synthetic data this proves the method; on real data a fairness audit is a precondition for production, and a monthly job re-runs the table and alerts on drift. Fairness is a monitoring discipline, not a one-time certificate.

Q: Why XGBoost? And why the monotonic constraints?
A: XGBoost is a strong, efficient baseline for structured tabular clinical data with interpretable per-prediction contributions, it handles thresholds like HbA1c above nine natively, and BigQuery ML has the same estimator, so on Google Cloud it is a CREATE MODEL statement. The constraints are kept only where they are directionally defensible for a predictive model: a measurement of worse control or worse organ function cannot lower the estimate, and better adherence or better kidney function cannot raise it. The therapy flags are deliberately unconstrained, because in a registry a drug on the record marks severity and treatment history, and the model is predictive, not a treatment-effect model. That is why the simulator only ever says how the estimate responds to an input.

Q: Is the data real?
A: No. Four thousand synthetic patients, zero PHI. But the shape is real: eight relational tables, LOINC, ICD-10, SNOMED and ATC codes, thirty-six months longitudinal, a FHIR R4 export. Four thousand is big enough for the evaluation methodology to be shown on a thousand-patient hold-out and small enough to run on one container. The first real workstream is loading a de-identified extract from the exchange into BigQuery and recomputing every page you saw.

Q: Real-time or batch?
A: Both, deliberately. Per-patient signals stream: a new HbA1c result re-scores that patient in seconds through the FHIR store, Pub/Sub and the endpoint. Population metrics batch nightly: stratification, care gaps, quality measures, variation views. Streaming the aggregates would cost many times more for numbers that move over weeks.

Q: How does it integrate with the hospital EHRs?
A: Through the exchange, not around it. The Healthcare API takes FHIR R4 natively and HL7 v2 through its own ingestion, so the legacy sites bridge rather than migrate. Write-back is a FHIR Task, which is how the EHRs already receive work items, so an approved review task, recall or referral appears in the clinician's normal worklist. We never write to a clinical record directly, and we never write a medication order.

Q: How does this scale to a million patients?
A: The target architecture uses managed, horizontally scalable services: BigQuery for the warehouse, Cloud Run for the app and the agents, a Vertex AI endpoint for scoring. But I would not tell a ministry it scales until it has been made to. National-scale capacity, quotas, concurrency, latency and cost would be validated through load testing during the pilot, and the two variables I would watch first are tokens per question and synchronous hops per question, which the evaluation tab already measures.

Q: Why build a custom agent instead of using Gemini Enterprise?
A: Gemini Enterprise is the right front door for knowledge workers, and it speaks MCP, so the population-health server plugs into it. What it does not give you out of the box is the governed clinical action path: drafts, the approval queue, FHIR write-back, and evaluation on tool trajectories. So Gemini Enterprise at the front, the ADK agent as the clinical backend behind it.

Q: Why not just BigQuery, Looker and a chatbot?
A: Looker answers the questions someone anticipated; the agent answers the one nobody did, and it can prepare work. But Looker belongs in the target architecture for exactly the governed KPIs a ministry publishes, and the dashboards in the demo run the same queries the agent runs, so the two never disagree. It is not either-or. The chatbot without tools, citations and a queue is the thing I would refuse to ship.

Q: Where does SAS fit? Would you tell the ministry to leave SAS?
A: Not on day one, and not as a rip-and-replace. SAS is where the pattern was proven and where the ministry's current models live; those models can be exposed as MCP tools and called by the same agent. The argument for Google is data gravity in the exchange, a sovereign region in Doha and a managed agent stack, not that SAS is bad. Over time BigQuery ML and Vertex reduce the licence footprint, and the customer decides the pace.

Q: What about MedGemma and clinical notes?
A: Everything in the demo is structured data. Clinical notes are a later workstream, and MedGemma is the right model for them: open weights, so it can run in region, on the unstructured parts of the record. The pattern does not change; it is one more specialist with one more tool. I would not start there, because the structured registry already carries most of the signal for deterioration.

Q: Security. What about prompt injection through a guideline PDF or a record?
A: The agent's tools are read-only against the data and draft-only against actions, so an injected instruction can at most produce a bad draft, which a human sees before anything happens. Tool inputs are validated schemas, not free text. Retrieved passages are quoted with their source so an odd instruction is visible. On Google Cloud, Sensitive Data Protection in region and Model Armor where regionally supported screen prompts and responses, and the evalset carries adversarial cases.

Q: Why did you put voice in?
A: Because the customer asked for it in the original programme, and because a clinician between patients does not type. Arabic and English through the Web Speech API today, Chirp 3 through Speech-to-Text on Google Cloud. It is a thirty-second beat in the demo and a real adoption lever in a clinic.

Q: What would you cut? What worries you?
A: I would cut the demand forecast: the weakest model and the least surprising insight. I would trade it for a hypoglycaemia-risk view on the insulin-treated cohort, where the case for early clinical review is strongest. What worries me is adoption, not accuracy. The queue exists so clinicians own the decision; the variation views exist so the ministry can see where to investigate. Tools do not change outcomes; workflows do.

### The customer engineer role

Q: How would you run this engagement from first meeting to a signed pilot?
A: Discovery first: two weeks with the registry team, two clinicians, the DPO and the security team, to agree the one question the pilot must answer, the data it needs, what may enter a model prompt, the required recovery point and time, and which managed services are available and approved in region. Then a half-day architecture workshop that turns the reference architecture you saw into their diagram, signed off, including the orchestration benchmark on their evalset. A six-to-eight-week PoC on a de-identified extract, with success criteria written before the first commit. Then a pilot at four facilities with a clinical safety case, load testing and a cost model validated against real usage. My job across all of it is to be the technical owner of the outcome and to keep the account team, the partner and product informed of what is blocking.

Q: What are the PoC success criteria?
A: Written down before we start, in the customer's words. For the model: discrimination on their held-out data above the registry's current baseline score, calibration within an agreed slope, fairness gaps reported by nationality. For the agent: the golden evalset at a pass rate they set, with faithfulness at one hundred percent because a wrong number is disqualifying, and the guardrail cases passing. For adoption: a clinician panel uses it for two weeks and the queue shows approvals. For the platform: data never leaves the boundary, and the DPO signs what enters a prompt. If any of those fail, the PoC failed, and we say so.

Q: The customer says their data is not ready.
A: It never is, and the exchange is more ready than most. I would start with the narrowest extract that answers the pilot question, run the profiling in BigQuery in the first week so the gaps are numbers rather than fears, and put data quality on the dashboard as a measure like any other. The care-gap engine in the demo is partly a data-quality engine: an overdue HbA1c is either a clinical gap or a missing feed, and both are worth knowing.

Q: A senior clinician says they do not trust it.
A: Good, that is the right starting position. I would sit with them and their own patients in the simulator, because trust comes from seeing the model agree with their judgment on cases they know, and disagree in ways they can check. I would show them the citation path and the queue, and the fact that it never chooses a drug for them, and I would ask them to write the first evalset questions. Clinicians who wrote the tests defend the system. Clinicians who were shown a demo do not.

Q: The customer wants to skip the approval queue to save time.
A: I would say no, and explain why in their terms: the queue is what makes the system defensible to the regulator, the medical director and the patient. Then I would find where the time actually goes and remove that instead: batch the drafts, route by facility, let a nurse pre-review. Speed inside the guardrail, not by removing it. If they insist, that is an escalation to the account lead and to legal, not something a customer engineer decides alone.

Q: How do you work with the account team and partners?
A: The account executive owns the relationship and the commercial; I own the technical outcome and the truth about what the product can and cannot do. Partners build and run; I make sure the reference architecture and the success criteria are clear enough that a partner can deliver them. And I feed product back what the customer needed and could not get, with evidence, which in this case is the population-health layer over the healthcare MCP tooling.

Q: How do you keep current with Google's product changes?
A: A weekly pass over the release notes for Vertex, BigQuery, the Healthcare API and the Gemini models, plus the region table for me-central1, because for Gulf customers the region is the first question and I would rather say "where regionally supported" than be wrong. I keep a short list of deprecations, which is how I knew not to build on Gemini 2.5 Flash, MedLM or the Healthcare Natural Language API. And I build small things constantly; the simulator in this demo was two days ago.

Q: What would you do in your first ninety days?
A: Learn the territory's top ten accounts and the three deals that are actually moving. Shadow two customer engineers on real engagements before I lead one. Build one reference asset the whole team can reuse, which is what this demo is meant to become. And send product one well-evidenced gap memo. By day ninety I should be the technical owner on at least one opportunity and known internally as the person to ask about healthcare on Google Cloud in the region.

Q: Tell me about a time you were wrong with a customer.
A: Use a real one. The shape that works: what you claimed, how you found out you were wrong, what you did within twenty-four hours, and what you changed in your process. The panel is testing whether you correct fast and in the open. Do not pick a story where you were secretly right.

### Curveballs

Q: Isn't this over-engineered for a proof of concept?
A: The engineering is in the guardrails, and those are the parts a health ministry will ask for first. Strip them out and it is a chatbot over a database, which is a demo nobody deploys. Everything else is intentionally thin: one container, one region, four models, eleven evalset questions. The reference architecture is a target to validate, and the phases are how we get there without paying for all of it on day one.

Q: What if the model suggests the wrong drug or dose?
A: It cannot, because it never drafts one. The action agent has no prescribing tool; it drafts a clinical review task that points at the cited guideline passage, and the evalset fails any answer that names a drug or a dose. The clinician sees the model drivers, the passage and the task before signing, and the audit trail shows exactly who decided what. A wrong recommendation reaching a patient would be a process failure at the signature, which is where a health system already puts its controls.

Q: Who owns the model risk?
A: The ministry owns it, because they own the clinical decisions and the population. Google provides the platform controls and their evidence. Whoever builds the model, us or a partner, owns the model card, the evaluation and the monitoring. I would write that into the pilot agreement as a RACI on the first page, because ambiguity there is how AI projects in healthcare die.

Q: Would this work for another disease or another country?
A: The pattern transfers; the content does not. The agent graph, the MCP server contracts, the evaluation harness and the queue are disease-agnostic. What changes is the registry schema, the guideline corpus, the outcome label and the quality measures. Cardiovascular disease would be the natural second programme for Qatar. Another Gulf country would reuse the architecture and re-do the data residency work for its own regulator.

Q: How long did this take and how did you build it?
A: About two weeks of evenings and weekends, in Python with FastAPI, the Agent Development Kit and the Gemini SDK, XGBoost for the models, React for the front end, deployed on Railway because it was the fastest path to a URL. I used an AI coding assistant as a pair programmer throughout, and I am happy to say so; the architecture, the clinical framing, the evaluation design and every decision in the deck are mine, and I can walk through any file. That is how I would expect a customer engineer to build in 2026.

Q: What do you need from Google to ship this?
A: Three things. Clear regional availability, with dates I can give the customer, for the managed agent runtime, Model Armor and Model Monitoring in me-central1. A population-health layer in the Healthcare API catalogue, or a partner programme that recognises one. And a reference architecture for sovereign healthcare AI in the Gulf that a customer engineer can hand over and validate, because today each of us is drawing it from scratch.

## 7. Questions to ask them

- How does the customer engineering team in the region divide healthcare and public sector between people, and where would this kind of asset live so others can reuse it?
- What is the blocker you hear most from Gulf customers right now: sovereignty, skills, or something else?
- How is a customer engineer's first year measured here, beyond the numbers?
- What did the strongest customer engineer you have worked with do differently?

## 8. Failure playbook

| If | Then |
|---|---|
| The model errors mid-scenario | Nothing to do. The backend runs the same tools directly, automatically, and says so in the trace. Keep talking. |
| The header shows a credentials or capacity error | Every scenario chip still runs on live data. Only free-form questions need the model. Say: "the chips run the same tools without the language model in the loop." |
| A free-form question goes sideways | "Let me show you the trace of why." The details view turns a miss into a transparency beat. Then run a chip. |
| The Explain button in the simulator returns the deterministic narrative | It is grounded in the same numbers. Say so and move on. |
| Someone asks how many events a programme would avoid, what it would save, or its return on investment | Do not improvise a number. Say the model is predictive, show the predictive shift, and, if there is time, run the guardrail case in the evalset or type the question into the assistant and let it decline. |
| Someone asks why it did not prescribe | "That boundary is intentional. The agent can identify, explain and prepare work, but the clinical decision remains with the clinician." |
| Wi-Fi dies | Switch to the hotspot. The direct tool runs need no external call after the page has loaded. |
| A number differs from this script | Read the screen. "The screen is the truth; that is the point of the product." |
| They interrupt with a deep question | Answer it, then say "and that is exactly what the next click shows". Every act has a natural re-entry. |
| You lose your place | The Simulator tab is a safe harbour from anywhere: Kamal, one input, one explanation, one minute. |

## 9. Numbers to have in your head

| Number | Where it comes from |
|---|---|
| 4,000 patients · 193k observations · 80k encounters · 18 facilities | Home counters |
| QAR 62.4M annual cost · top 10% of patients = 26% of spend | Home, Cost & Population Variation, E2 |
| Mean HbA1c 7.52% (down 0.12 year on year) · 35.7% well-controlled · 15.2% poorly controlled | KPI strip, E1 |
| 753 HbA1c tests overdue · 7,699 open care gaps · 1,203 retinal screening overdue · 818 with adherence below 60% | Home badges, C1, C4 |
| Five patients at 98 to 99% · about 418 expected deterioration events in 12 months | C1 |
| Kamal Miah QH-101795: 48, type 2 for 13.7 years, Al Rayyan HC · HbA1c 10.2 → 10.9 · PDC 59% · BP 143/93 · registry Moderate · model 34% Very High · drivers HbA1c, ED visits · guideline MOPH NCG T2DM Adults Elderly, page 14 · draft: clinical review task | C2, Simulator |
| Simulator (v2.2.0): baseline 34.5% Very High, 90th percentile · HbA1c 10.9 → 7.0: 3.3% Low (HbA1c about minus 31 points) · HbA1c 8.0: 5.8% Moderate · Inputs at guideline targets: 1.1% Low, 33rd percentile, four gap flags clear · Poorer control inputs: 87% Very High | Simulator |
| 999 in the intensification gap · 975 eligible re-scored · mean predicted risk 26.1% → 18.9% · 346 to a lower predictive band · HbA1c accounts for the change | C3, E3 |
| Population risk scenarios: overdue HbA1c 723, 16.2% → 8.9%, 288 · low adherence 796, 27.5% → 16.1%, 376 · uncontrolled BP 1,229, 18.4% → 15.5%, 196 | E3, G1 |
| Facility control spread 18% (Rawdat Al Khail) to 54% (West Bay) · six facilities below the flag line · 24.4% retinopathy, 19.2% neuropathy, 14.5% CKD | E1 |
| Variation by nationality: HbA1c 7.17% Qatari to 8.01% Nepali · 2.5 vs 1.6 open gaps per patient · descriptive, synthetic | E4, Cost & Population Variation |
| Segments: Complex high-cost 670 (QAR 33k, 13%) · Care-gap heavy 1,535 · Stable low-touch 1,464 · Rising-risk 331 (64% mean risk) | E2 |
| Registry tier High: 406 of 4,000 | Registry dashboard cross-filter |
| Model v2.2.0: AUC 0.854 vs 0.809 baseline rule-based score · AP 0.577 on a 10.7% event rate · Brier 0.067 vs 0.096 · slope 0.82 · 1,000 held out, 107 events · threshold 12%: sensitivity 69%, specificity 84%, 2.9 reviews per event found · synthetic data, methodology not clinical validation | Evaluation |
| Evalset: 11 cases, 11 of 11 in direct-tool mode · trajectory, groundedness, action safety, faithfulness · g_causal guardrail case | Evaluation |
| Gemini 3.8 Flash $0.75 / $3.75 per million tokens (intro) · Pro 3.1 judge · 2.5 Flash retiring Oct 2026 | LLM & cost |
| Schema tokens per hop: supervisor 687 · one flat agent 2,698 · orchestration pattern of the prototype, topology decided in discovery | LLM & cost |
| Governance: 16 controls · 10 implemented · 6 Google Cloud · 0 autonomous writes | Governance |
| Google Cloud mapping (reference architecture, validated in discovery): BigQuery · RAG Engine · Vertex endpoint · ADK on Cloud Run in me-central1 · AlloyDB · FHIR Task | Slide 9 |
