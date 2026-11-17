# LinkedIn collection

LinkedIn supplements the existing employer and national-board sources. Its collector
writes unverified leads; the weekly agent verifies postings before adding them to
`state/raw_candidates.json`. The final pipeline rejects `evidence_verified: false`.

## Setup and acceptance

Install the pinned upstream release as a separate uv tool:

```bash
uv tool install https://github.com/Panniantong/Agent-Reach/releases/download/v1.6.1/agent-reach.zip
agent-reach add linkedin
uv run --locked python scripts/patch_linkedin_adapter.py
```

If CloakBrowser 0.6.3 fails with a missing `playwright._impl._js_handle` module,
its private environment needs the compatible Playwright version:

```bash
uv pip install --python ~/.agent-reach/tools/cloakbrowser/venv/bin/python playwright==1.55.0
agent-reach add linkedin
```

The installed OpenCLI adapter needs the repository's layout compatibility patch
for LinkedIn's newer pages (no h1 and an expandable description container). The
patch adds that extraction path and retains the legacy extractor. It changes only
Agent-Reach's private adapter; its original file is kept beside it as
`job-detail.js.job-crawler-original`. Reapply after an Agent-Reach/OpenCLI update:

```bash
uv run --locked python scripts/patch_linkedin_adapter.py
uv run --locked python scripts/patch_linkedin_adapter.py --check
```

From a terminal in the host's desktop session, run `agent-reach login linkedin`
and sign in yourself. Credentials and cookies stay in Agent-Reach's dedicated
browser directory. Never put them in this repository or chat. The collector does
not open login windows. An update of Agent-Reach's browser dependencies may require
reapplying the compatibility pin.

When connecting from a Mac over SSH, start XQuartz locally and use
`ssh -Y -C pashatheboss1@vault`. Run the login command inside that forwarded
session and keep it connected while signing in. If the window is on an old
display, run `agent-reach browser stop` before starting login again. SSH sets
`DISPLAY` automatically; do not set it to `:0` for remote viewing. After login,
saved sessions work in the default headless browser without SSH forwarding.

Verify a real search, then read one returned job URL:

```bash
agent-reach linkedin jobs "machine learning intern" --location Norway --limit 2 --backend opencli --timeout 60
agent-reach linkedin read "https://www.linkedin.com/jobs/view/JOB_ID" --backend opencli --timeout 60
```

For a bounded smoke test, copy the registry to a temporary file, keep only Norway
and one query in its `linkedin` section, and set `max_details` to 1. Run the
collector with `--registry /tmp/your-registry.json --output /tmp/linkedin-smoke.json
--budget-seconds 120`. Confirm a successful search and a nonempty detail description.
Run the reviewed sample through the pipeline with temporary ledger, legacy, output
and source-health paths; never use production paths for smoke testing.

Then enable the weekly schedule:

```bash
uv run python scripts/schedule_linkedin.py --acceptance-file /tmp/linkedin-smoke.json --install
```

Without `--install`, the command previews the complete resulting crontab. It
preserves unrelated entries and replaces only its own marked entry. Installation
requires fresh successful collection evidence and the Europe/Oslo host timezone.
Monday 07:35 collection finishes by 07:50, before the 08:00 agent run. The existing
Bindeleddet schedule remains independent.

## Collection contract

```bash
uv run --locked python scripts/fetch_linkedin.py
```

Settings live in the registry's `linkedin` section: 900 seconds overall, up to
450 seconds searching, five results per query and 30 detail reads. Five query
families cover the four lanes plus time-series research in NO, IE, NL, CH and UK.
Primary-country searches precede UK searches. Each family uses one plain-keyword
variant per ISO week, rotating internship/graduate/junior terms without increasing
the request count. Boolean OR/AND expressions caused HTTP 400 responses through
the installed adapter; keep these queries as plain phrases. This is a bounded supplement, not
exhaustive LinkedIn coverage. Search pacing is handled by Agent-Reach.

The versioned staging file contains `fetched_at`, `completed_at`, `status`,
`partial`, `attempts`, `sources`, `errors` and `candidates`. Each lead retains its
LinkedIn ID, canonical URL, query country/families, upstream company/location,
listing/pay text, description, detail outcome and `evidence_verified: false`.
Query country is a search hint, not proof of job location. Relative dates and
salary text are not automatically converted into posting dates or compensation.
`detail_status: fetched` means text was obtained, not that the position is live.

A fresh partial run can supply leads, but inspect its errors and limited detail
coverage. Missing/older-than-24-hour/running files cannot supply current evidence.
Only actual query attempts count toward coverage; use one LinkedIn source ID per
country regardless of how many queries or search fallbacks were attempted.

Login, verification, rate limits, timeouts, setup and backend failures stop this
LinkedIn run and preserve partial results. A missing individual job is skipped.
Only structured error codes are persisted; upstream messages may contain secrets.
Use the normal web-search fallback and other sources when LinkedIn fails. Never
retry around a verification challenge or channel cooldown.

## Reviewer responsibilities

Open the live posting and check its full requirements, application status,
location, MSc/PhD wording, experience, language, deadline and authorization rules.
Do not treat search cards, a successful read, or an apply URL as proof it is open.
Only verified jobs may enter the final input; set `evidence_verified: true` after
review, supply the existing candidate fields, and retain the existing scoring and
priority-employer policy. Missing information must remain unknown.

Prefer a checked employer/ATS URL. Include its corresponding LinkedIn URL in
`alternate_urls` only when it demonstrably refers to that exact job. LinkedIn-only
postings are eligible after the same checks. Alias matching uses exact normalized
URLs, never title/company similarity. Existing ledger records need no migration.

## Checks

```bash
uv run --locked python -m unittest discover -s tests -v
```

Tests use fixtures and mocked subprocesses; they never log into LinkedIn or write
production job state. Live acceptance is a separate, user-authenticated step.
