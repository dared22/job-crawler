# Source policy

The machine-readable registry is `source_registry.json`. Read it at the start of every crawl and
attempt sources in priority order. A healthy weekly run must attempt at least two independent
source attempts for each of Norway, Ireland, the Netherlands and Switzerland. These are the
primary markets; attempt at least one UK source as secondary coverage.

## Collection tiers

1. Direct employer/lab boards and structured ATS/API feeds. These are authoritative and normally
   provide stable URLs, dates and complete requirements.
2. National and graduate boards: jobs.ch, ETH/EPFL, gradireland, JobsIreland/IrishJobs,
   Gradcracker, Find a Job and jobs.ac.uk.
3. LinkedIn and general web search for discovery and gaps. Never make LinkedIn the sole source for
   a country or role lane.

## Tool selection

- Greenhouse, Lever, public JSON, plain HTML and Markdown: `web_fetch`.
- JS-heavy or protected pages such as finn.no and Google Careers: browser, then `web_search`
  fallback.
- LinkedIn: fresh `state/linkedin_candidates.json` collected with Agent-Reach; follow
  `docs/linkedin.md`. Fall back to `web_search` on missing/stale/failed collection.
- IrishJobs and other gated boards: `web_search`; open only promising results.
- Bindeleddet: read `state/bindeleddet_candidates.json`. If stale or missing, fetch
  `https://apiv2.bindeleddet.no/jobs/`; never browse its SPA.

## Required explicit searches

For each of Norway, Ireland, the Netherlands and Switzerland, combine early-career terms with all four lanes:

- AI research: `research engineer`, `ML research engineer`, `applied scientist`, `research
  software engineer`, `research intern`;
- time series: `time series`, `forecasting`, `state space`, `sequential modelling`, `scientific
  machine learning`, `neural SDE`, `stochastic`, `spatiotemporal`, `signal processing`;
- AI engineering: `AI engineer`, `machine learning engineer`, `foundation model`, `LLM engineer`,
  `inference`, `training infrastructure`;
- quant + ML: `quantitative researcher`, `quant developer`, `systematic trading`, `machine
  learning trading`;
- data science: `data scientist`, `product data scientist`, `decision scientist`,
  `data science intern`, `graduate data science`, combined with target employers from
  `profile.md` and the country;
- early career: `graduate`, `new grad`, `junior`, `intern`, `summer`, `2027`, `0–3 years`.

Use the local-language Swiss variants when useful (`KI`, `maschinelles Lernen`, `prévision`,
`apprentissage automatique`), while retaining English queries because many Swiss research and
engineering roles are advertised in English.

## Freshness and evidence

- Open the canonical posting before reporting it. Capture posted date, deadline, seniority, PhD
  wording, years required, language and work-authorization restrictions.
- Treat “rolling” as open only when the canonical page is live.
- Keep source failures isolated. Add each attempt to the payload's `sources` array with status
  `ok`, `nothing_new`, `blocked`, `stale` or `error`.
- Cap deep inspection to the strongest leads. A source failure must not abort the run.

## Source-specific invariants

- finn.no: canonical fingerprint is `https://finn.no/job/ad/<id>`.
- Bindeleddet: canonical link is `https://bindeleddet.no/jobs/<id>/`, never the API URL.
- Greenhouse/Lever: use the public job URL and ATS job ID; capture update timestamps.
- Google: confirm the resolved job page remains live; listings are pulled quickly.
- Amazon: prefer its JSON search response, then open shortlisted canonical pages.
- Direct research boards are essential: Swiss AI/Apertus, ETH/EPFL, ADAPT/CeADAR/Insight,
  DeepMind, Anthropic and Microsoft Research Cambridge.

## Compensation evidence

Prefer employer-disclosed pay. If using a salary dataset, verify employer, country,
role, level, currency, date and whether figures are base or total compensation.
Label estimates and limitations explicitly. Missing pay must not block an otherwise
strong priority-employer role. Inspect canonical requirements rather than assuming
that data science titles require a PhD.

## Employer breadth and search order

Read `employer_targets.json`. Search regional employer groups as well as global tech/quant
firms; use the registered group queries to discover leads, then inspect authoritative
career/ATS pages for the strongest eligible matches. Start in the four primary countries.
Use nationwide locations and local terms (`data scientist`, `data science`, `datavitenskap`,
`maskinlæring`, `Datenwissenschaft`, `science des données`) when useful. Search all four
lanes, not just data science. Do not require that every employer has an open role.
Rotate deeper board inspections across weeks within the runtime budget; do not let a
long employer list prevent completing primary-country coverage and report validation.
