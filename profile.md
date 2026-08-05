# Candidate profile & scoring rubric

This file is the single source of truth for *what to search for* and *how to score* each
posting. The job_crawler skill reads it every run. Score each posting 0–100, apply the
multiplier, sort highest-first.

## Who I am (for the "why it fits" line)
Early-career ML/AI + quant candidate. Thesis on **neural SDEs** (neural stochastic
differential equations) — the intersection of deep learning and quantitative/stochastic
finance is my single most differentiated wedge. Core stack: Python, PyTorch,
transformers/Hugging Face, LLMs/foundation models, CUDA/GPU + distributed training,
time-series & stochastic methods.

**Status / timeline:** Graduating in **2027** (next year) at **MSc level — I do NOT have a
PhD and am not pursuing one.** Internships, summer placements, new-grad and graduate-programme
roles are squarely in scope and are the **primary target** — treat them as first-class, not
afterthoughts.

## Two equally-weighted title buckets
Run these as two equally-weighted lanes — neither lane should crowd the other out.

**ML/AI bucket:** Machine Learning Engineer, AI Engineer, Applied Scientist,
Research Engineer, ML Research Engineer, Foundation Model Engineer, LLM Engineer,
Deep Learning Engineer, MLOps Engineer, ML Platform / Infrastructure Engineer.

**Quant bucket:** Quantitative Researcher, Quant Developer, Quant Engineer,
Systematic Trading Researcher, "ML Engineer + (trading OR fintech OR hedge fund)".

**Internship & graduate lane (applies across BOTH buckets above — search these explicitly):**
ML/AI Intern, Quant Intern, Research Intern, Summer Analyst / Summer Internship (Quant/ML),
Graduate Programme, Graduate Engineer, Graduate ML/Quant, New Grad, Trainee, Working-student.
These often don't surface under the senior-sounding titles, so query them on their own.

**Norwegian variants (for finn.no):** maskinlæring, kunstig intelligens, ML-ingeniør,
data scientist, kvantitativ.

## Geography filter
- **Scope:** All Europe + remote-EU.
- **Amsterdam = priority cluster** — Optiver, IMC, Flow Traders, Da Vinci, Maven.
  Surface these to the top even when the wider European net is noisy.
- **Norway:** weight **Oslo** highest.

## Seniority gate
- **Keep (in priority order):** **internships / summer placements → graduate programmes &
  new-grad → junior/mid (0–3 yr).** Graduating in 2027, so internships and graduate roles are
  the bullseye — give them a visible ranking boost (see rubric), don't bury them under mid-level
  full-time roles.
- **Auto-reject:** Staff / Principal / Lead; anything stating **5+ years required**; roles
  framed as **senior / experienced-hire**.

## Freshness / application-deadline gate (CRITICAL — must still be applicable today)
Only surface roles I can **still apply to**. Compute everything relative to **today's date at
run time**. A great match I can't apply to is worse than useless — last run sent expired ones.
- **Drop if the application deadline has passed.** finn.no shows "Frist" / "Søknadsfrist";
  LinkedIn and others show "apply by", "closes", "deadline". Past deadline → drop entirely.
- **Drop if the posting is closed/expired** — LinkedIn "No longer accepting applications",
  "Closed", removed/404 ad pages.
- **Drop stale undated posts:** no deadline **and** posted more than ~6 weeks ago
  ("30+ days ago", old timestamp) → treat as likely expired, drop.
- **Keep** rolling/open applications and graduate programmes with a **future start date** as
  long as applications are still open (a 2027 start with open applications is good).
- If you genuinely can't determine a deadline but the post looks recent (<3 weeks) → keep and
  label it "deadline unknown". When in doubt on an old post, drop it.
- **Capture each kept role's deadline / posted age** — it must appear in the summary so I can
  see at a glance that it's live.

## Scoring rubric (per posting)
- **High weight (ML side):** PyTorch, transformers / Hugging Face, LLMs / foundation models,
  CUDA / GPU + distributed training / training-infra, Python.
- **High weight (quant side):** time-series modelling, stochastic / differential-equation
  methods, systematic strategies.
- **★ Bonus multiplier:** when a posting touches **both** ML **and** quantitative finance
  (the neural-SDE overlap), multiply its score up — it should **rank to the very top**, not
  just add a few points. This intersection is the rarest, most differentiated match.
- **★ Graduate / internship boost:** internships, summer placements, graduate programmes and
  explicit new-grad roles get a strong ranking boost that **stacks** with the ML∩quant
  multiplier. I'm early-career graduating in 2027, so these are the most actionable — a
  graduate/intern role that is *also* ML∩quant belongs at the very top of the list.
- **Medium weight:** backend / APIs, Postgres, Docker, Azure, PySpark / data engineering.
- **Low / neutral:** generic "data scientist" duties (dashboards, BI).

## Hard excludes (drop entirely)
- Pure frontend.
- Non-technical PM.
- **Any role that requires a PhD** (completed or in-progress) as a hard requirement — I don't
  have one and am not pursuing one. ✅ KEEP roles where a PhD is only "preferred / nice-to-have"
  or listed as "MSc **or** PhD" (an MSc qualifies). Drop only the hard PhD gates.
- Anything requiring nationality / security clearance.
- 5+ year minimums.

## Volume note
Casting wide (two lanes + all of Europe) pulls volume, so the **bonus multiplier** and the
**seniority gate** are what keep the top of the list signal-rich. Lead with the ML∩quant
matches and the Amsterdam/Oslo clusters; let the long tail fall below.
