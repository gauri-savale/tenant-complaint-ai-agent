# 🏢 TenantCare AI — Intelligent Tenant Complaint Management Agent

**Major Academic Project (CSE) — NLP + Machine Learning + Agentic AI + Database + Analytics, built with Gradio**

---

## 1. Abstract

TenantCare AI is an end-to-end intelligent complaint management system for residential
property management. Tenants describe issues in plain natural language; an AI agent
automatically extracts structured information, classifies the issue, detects safety
emergencies, computes a priority score, routes the complaint to the correct maintenance
department, estimates an SLA deadline, checks for duplicates against complaint history,
and generates both an internal recommendation and a tenant-facing acknowledgement — all
visible through a polished, multi-tab Gradio interface with a live analytics dashboard.

The system deliberately combines **explainable, deterministic rule-based decisions**
(for safety-critical judgments like emergency detection and priority) with **classical
machine learning** (TF-IDF + Logistic Regression for category classification) and
**optional LLM enrichment** (for natural-language summaries only, never for critical
decisions). It runs **fully offline by default (DEMO_MODE)** — no API key is required.

## 2. Problem Statement

Manual tenant complaint handling in residential properties is slow, inconsistent, and
error-prone: complaints get lost in email threads, safety-critical issues (gas leaks,
exposed wiring, break-ins) are not always triaged fast enough, similar/duplicate
complaints waste maintenance staff time, and management has no data-driven view of
recurring problems or department workload.

## 3. Motivation

A property manager handling dozens of units cannot manually read, categorize, prioritize
and route every complaint the moment it arrives, especially outside office hours.
An AI agent that performs this triage automatically — with explainable reasoning a human
can audit — reduces response time for genuinely urgent issues and gives management
data to act on recurring maintenance problems proactively.

## 4. Objectives

1. Accept free-text tenant complaints through a professional web UI.
2. Automatically extract structured fields (category, location, sentiment, urgency, severity).
3. Deterministically detect safety emergencies and assign a priority level.
4. Route each complaint to the correct department/staff and estimate an SLA deadline.
5. Detect duplicate and recurring complaints using semantic similarity.
6. Provide a conversational agent that can answer questions using the complaint database.
7. Give management a live analytics dashboard and AI-generated insights report.
8. Work reliably offline (no external API dependency required).

## 5. Existing System

Most small-to-mid property managers rely on phone calls, email, or generic ticketing
tools with **no automatic classification, no priority intelligence, no emergency
detection, and no duplicate detection**. Even "smart" ticketing SaaS tools typically
route tickets on static keyword rules with no learning component and no transparent
reasoning for their decisions.

## 6. Proposed System

TenantCare AI combines rule-based NLP, a trained ML classifier, and an orchestrating
AI agent that decides which of its 12 tools to invoke for a given complaint or
question — producing not just a category label but a full audit trail ("Agent
Actions") of every step taken, plus a plain-English "Why?" explanation for every
classification and priority decision.

## 7. System Architecture

```
                     ┌─────────────────────┐
                     │   Gradio UI (6 tabs) │
                     └──────────┬──────────┘
                                │
                     ┌──────────▼──────────┐
                     │      AI Agent        │  agent/agent.py
                     │ (tool orchestrator)  │
                     └──────────┬──────────┘
                                │  calls tools as needed
         ┌──────────┬──────────┼──────────┬──────────────┐
         ▼          ▼          ▼          ▼              ▼
  ┌───────────┐┌──────────┐┌─────────┐┌──────────┐┌─────────────┐
  │Complaint  ││ Risk +   ││Department││Resolution││  Database   │
  │Understand.││ Priority ││Assignment││  Recomm. ││  (SQLite)   │
  │(NLP + ML) ││ Analysis ││          ││          ││             │
  └───────────┘└──────────┘└─────────┘└──────────┘└──────┬──────┘
                                                            │
                                                  ┌─────────▼─────────┐
                                                  │ Dashboard/Analytics │
                                                  └────────────────────┘
```

## 8. Technologies Used

| Layer | Technology |
|---|---|
| UI | Gradio (Blocks, multi-tab) |
| Language | Python 3.10+ |
| Database | SQLite |
| Classical ML | scikit-learn (TF-IDF + Logistic Regression) |
| NLP | Custom lexicon/keyword-based extraction + TF-IDF cosine similarity |
| Optional LLM | OpenAI API (only for natural-language generation, fully optional) |
| Analytics/Charts | Matplotlib |
| Data handling | Pandas |

## 9. AI Agent Architecture

The agent (`agent/agent.py`) is a **tool-calling orchestrator**, not a single prompt.
It has 12 discrete tools (`agent/tools.py`):

`classify_complaint`, `extract_complaint_information`, `detect_emergency`,
`determine_priority`, `assign_department`, `estimate_sla`,
`generate_tenant_response`, `search_similar_complaints`, `recommend_resolution`,
`update_complaint_status`, `generate_summary`, `generate_management_insights`
(plus `check_duplicate` for duplicate-complaint detection).

Two entry points:
- **`analyze_new_complaint()`** — always runs the full pipeline (all safety-critical
  tools always execute; a full audit trail of every action taken is returned).
- **`chat()`** — a lightweight agent that inspects the user's natural-language message
  and **decides which subset of tools are relevant** (ID lookup vs. similarity search
  vs. management insight vs. general triage), which is what makes it an agent rather
  than a single LLM call.

## 10. ML Methodology

`ml/train_model.py` trains: **text → TF-IDF (1-2 grams, English stopwords) →
Logistic Regression (`class_weight="balanced"`)** to predict complaint **category**.
Evaluated with an 80/20 stratified train/test split using accuracy, weighted
precision/recall/F1, and a confusion matrix (saved as `ml/model/confusion_matrix.png`).
Metrics are saved to `ml/model/metrics.json`.

`data/training_data.csv` is a **196-row synthetic demonstration dataset** built from
templated realistic complaint phrasings across all 10 categories (see
`data/generate_dataset.py`). Because the templates are cleanly separable, the model
reaches ~100% test accuracy on this data — this is explicitly **not** claimed as
real-world accuracy; the code and this README both flag it as a demonstration dataset.
A production system would train on thousands of real, anonymized historical complaints.

If the trained model files are missing, `nlp/classifier.py` automatically falls back
to the keyword rule classifier — **the app never crashes** if you skip training.

## 11. NLP Methodology

- **Entity/category extraction** (`nlp/entity_extraction.py`): keyword/phrase matching
  against a curated dictionary per category → subcategory, plus location and
  emergency-keyword detection. Fully explainable ("Why?" = the matched keywords).
- **Sentiment & urgency** (`nlp/sentiment.py`): lexicon-based scoring (positive/negative
  word lists, exclamation marks, ALL-CAPS words, intensity words) — no external corpus
  downloads needed, so it works fully offline.
- **Semantic similarity / duplicate detection / recurring-issue detection**
  (`nlp/similarity.py`): TF-IDF vectorization + cosine similarity across complaint
  descriptions. Chosen over sentence-transformer embeddings specifically so the whole
  project has **zero large model downloads** and starts instantly on any laptop.

## 12. Database Design

SQLite (`database/schema.sql`), 5 tables: `tenants`, `departments`,
`maintenance_staff`, `complaints`, `complaint_updates` (status-change audit log).
See the schema file for full column list. Key complaint fields: `complaint_id`,
`tenant_id`, `timestamp`, `description`, `category`, `subcategory`, `location`,
`sentiment`, `severity`, `urgency`, `safety_risk`, `priority`, `priority_reason`,
`department`, `assigned_staff`, `status`, `sla_deadline`, `ai_summary`,
`recommended_action`, `resolution`, `is_duplicate_of`, `last_updated`.

Statuses: `Submitted → AI Analyzed → Assigned → In Progress → Waiting for Tenant →
Resolved → Closed`.

## 13. Functional Requirements

- Submit a complaint and receive an AI analysis card within seconds.
- Classify, prioritize, and detect safety risk automatically.
- Detect duplicate complaints against recent history.
- Chat with the agent about urgency, similar complaints, or a specific complaint ID.
- Filter/search/update complaints as a manager.
- View a live analytics dashboard with 7 charts and key metrics.
- Generate an AI management-insights report and recurring-issue list.
- Look up a tenant's own complaint history by Tenant ID.

## 14. Non-Functional Requirements

- Must run fully offline (no mandatory external API).
- Must not crash on missing model files, empty database, or malformed input.
- Must respond to a single complaint analysis in well under a few seconds on a laptop CPU.
- Must be modular so each layer (DB/NLP/ML/agent/UI) can be explained independently in a viva.

## 15. Use Cases

1. Tenant submits a plumbing leak → routed to Plumbing Maintenance, Medium/High priority.
2. Tenant submits a gas-smell complaint → flagged Critical, immediate safety alert shown.
3. Manager filters all Critical, open complaints and updates one to "In Progress".
4. Manager asks the AI Agent "which department is overloaded?" and gets a data-backed answer.
5. Tenant checks their own complaint history by Tenant ID.

## 16. Data Flow

`Tenant text → extract_complaint_information → classify_complaint → detect_emergency
→ determine_priority → check_duplicate → assign_department → estimate_sla →
recommend_resolution → generate_summary → generate_tenant_response → SQLite → 
Analytics/Dashboard/Insights`

## 17. Algorithms

- **TF-IDF** vectorization for both ML classification features and similarity search.
- **Logistic Regression** (multinomial, balanced class weights) for category classification.
- **Weighted deterministic scoring rule** for priority (see `agent/decision_engine.py` —
  explicit point weights for emergency/severity/urgency/sentiment/category risk, summed
  and thresholded into Critical/High/Medium/Low).
- **Cosine similarity** over TF-IDF vectors for duplicate and similar-complaint retrieval.

## 18. Agent Tools (recap)

See Section 9. Every tool is a plain Python function — no external agent framework
dependency — callable individually and composed by `agent/agent.py`.

## 19. Screenshots

_Add screenshots here after running the app locally:_
- `[Screenshot: Tab 1 — Tenant Complaint submission + AI analysis card]`
- `[Screenshot: Tab 2 — AI Agent chat]`
- `[Screenshot: Tab 3 — Complaint Management table]`
- `[Screenshot: Tab 4 — Analytics Dashboard]`
- `[Screenshot: Tab 5 — AI Insights report]`
- `[Screenshot: Tab 6 — Complaint History]`
- `[Screenshot: ml/model/confusion_matrix.png]`

## 20. Installation

```bash
# 1. Clone / unzip the project, then enter the folder
cd tenant-complaint-ai-agent

# 2. Create a virtual environment (recommended)
# macOS / Linux:
python3 -m venv venv
source venv/bin/activate
# Windows (PowerShell):
python -m venv venv
venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. (Optional) copy the env file if you want LIVE MODE with an OpenAI key
cp .env.example .env     # Windows: copy .env.example .env
# then edit .env and set OPENAI_API_KEY=...   (leave blank to stay in DEMO_MODE)

# 5. (Optional but recommended) regenerate datasets and train the ML model
python data/generate_dataset.py
python ml/train_model.py
```

## 21. Running Instructions

```bash
python app.py
```

Then open the printed local URL (typically `http://127.0.0.1:7860`) in your browser.
On first run the SQLite database is created and automatically seeded with 150 realistic
demo complaints from `data/sample_complaints.csv`, so every tab — including the
dashboard — has real data immediately.

## 22. Expected Output

- Console prints `Seeded database with 150 demo complaints.` on first run.
- Console prints `Running on local URL: http://127.0.0.1:7860`.
- Submitting a complaint in Tab 1 returns an analysis card within ~1 second showing
  category, priority, department, SLA deadline, AI summary, and a tenant message.
- Tab 4 shows non-empty charts immediately (seeded data).

## 23. Troubleshooting Guide

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` inside the activated venv. |
| Port 7860 already in use | Close other Gradio apps, or edit `app.py`'s final line to `demo.launch(server_port=7861, ...)`. |
| Dashboard is empty | Delete `data/complaints.db` and restart — it will reseed automatically. |
| "ML classifier: not found" banner | Run `python ml/train_model.py` once. |
| Want to reset everything | Delete `data/complaints.db` (safe — it regenerates). |
| LLM enrichment not activating | Check `.env` has a valid `OPENAI_API_KEY` and `openai` package is installed; the app silently falls back to templates on any API error. |

## 24. Test Cases

Run: `python -m unittest tests.test_app -v` (16 automated tests). Covered scenarios:
normal complaint, emergency complaint, high-priority complaint, low-priority complaint,
duplicate complaint, unknown/ambiguous complaint, empty input, very long complaint,
multiple issues in one complaint, angry-sentiment complaint, safety-risk complaint,
department routing for different categories, existing-complaint lookup, status update,
SLA breach detection, and a chat-agent sanity check. All 16 pass in the shipped state.

## 25. Results

- ML classifier: 100% accuracy on the 40-example held-out test split of the
  196-row demonstration dataset (see `ml/model/metrics.json` after training) —
  expected given clean, templated training data; explicitly not a real-world claim.
- End-to-end complaint analysis (extraction → classification → priority → routing →
  SLA → summary → tenant message → DB write) completes in well under a second on a
  standard laptop CPU, fully offline.

## 26. Limitations

- The training/demo datasets are synthetic and small — a real deployment needs real,
  anonymized historical complaints for meaningful ML generalization.
- Rule-based sentiment/urgency/keyword extraction, while explainable and fast, is less
  nuanced than a full transformer-based NLP pipeline.
- LLM enrichment (LIVE_MODE) is optional and untested against a live key in this
  environment — it degrades gracefully to templates if the API call fails.

## 27. Future Scope

- Swap the keyword/TF-IDF similarity for sentence-transformer embeddings if GPU/network
  access is available.
- Add authentication for tenants vs. managers.
- Integrate with a real maintenance-ticketing/SMS notification system.
- Expand the ML model with real historical data and try gradient-boosted trees.

## 28. Conclusion

TenantCare AI demonstrates a complete, explainable, offline-first AI agent system
combining classical NLP, machine learning, a deterministic rule engine for
safety-critical decisions, a genuine multi-tool agent architecture, a relational
database, and live analytics — all through a single polished Gradio application.

---

## 🎓 Academic Concepts Demonstrated

- **Artificial Intelligence:** rule-based expert-system-style decision engine, agentic
  tool orchestration.
- **Machine Learning:** supervised text classification (TF-IDF + Logistic Regression),
  train/test evaluation methodology, confusion matrix analysis.
- **NLP:** tokenization, lexicon-based sentiment analysis, keyword/entity extraction,
  TF-IDF vectorization, cosine-similarity information retrieval.
- **Agentic AI:** a tool-calling orchestrator that selects which of 12 tools to invoke
  per request, with a full, auditable action log — not a single prompt-to-LLM call.
- **Database Management Systems:** relational schema design, foreign keys, indices,
  audit-log table pattern.
- **Software Engineering:** modular layered architecture, defensive error handling,
  graceful degradation (DEMO_MODE), automated test suite.
- **Data Analytics:** aggregate metrics, multi-chart dashboard, SLA-breach detection.
- **Information Retrieval:** duplicate detection and recurring-issue mining via
  vector-space similarity.

---

## 🎤 Viva Preparation

### A. 30 Important Viva Questions & Answers

1. **What does this project do?**
   It's an AI agent that reads a tenant's free-text maintenance complaint, understands
   it, classifies it, checks for safety risk, assigns priority, routes it to the right
   department, and tracks it to resolution — with full analytics for management.

2. **What makes this an "AI agent" and not just a chatbot?**
   It has 12 discrete tools and an orchestrator that decides which tools to run based
   on the input — a chatbot just answers with one LLM call; this agent performs a
   multi-step pipeline with database reads/writes and a visible action log.

3. **Why Gradio?**
   It lets us build a polished, multi-tab, interactive web UI in pure Python, with no
   separate frontend framework, which is ideal for a fast, demonstrable academic project.

4. **Why SQLite?**
   Zero configuration, a single file, built into Python's standard library — ideal for
   running the whole project on any evaluator's laptop with no server setup.

5. **Why use an AI agent instead of a single LLM prompt?**
   A single prompt can't reliably guarantee deterministic safety decisions, can't query
   a database, and gives no visible reasoning trail. Splitting the work into tools makes
   each decision explainable, testable, and independent of any one model's mood.

6. **Difference between a chatbot and an AI agent?**
   A chatbot maps input text to output text. An agent perceives (extracts structured
   info), decides (which tools to call), acts (calls tools, writes to a database), and
   can explain its actions — a chatbot does none of the middle two steps.

7. **How does the agent decide priority?**
   A deterministic weighted-scoring rule engine (`agent/decision_engine.py`) adds points
   for emergency keywords, severity, urgency, negative sentiment, and category risk,
   then thresholds the total into Critical/High/Medium/Low — fully explainable, never
   left to an LLM.

8. **How is emergency detection performed?**
   Keyword matching against a curated list (fire, smoke, gas leak, exposed wire,
   flooding, break-in, etc.) — deterministic and auditable, run identically regardless
   of whether LLM enrichment is enabled.

9. **How does semantic similarity work here?**
   Each complaint description is vectorized with TF-IDF (word/bigram frequencies
   weighted by rarity); cosine similarity between vectors measures how alike two
   complaints are in wording.

10. **Why TF-IDF instead of embeddings/sentence-transformers?**
    No large model download is required, so the project starts instantly and runs
    fully offline on any laptop — a deliberate reliability trade-off for a course
    project, explained in the README.

11. **Why Logistic Regression for the ML classifier?**
    It's fast to train, interpretable (coefficients per word/category), performs well
    on small-to-medium labeled text datasets, and is a standard, easily-explained
    baseline for text classification in an academic setting.

12. **What is an SLA in this context?**
    Service Level Agreement — the promised resolution deadline, computed as
    `submission time + N hours`, where N depends on priority (2h Critical, 24h High,
    72h Medium, 168h Low).

13. **How does duplicate detection work?**
    New complaint text is compared via TF-IDF cosine similarity against recent
    (within 72 hours) complaints from the same location; if similarity exceeds a
    threshold (0.55), it's flagged as a likely duplicate with the matched complaint ID.

14. **What happens if the LLM/API fails or no key is provided?**
    Every LLM call is wrapped in a try/except; on any failure (or if `DEMO_MODE` is
    active because no key is set) the system falls back to template-based text
    generation — the app never crashes and always returns a usable response.

15. **How is the database designed?**
    Five normalized tables: tenants, departments, maintenance_staff, complaints, and
    complaint_updates (an audit log of every status change), connected by foreign keys.

16. **What makes this an "AI" project overall?**
    It combines rule-based expert-system reasoning, a trained supervised ML classifier,
    NLP feature extraction (sentiment/urgency/entities), and vector-space information
    retrieval (similarity search) — multiple AI subfields working together.

17. **What makes this specifically "agentic" AI?**
    The orchestrator dynamically composes tool calls based on the input rather than
    following one fixed prompt template — e.g. a duplicate check only meaningfully runs
    if there's history, and the chat agent picks different tool subsets per question type.

18. **What's the accuracy of your ML model and is it meaningful?**
    ~100% on the held-out demonstration data — expected because the demo dataset is
    templated and cleanly separable; the README and code explicitly flag this as
    non-representative of real-world performance, which would require a larger, messier,
    real dataset.

19. **How do you avoid the app crashing on missing files?**
    Every file/model access is wrapped defensively — `ml/classifier.py` checks file
    existence before loading and falls back to rule-based classification; the database
    layer creates tables if missing; empty DataFrames are handled explicitly everywhere.

20. **How does the chat agent (Tab 2) decide what to do?**
    It inspects the message for cues — a complaint ID pattern, "similar"/"duplicate"
    keywords, "my complaints" phrasing, or management-insight phrasing — and routes to
    the matching tool combination; otherwise it treats the message as a new complaint-like
    query and runs the standard triage tools.

21. **What's the difference between severity and priority here?**
    Severity is one input signal (how bad the issue itself sounds, from keywords) fed
    into the priority score, which also incorporates urgency, sentiment, emergency
    status, and category risk.

22. **How would you extend this to production scale?**
    Swap SQLite for PostgreSQL, add authentication, replace TF-IDF similarity with
    sentence-transformer embeddings, retrain the ML model on real historical data, and
    add push notifications.

23. **What Python libraries power the ML pipeline?**
    scikit-learn for TF-IDF vectorization, Logistic Regression, train/test split, and
    evaluation metrics; joblib for persisting the trained model.

24. **How is sentiment analysis implemented without heavy NLP libraries?**
    A lexicon-based approach — curated positive/negative word lists scored against the
    complaint text, adjusted for exclamation marks and ALL-CAPS emphasis — fully offline
    and explainable.

25. **What does "explainable AI" mean in this project?**
    Every classification/priority decision returns a plain-English reason (matched
    keywords, contributing score factors) rather than a bare label — shown in the UI's
    "Why?" fields.

26. **How do you detect recurring issues for management?**
    Group complaints by (category, location) and flag groups with 3+ occurrences —
    surfaced in the AI Insights tab as candidates for preventive maintenance.

27. **Why did you separate rule-based logic from the optional LLM calls?**
    So safety-critical decisions (emergency, priority) are 100% reproducible and
    auditable, and the system remains fully functional and demonstrable even with zero
    external API access — a requirement for reliable classroom evaluation.

28. **What is DEMO_MODE and how is it triggered?**
    A config flag (`utils/config.py`) that's automatically `True` whenever no
    `OPENAI_API_KEY` is set (or can be forced via `FORCE_DEMO_MODE`); in this mode all
    natural-language generation uses templates instead of an LLM call.

29. **How do you test the system?**
    `tests/test_app.py` — 16 automated unit tests covering normal, emergency, duplicate,
    empty-input, long-text, multi-issue, angry-sentiment, and status-update scenarios,
    run directly against the agent/database layer (no browser needed).

30. **What was the hardest part of building this?**
    Making the priority/emergency logic both deterministic (safety-critical, always
    reproducible) and still genuinely responsive to nuanced language — balanced via the
    weighted rule-scoring system in `agent/decision_engine.py`.

### B. Key Concept Explanations
See questions 3–18 above — Why Gradio, Why SQLite, Why an agent, chatbot vs. agent,
how priority/emergency detection works, why TF-IDF, why Logistic Regression, what SLA
means, how duplicate detection works, what happens on LLM/API failure, and database
design are all answered there in interview-ready form.

### C. 2-Minute Project Presentation Script

> "Good [morning/afternoon]. My project is TenantCare AI — an AI agent for tenant
> complaint management. The problem: property managers handle complaints manually,
> with no automatic triage, so urgent safety issues like gas leaks or exposed wiring
> can sit unnoticed alongside routine requests like a slow drain.
>
> My system lets a tenant type their complaint in plain English. An AI agent — not a
> single chatbot prompt, but an orchestrator with twelve distinct tools — extracts the
> location, sentiment, and urgency; classifies the category using a trained TF-IDF plus
> Logistic Regression model; checks a deterministic rule engine for emergency keywords;
> computes a weighted priority score; checks for duplicate complaints using cosine
> similarity; routes it to the right maintenance department; and estimates an SLA
> deadline — all in under a second, fully offline.
>
> Everything is visible through a six-tab Gradio interface: complaint submission, an
> agent chat you can ask questions like 'is this urgent?', a manager's complaint
> tracker, a live analytics dashboard with seven charts, an AI-generated management
> insights report, and tenant complaint history lookup.
>
> The key design decision I want to highlight: safety-critical decisions — emergency
> detection and priority — are never left to an unpredictable LLM. They run through an
> explainable, deterministic rule engine, while an optional LLM is used only to make the
> natural-language summaries sound nicer, with a template fallback if it's unavailable.
> That's what makes this reliably demonstrable, evaluable, and genuinely agentic AI."

### D. 5-Minute Detailed Demonstration Flow

1. **(30s)** Launch `python app.py`, show the console confirming DEMO_MODE and that the
   database auto-seeded with 150 demo complaints.
2. **(60s)** Tab 1: submit "There is smoke coming from the electrical socket in my
   kitchen, it smells like burning!" — point out the Critical priority, the safety-risk
   flag, the "Why?" reasoning, the department routing, and the generated tenant message.
3. **(45s)** Tab 2: ask the AI Agent "Show me similar complaints about noise" and "Is a
   leaking ceiling urgent?" — highlight the visible Agent Actions checklist proving
   which tools ran.
4. **(45s)** Tab 3: filter by Priority = Critical, then update one complaint's status
   to "In Progress" with a note.
5. **(45s)** Tab 4: refresh the dashboard, point out the 7 charts and the SLA breach
   count.
6. **(30s)** Tab 5: generate the AI Insights report, show recurring issues and
   SLA-approaching-breach list.
7. **(15s)** Tab 6: look up a tenant's history by ID.
8. **(30s)** Briefly show `ml/train_model.py` output (accuracy/precision/recall/F1 and
   the confusion matrix image) and run `python -m unittest tests.test_app -v` to show
   all 16 tests passing.

### E. Possible Examiner Questions & Strong, Simple Answers

- **"Isn't this just calling ChatGPT to do everything?"**
  No — by default (DEMO_MODE) there is zero LLM involvement at all; classification uses
  a trained scikit-learn model with a keyword fallback, emergency/priority use a
  deterministic rule engine, and even with an LLM key configured, it is only ever used
  to phrase summaries/messages more naturally, never to make the classification or
  priority decision.

- **"How do I know your ML model actually works and isn't hardcoded?"**
  Run `python ml/train_model.py` live — it trains on the CSV dataset from scratch, does
  an 80/20 split, and prints accuracy/precision/recall/F1 plus saves a confusion matrix,
  which I can show right now.

- **"What if two students run this and get different results?"**
  Priority and emergency detection are deterministic rule-based functions — they will
  always produce the same output for the same input text, on any machine.

- **"Why is your ML accuracy 100%? That looks suspicious."**
  The demonstration training dataset is synthetically templated for clean category
  separation, which the README and code both explicitly flag — it demonstrates the full
  ML pipeline and methodology correctly, but a real deployment would need a much larger,
  messier, real-world labeled dataset for a meaningful accuracy figure.

- **"What happens if I don't run `train_model.py`?"**
  The app still works perfectly — `ml/classifier.py` detects the missing model files and
  automatically falls back to the keyword-based rule classifier in `nlp/entity_extraction.py`.
