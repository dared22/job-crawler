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

## Three equal search lanes

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

## Geography

- Search all of Europe and remote-Europe.
- Explicit weekly coverage: Norway, Netherlands, Switzerland, Ireland and the UK.
- Priority clusters: Oslo, Amsterdam, Zürich, Dublin and London.
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
research, ML∩quant overlap, priority geography and freshness. Strong evidence beats title-only
matches. Generic BI/dashboard work is low-value.

The agent may provide `manual_score_adjustment` from -10 to +10 only for evidence not captured by
the deterministic features. Never use it to bypass a hard gate.
