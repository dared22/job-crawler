# Candidate profile and ranking policy

This is the single source of truth for eligibility and fit. The deterministic pipeline enforces
hard gates and calculates the final score; the agent supplies normalized facts and a concise fit
reason from each posting.

## Candidate

- Early-career MSc candidate graduating in 2027.
- Core stack: Python, PyTorch, transformers/Hugging Face, LLMs/foundation models, CUDA/GPU,
  distributed training, time-series modelling and stochastic methods.
- Thesis: neural stochastic differential equations. ML combined with quantitative/stochastic
  finance is a distinctive strength.
- Primary targets: internships, summer placements, graduate programmes, new-grad and junior
  roles with 0–3 years of experience.

## Four search lanes

### 🔬 AI research

Search explicitly for Research Engineer, ML Research Engineer, Research Software Engineer,
Applied Scientist, MSc-eligible Research Scientist, Scientific ML Engineer and Research Intern.

Time-series research is a first-class specialty, including:

- time-series modelling and forecasting;
- neural SDEs and stochastic processes;
- sequential, state-space and probabilistic models;
- financial and economic time series;
- sensor, energy, climate and industrial forecasting;
- spatiotemporal modelling;
- foundation models for time series;
- anomaly detection and signal processing.

Relevant titles include Time Series Researcher, Forecasting Scientist, Research Engineer — Time
Series and Applied Scientist — Forecasting. Strongly boost time-series work that also involves
deep learning or quantitative finance.

### 🤖 AI engineering

AI Engineer, Machine Learning Engineer, Foundation Model/LLM Engineer, Deep Learning Engineer,
MLOps Engineer, inference engineer, ML platform/infrastructure engineer and applied GenAI roles.

### 📈 Quant + ML

Quantitative Researcher, Quant Developer/Engineer, Systematic Trading Researcher and ML roles in
trading, asset management, pricing, fintech or hedge funds. ML∩quant roles receive the strongest
cross-lane bonus.

### 📊 Data science at priority employers

Find Data Scientist, ML/Data Scientist, Product Data Scientist, Decision Scientist,
Data Science Intern and graduate data science programmes. Prioritize Python/SQL,
statistical modelling, experimentation/A-B testing, causal inference, forecasting,
optimization and production ML. Strong product data science is relevant even without
deep learning; dashboard-only BI, reporting and generic analyst roles are low-value.

The maintained target list is `employer_targets.json`, shared with the pipeline.
Search its 50 employer groups, including global tech/quant targets and these regional additions:

- Norway: Cognite, Equinor, DNB, Telenor and Kongsberg.
- Ireland: Workday, Salesforce, Mastercard, HubSpot and Intercom.
- Netherlands: ASML, Booking.com, Adyen, Uber, ING, Flow Traders, Da Vinci Trading,
  Maven Securities, bol, Picnic and TomTom, alongside Optiver and IMC.
- Switzerland: Roche, Novartis, UBS, Swiss Re, Zurich Insurance, ABB, Logitech and Swissquote.

Regional technical leaders are discovery targets, not automatically the highest-paying
employers. Prioritize strong technical roles and evidenced pay/earnings potential.
Comparable unlisted employers require explicit evidence. These are employer groups;
related legal names and known subsidiaries share one reporting cap.

Optimize for long-term earnings and technical development as well as immediate fit.
Show published compensation when available, including currency, period, base salary,
bonus and equity separately. Label sourced local/level-matched estimates as estimates.
If pay is unavailable, state that it is not disclosed; never infer a salary from brand.
Do not impose a numeric salary floor without a user-specified country/role threshold.
Internship pay must not be presented as annual full-time total compensation.

Keep the MSc/2027 graduation and internship/graduate/junior eligibility gates.
A high salary or prestigious employer never overrides eligibility.

## Geography

- Search all of Europe and remote-Europe.
- Primary weekly coverage: Norway, Ireland, Netherlands and Switzerland; search these first.
- UK and wider Europe are secondary; retain strong matches when primary-market leads are exhausted.
- Search nationwide, including Oslo/Trondheim/Bergen/Stavanger, Dublin/Cork/Galway,
  Amsterdam/Eindhoven/Utrecht and Zürich/Basel/Lausanne/Geneva. Do not limit searches to capitals.
- Surface language and work-authorization requirements as visible caveats. Do not silently infer
  the candidate's eligibility.

## Hard gates

- Reject closed roles and passed deadlines.
- Reject undated roles posted more than 42 days ago unless explicitly rolling/open.
- Reject Staff, Principal, Lead, Director and Head roles, or jobs requiring 5+ years.
- Reject roles that require a completed or in-progress PhD. Keep “MSc or PhD” and “PhD
  preferred/nice-to-have”.
- Reject nationality/security-clearance requirements, pure frontend and non-technical PM roles.

## Ranking priorities

The pipeline scores role-lane fit, early-career suitability, technical overlap, time-series
research, ML∩quant overlap, priority geography, priority employers, statistical data science work and freshness. Strong evidence beats title-only
matches. Generic BI/dashboard work is low-value.

The agent may provide `manual_score_adjustment` from -10 to +10 only for evidence not captured by
the deterministic features. Never use it to bypass a hard gate.

## Report policy

Return up to 20 fresh eligible jobs within 12,000 characters, across all four lanes.
Preserve quality and deduplication; do not fill the report with weak matches. Represent
each lane when eligible matches exist. Prefer the four primary countries and represent
each when eligible matches exist. Allow up to six jobs per country and four per employer
group. Secondary countries fill remaining slots after primary-market matches.
