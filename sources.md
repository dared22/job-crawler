# Sources & query entry points

Concrete URLs and query templates for the job_crawler skill. Buckets and Norwegian variants
are defined in `profile.md` — this file is the *where to look*.

## ⚙️ Tooling reality (read first)
This agent's actual tools are **`web_search` (Brave)**, a headless **`browser`** tool, and
**`web_fetch`**. There is **no `firecrawl`** here. Pick the tool per source:
- **JS-heavy / bot-protected sites** (finn.no, bindeleddet, arbeidsplassen) → use the
  **`browser`** tool to render the page, *or* `web_search` with a `site:` filter. **Do NOT
  rely on `web_fetch` for these — it gets a blank/blocked page** (that's why finn.no returned
  nothing before).
- **ATS JSON boards** (Greenhouse / Lever) and plain HTML/Markdown → use **`web_fetch`** (fast,
  structured, dated, not blocked).
- `web_search` is the most reliable broad-coverage path — lead with it, then deepen with the
  browser/web_fetch on the specific postings you want to score.
- Budget tool calls: a handful per source. If a source blocks or returns nothing, **note it in
  the summary footer and move on** — never fail the whole run over one source.

## 1. finn.no  (Norway / Oslo) — use the `browser` tool, NOT web_fetch
Full-time search URL (URL-encode the query):
`https://www.finn.no/job/fulltime/search.html?q=<QUERY>`
Open it with the **`browser`** tool (it's JS-rendered + bot-protected). Run the Norwegian
variants + English ML/quant terms + the grad/intern terms:
- `q=maskinlæring`, `q=kunstig%20intelligens`, `q=machine%20learning`, `q=quantitative`,
  `q=data%20scientist`, `q=graduate`, `q=trainee`, `q=internship`
Each result links to an ad page — finn.no's current format is
`https://www.finn.no/job/ad/<id>` (older `…/fulltime/ad.html?finnkode=<id>` may still appear).
The **numeric ad id is the dedup fingerprint** (normalise to one canonical form). Open the ad to read the description and the **deadline
("Frist" / "Søknadsfrist")** for the freshness gate. Oslo-weight per profile.
**Fallback if the browser tool struggles:** `web_search` →
`site:finn.no/job machine learning Oslo`, `site:finn.no/job maskinlæring`, etc.

## 2. bindeleddet.no  (NTNU "Bedriftskontakt") — use the `browser` tool — FORCE A REAL ATTEMPT
This site is a **pure client-side SPA**: every path — `/jobs`, `/jobb`, and individual posting
URLs like `/jobs/<id>/` — returns **HTTP 404 on a plain fetch**, because the server has no route
for them at all; the content only exists after client-side JavaScript renders it. This has
caused this source to **return zero postings in every run since the skill was created** —
treat that streak as evidence of a tool/procedure failure, not proof the source is empty.
Do not let this run repeat that streak on autopilot.

Concrete procedure — follow every step before concluding "nothing found":
1. Open `https://bindeleddet.no/jobs` with the **`browser`** tool (try `https://www.bindeleddet.no`
   too if the bare domain doesn't render).
2. **Wait for the SPA to hydrate before reading the page** — an immediate read after page-load
   often only catches an empty shell (title, no body). If your browser tool supports a
   wait/sleep or "wait for selector", use it; otherwise take a second snapshot a few seconds
   after the first and compare — if the second has more content, the first was read too early.
3. In the rendered page, look for links matching `/jobs/<numeric-id>/` — those are individual
   postings.
4. Open each candidate posting with the **`browser`** tool (same wait-and-recheck approach) to
   read title, company, and deadline.
5. **Budget up to 3 browser-tool attempts on this source** (more than the usual "handful" —
   its 100% historical failure rate earns it a harder push) before giving up.
6. In the summary footer, distinguish *why* you got nothing, if you do: `bindeleddet — page
   never rendered (tool issue)` is a different signal than `bindeleddet — rendered, zero
   postings`. Never just write "nothing new" without knowing which one happened.

Each posting's canonical URL (`https://bindeleddet.no/jobs/<id>/`) is the fingerprint.

## 3. arbeidsplassen.nav.no  (NAV — Norway's official national job board)  [NEW]
Aggregates most finn.no + public-sector ads — best single net for Norway/Oslo. Use
`web_search` with a `site:` filter (the public JSON feed API now needs a Bearer token, so skip
the API unless one is configured):
- `site:arbeidsplassen.nav.no maskinlæring`
- `site:arbeidsplassen.nav.no "machine learning" Oslo`
- `site:arbeidsplassen.nav.no kvantitativ OR data scientist`
Each ad's canonical URL = fingerprint; open it for the deadline.

## 4. Amsterdam priority prop firms — hit their own boards directly  [NEW]
These are dated, structured, and not blocked — ideal `web_fetch` targets, and they carry the
graduate/internship roles that matter most.
- **Optiver** — Greenhouse board token `optiverus`. JSON list:
  `https://boards-api.greenhouse.io/v1/boards/optiverus/jobs` (fields include `title`,
  `location`, `updated_at`, `absolute_url`); per-job detail at `.../jobs/<id>`. Also the
  human pages `https://www.optiver.com/join-us/graduate/` and `.../internships/`.
- **IMC** — try Greenhouse `https://boards-api.greenhouse.io/v1/boards/imc/jobs`; if that 404s,
  `web_search site:careers.imc.com (graduate OR intern) (quant OR machine learning)`.
- **Flow Traders / Da Vinci / Maven** — `web_search`:
  `site:flowtraders.com careers (graduate OR intern)`,
  `site:davincitrading.com/careers (graduate OR quant)`,
  `site:mavensecurities.com careers (graduate OR intern)`.
For Greenhouse JSON, `updated_at` feeds the **freshness gate** and `absolute_url` is the
fingerprint. These firms run rolling/EOI applications — keep open ones even with a 2027 start.

## 4b. NBIM — Norges Bank Investment Management (Oljefondet, Oslo)  [NEW]
Norway's sovereign wealth fund — a top-priority Oslo employer for ML/quant/tech roles.
`web_fetch` the listings page (it renders fine), then follow into individual postings:
`https://www.nbim.no/no/om-oss/jobb-i-oljefondet/ledige-stillinger/`
Individual postings live on the **Webcruiter** ATS — URL pattern
`https://398280.webcruiter.no/main/recruit/public/<position-id>` — that URL is the dedup
fingerprint, and Webcruiter pages show the application deadline ("søknadsfrist"). NBIM is small-
volume (often only a handful of openings) but high-relevance: weight its quant / data science /
ML / technology / graduate roles up, and apply the seniority gate (drop "Head of" / lead roles).

## 5. LinkedIn  (web_search only — no login)
Query templates — run several, mixing buckets, geography, seniority:
- `site:linkedin.com/jobs "Machine Learning Engineer" (graduate OR junior OR "0-3 years") Europe`
- `site:linkedin.com/jobs "AI Engineer" (graduate OR junior) remote Europe`
- `site:linkedin.com/jobs "Quantitative Researcher" (graduate OR junior) Amsterdam`
- `site:linkedin.com/jobs "Quant Developer" (Optiver OR IMC OR "Flow Traders" OR "Da Vinci" OR Maven)`
- `site:linkedin.com/jobs ("ML Engineer" OR "Applied Scientist") (Oslo OR Norway) junior`
- `site:linkedin.com/jobs ("Research Engineer" OR "LLM Engineer") graduate Europe`
- `site:linkedin.com/jobs ("ML Intern" OR "Machine Learning Intern" OR "AI Intern") Europe 2027`
- `site:linkedin.com/jobs ("Quant Intern" OR "Quantitative Intern" OR "Summer Internship" quant) Amsterdam`
- `site:linkedin.com/jobs ("Graduate Programme" OR "Graduate Engineer" OR "New Grad") (machine learning OR quant) Europe`
- `site:linkedin.com/jobs ("Summer Analyst" OR internship) (Optiver OR IMC OR "Flow Traders" OR "Da Vinci" OR Maven)`
Use the resolved LinkedIn job URL as the fingerprint. Open promising results for the
description + deadline; some are gated — score from the snippet and note it.

## 6. Extra graduate / internship sources  [NEW]
- **GitHub new-grad / internship lists** — `web_fetch` the raw README (plain dated markdown,
  never blocked), then filter to Europe / remote-EU:
  - `https://github.com/speedyapply/2026-AI-College-Jobs` (AI/ML internships + new-grad, updated daily)
  - (also try `https://github.com/SimplifyJobs/Summer2026-Internships` if it exists at run time)
- **thehub.io** — Nordic startup jobs (good for Oslo): `web_search site:thehub.io (machine learning OR data OR AI) Oslo`.
- **kode24.no** — Norwegian dev jobs: `web_search site:kode24.no/jobb (machine learning OR data)`.
- **jobbnorge.no** — academic / research Norway: `web_search site:jobbnorge.no (machine learning OR data scientist OR kvantitativ)`.

## 7. Big-tech Europe internships — Google & Amazon  [NEW]
High-volume ML/DS/AI internship + new-grad pipelines. Both are Europe-wide, so **filter hard to
Europe** (Oslo/Nordics and Amsterdam/NL first, then London/Dublin/Zurich/Munich/Berlin/Paris/
Madrid/Warsaw) and drop US/APAC hits. Apply the **PhD hard-exclude** from `profile.md` — a large
share of Google Research / Amazon Applied Scientist openings are PhD-only; keep "MSc or PhD".
Pasha graduates 2027, so target **2027 summer internships** and 2026/2027 new-grad intakes.

- **Amazon** — `amazon.jobs` exposes a JSON search endpoint that is **not** blocked, so prefer
  **`web_fetch`** here:
  `https://www.amazon.jobs/en/search.json?base_query=<QUERY>&result_limit=100&sort=recent`
  Useful `base_query` values: `machine learning intern`, `applied scientist intern`,
  `data scientist intern`, `ML engineer graduate`. Response fields: `title`, `location`,
  `posted_date` (→ freshness gate), `job_path` (→ fingerprint, prefix with
  `https://www.amazon.jobs`). Also worth a pass:
  `https://www.amazon.jobs/en/teams/internships-for-students` and Amazon Science's research
  internships at `https://www.amazon.science/careers`.
  Fallback: `web_search site:amazon.jobs (intern OR graduate) "machine learning" Europe`.

- **Google** — `careers.google.com` is JS-rendered, so **do NOT `web_fetch` it**; use the
  **`browser`** tool or lead with `web_search`:
  `https://www.google.com/about/careers/applications/jobs/results/?employment_type=INTERN&q=<QUERY>`
  with `q=machine learning`, `q=data science`, `q=AI`. Named student programmes to search by
  name: **STEP** (Student Training in Engineering Program), **Student Researcher**,
  **Software Engineering Intern, Machine Learning**. Fallback queries:
  - `site:google.com/about/careers/applications/jobs ("machine learning" OR AI) intern Europe`
  - `site:google.com/about/careers "Student Researcher" (Zurich OR London OR Munich OR Paris)`
  The resolved `.../jobs/results/<id>-<slug>` URL is the fingerprint. Google posts *and pulls*
  listings quickly — always confirm the posting is still live before including it.

Both are large enough to flood the summary: cap at the **top ~3 per company per run** after
scoring, and let the ML∩quant + graduate/internship boosts decide which survive.

## Notes
- Always normalise the fingerprint (strip tracking query params, lowercase host; finn.no →
  `finnkode`; Greenhouse → `absolute_url`) before comparing against `state/seen_jobs.json`.
- Capture each posting's **deadline / posted date** so the freshness gate (profile.md) and the
  summary can use it.
- If a source returns nothing for a run (site change / block / 404), note it in the summary's
  footer rather than failing the whole run.
