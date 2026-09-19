#!/usr/bin/env python3
"""
Deterministic pre-fetch for bindeleddet.no, run by system cron BEFORE the
weekly job-crawler agent turn (see sources.md section 2 for why this exists:
apiv2.bindeleddet.no is a public unauthenticated JSON API backing the site's
SPA frontend).

Does the parts that don't need LLM judgment - fetch, dedup against
seen_jobs.json, and the deadline/staleness freshness gate - and writes the
survivors to state/bindeleddet_candidates.json for the agent to `read`.
Never writes to seen_jobs.json itself; the agent still fingerprints
everything it's shown in its normal step 5, same as every other source.
"""

import json
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SEEN_PATH = BASE_DIR / "state" / "seen_jobs.json"
LEDGER_PATH = BASE_DIR / "state" / "jobs.json"
OUT_PATH = BASE_DIR / "state" / "bindeleddet_candidates.json"
API_URL = "https://apiv2.bindeleddet.no/jobs/"
FRONTEND_URL_TMPL = "https://bindeleddet.no/jobs/{id}/"
STALE_UNDATED_AFTER = timedelta(weeks=6)

TAG_RE = re.compile(r"<[^>]+>")


def strip_html(text: str) -> str:
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", text or "")).strip()


def load_seen() -> set:
    """Suppress only jobs already reported by v2; retain legacy compatibility."""
    try:
        ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
        return {
            fingerprint
            for fingerprint, record in ledger.get("jobs", {}).items()
            if record.get("status") in {"reported", "legacy_seen"}
        }
    except (FileNotFoundError, json.JSONDecodeError, AttributeError):
        pass
    try:
        return set(json.loads(SEEN_PATH.read_text(encoding="utf-8")))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def fetch_jobs() -> list:
    req = urllib.request.Request(API_URL, headers={"User-Agent": "job-crawler/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def parse_dt(value):
    if not value:
        return None
    return datetime.fromisoformat(value)


def main() -> int:
    try:
        jobs = fetch_jobs()
    except Exception as exc:
        print(f"FETCH FAILED: {exc}", file=sys.stderr)
        return 1

    seen = load_seen()
    now = datetime.now(timezone.utc)

    candidates = []
    for job in jobs:
        url = FRONTEND_URL_TMPL.format(id=job["id"])
        if url in seen:
            continue

        deadline = parse_dt(job.get("deadline"))
        created_at = parse_dt(job.get("created_at"))

        if deadline is not None and deadline < now:
            continue
        if deadline is None and created_at is not None and (now - created_at) > STALE_UNDATED_AFTER:
            continue

        candidates.append({
            "id": job["id"],
            "url": url,
            "title": job.get("title"),
            "company_name": job.get("company_name"),
            "location": job.get("location"),
            "job_type": job.get("job_type"),
            "year_levels": job.get("year_levels"),
            "deadline": job.get("deadline"),
            "created_at": job.get("created_at"),
            "description": strip_html(job.get("description", "")),
        })

    OUT_PATH.write_text(
        json.dumps({
            "fetched_at": now.isoformat(),
            "source": API_URL,
            "total_open_postings": len(jobs),
            "new_candidates": len(candidates),
            "candidates": candidates,
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"bindeleddet: {len(jobs)} open postings, {len(candidates)} new candidates -> {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
