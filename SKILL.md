---
name: job-crawler
description: >-
  Weekly crawler for early-career AI research, AI engineering, time-series ML, quant+ML, and priority-employer data science jobs
  across Norway, the Netherlands, Switzerland, Ireland, the UK, and wider Europe. Finds live
  internships, graduate and junior roles; ranks and deduplicates them; and returns a validated
  Telegram digest. Use when asked to run or maintain the job crawler or weekly job summary.
metadata:
  {
    "openclaw":
      {
        "emoji": "💼",
        "requires": { "tools": ["web_search", "browser", "web_fetch", "read", "write", "exec"] },
      },
  }
---

# Job Crawler v2

Produce a concise weekly digest of new, live, early-career matches. Discovery and evidence review
use agent judgment; normalization, hard gates, scoring, diversity, state and rendering use the
deterministic pipeline.

## Files

- `profile.md`: candidate, lanes, eligibility and ranking policy.
- `sources.md`: collection policy and source invariants.
- `source_registry.json`: exact source/query registry.
- `employer_targets.json`: shared employer groups, aliases, market priorities and career URLs.
- `scripts/job_pipeline.py`: normalize, gate, score, select, persist, render and validate.
- `state/jobs.json`: v2 job ledger. Never replace it with a flat seen-URL list.
- `state/raw_candidates.json`: normalized input prepared during a run.
- `state/last_digest.txt`: exact validated Telegram output.

## Python environment

This project uses uv and Python 3.12. All scripts currently use the standard library;
there are no third-party dependencies. From this directory, run:

```bash
uv sync --locked
uv run python -m unittest discover -s tests -v
```

Run the pre-fetch script with `uv run python fetch_bindeleddet.py`. It fetches live
postings and updates `state/bindeleddet_candidates.json`. Use `uv add <package>` if
a third-party dependency is needed; commit both `pyproject.toml` and `uv.lock`.

## LinkedIn prefetch

Read `docs/linkedin.md` for setup, staging and verification rules. Read fresh
`state/linkedin_candidates.json` (schema version 1, completed partial/complete run,
`fetched_at` within 24 hours) alongside Bindeleddet. Treat every entry as an
unverified lead: check the live posting and full requirements before copying it to
final input, and set `evidence_verified: true` only after review. Prefer verified
employer/ATS URLs; attach the exact LinkedIn posting as `alternate_urls`. LinkedIn-only
jobs are eligible after equivalent live-status and requirements checks. Never pass
staging directly to the pipeline, infer location from query country, or treat a
successful detail read as proof that applications remain open.

Inspect partial-run errors. Missing, running, failed or stale staging must produce a
source warning and fall back to normal web-search discovery; continue other sources.
Use one `linkedin_<country>` source per country for actual attempts, including its
web-search fallback; queries do not count as independent sources. Do not fabricate
attempts for countries skipped because of budget or setup failure. Preserve at least
one independent non-LinkedIn source per country. Do not run the 15-minute collector
inside the scheduled agent's own 15-minute budget; its separate cron prefetch runs
at 07:35. For manual collection, run it before starting evidence review.

## Workflow

1. Read `profile.md`, `sources.md`, `source_registry.json`, `employer_targets.json` and the current ledger.
2. Gather current postings. Attempt priority-1 sources first, then use priority-2/3 sources to fill
   country or lane gaps. Search Norway, Ireland, Netherlands and Switzerland first, with at least two independent
   source attempts per country. Search the UK and wider Europe as secondary markets.
3. Open promising canonical postings and extract evidence. Do not invent deadlines, experience,
   PhD, language or authorization requirements.
4. Write `state/raw_candidates.json` with this shape:

```json
{
  "generated_at": "2026-09-19T12:00:00+02:00",
  "minimum_score": 55,
  "max_results": 20,
  "sources": [
    {"id": "jobs_ch", "country": "CH", "status": "ok", "new_count": 3}
  ],
  "candidates": [
    {
      "title": "Research Engineer — Time Series",
      "company": "Example AI",
      "location": "Zürich",
      "country": "CH",
      "url": "https://canonical.example/jobs/123",
      "source": "jobs_ch",
      "description": "Evidence-rich description or faithful summary",
      "requirements": "Degree and experience wording",
      "skills": ["Python", "PyTorch", "forecasting"],
      "lane": "ai_research",
      "seniority": "graduate",
      "posted_at": "2026-09-15T10:00:00Z",
      "deadline": "2026-10-15T23:59:59Z",
      "rolling": false,
      "open": true,
      "phd_required": false,
      "security_clearance": false,
      "years_required": 0,
      "language_requirement": "English",
      "work_authorization": "Check Swiss eligibility",
      "why": "Direct time-series research match using PyTorch and probabilistic modelling."
    }
  ]
}
```

5. Run the pipeline with commit enabled:

```bash
cd /home/pashatheboss1/.openclaw/workspace/skills/job-crawler
uv run python scripts/job_pipeline.py state/raw_candidates.json --commit
```

The command updates the ledger only after the digest passes validation. It retains rejected and
eligible-but-unreported records with reasons, suppresses reported jobs, and reconsiders a posting
when its content changes.

6. Read `state/last_digest.txt` and return its contents exactly. The first character of the reply
must be `💼`; do not add a preamble, explanation, code fence or sign-off. The file is the entire
Telegram report. OpenClaw splits it into messages within Telegram limits.

## Input rules

- Use canonical URLs and one candidate per actual job.
- `lane` is one of `ai_research`, `ai_engineering`, `quant_ml`, `data_science`. Omit only when the pipeline can
  safely infer it.
- Surface uncertain language/work-authorization requirements as caveats; do not silently reject
  them.
- A factual hard-gate field must reflect the canonical posting. Do not mark a role PhD-required
  when the PhD is merely preferred or an MSc is accepted.
- Never write directly to `state/jobs.json` or `state/last_digest.txt`; use the pipeline.

## Failure behavior

- If a source blocks or fails, record it in `sources` and continue.
- If the pipeline fails validation, do not commit state and do not emit a partial digest. Fix the
  input or rendering issue and rerun once.
- Do not send messages directly. The scheduled job's announce delivery handles Telegram after the
  final reply.

## Report size and data science evidence

- Set `max_results` to 20. The report budget is 12,000 characters; return the complete validated
  file so scheduled delivery can split it into multiple Telegram messages. Never summarize it
  into a shorter reply. Fewer than 20 results is correct when quality, diversity or size requires it.
- Search all four lanes explicitly. For data science, apply the priority-employer policy in
  `profile.md`; do not broaden it to generic BI or unrelated analyst jobs.
- For an employer outside `employer_targets.json`, supply `employer_tier: "elite"`,
  `employer_evidence` and an HTTPS `employer_evidence_url` supporting comparable technical
  standing and compensation potential. A famous brand alone is not evidence of role-specific pay.
- Optional pay fields: `compensation` (currency, range, period, base/bonus/equity breakdown),
  `compensation_basis` (`employer_disclosed` or `estimate`), `compensation_source_url`.
  Estimates require comparable country, role and seniority, with date and sample limitations
  in the summary. Do not substitute US or senior salaries for European graduate pay.
  When unavailable, leave pay fields empty; do not invent a range.
