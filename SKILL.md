---
name: job-crawler
description: >-
  Weekly crawler for early-career AI research, AI engineering, time-series ML, and quant+ML jobs
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
- `scripts/job_pipeline.py`: normalize, gate, score, select, persist, render and validate.
- `state/jobs.json`: v2 job ledger. Never replace it with a flat seen-URL list.
- `state/raw_candidates.json`: normalized input prepared during a run.
- `state/last_digest.txt`: exact validated Telegram output.

## Workflow

1. Read `profile.md`, `sources.md`, `source_registry.json` and the current ledger.
2. Gather current postings. Attempt priority-1 sources first, then use priority-2/3 sources to fill
   country or lane gaps. Every run must explicitly cover Switzerland, Ireland and the UK, plus
   Norway and the Netherlands.
3. Open promising canonical postings and extract evidence. Do not invent deadlines, experience,
   PhD, language or authorization requirements.
4. Write `state/raw_candidates.json` with this shape:

```json
{
  "generated_at": "2026-09-19T12:00:00+02:00",
  "minimum_score": 55,
  "max_results": 8,
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
python3 scripts/job_pipeline.py state/raw_candidates.json --commit
```

The command updates the ledger only after the digest passes validation. It retains rejected and
eligible-but-unreported records with reasons, suppresses reported jobs, and reconsiders a posting
when its content changes.

6. Read `state/last_digest.txt` and return its contents exactly. The first character of the reply
must be `💼`; do not add a preamble, explanation, code fence or sign-off. The file is the entire
Telegram message.

## Input rules

- Use canonical URLs and one candidate per actual job.
- `lane` is one of `ai_research`, `ai_engineering`, `quant_ml`. Omit only when the pipeline can
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
