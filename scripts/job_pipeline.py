#!/usr/bin/env python3
"""Deterministic normalize, gate, rank, deduplicate, and Telegram rendering pipeline."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_LEDGER = BASE_DIR / "state" / "jobs.json"
DEFAULT_LEGACY = BASE_DIR / "state" / "seen_jobs.json"
DEFAULT_OUTPUT = BASE_DIR / "state" / "last_digest.txt"
DEFAULT_SOURCE_HEALTH = BASE_DIR / "state" / "source_health.json"
MAX_MESSAGE_CHARS = 3800
MAX_RESULTS = 8
VALID_LANES = {"ai_research", "ai_engineering", "quant_ml"}
TRACKING_PARAMS = {
    "fbclid", "gclid", "gh_src", "ref", "referrer", "source",
    "trk", "trackingid", "utm_campaign", "utm_content", "utm_medium",
    "utm_source", "utm_term",
}
COUNTRY_FLAGS = {
    "NO": "🇳🇴", "NL": "🇳🇱", "CH": "🇨🇭", "IE": "🇮🇪",
    "UK": "🇬🇧", "GB": "🇬🇧", "EU": "🇪🇺",
}
LANE_META = {
    "ai_research": ("🔬", "AI research"),
    "ai_engineering": ("🤖", "AI engineering"),
    "quant_ml": ("📈", "quant + ML"),
}


def parse_datetime(value: object) -> datetime | None:
    if not value:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        try:
            parsed = datetime.strptime(text, "%Y-%m-%d")
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def canonicalize_url(raw_url: str) -> str:
    raw_url = raw_url.strip()
    if not raw_url:
        return ""
    parts = urlsplit(raw_url)
    host = (parts.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    path = re.sub(r"/{2,}", "/", parts.path).rstrip("/") or "/"

    if host == "finn.no":
        match = re.search(r"/(?:job/ad|fulltime/ad\.html)/(\d+)", path)
        query = dict(parse_qsl(parts.query))
        job_id = match.group(1) if match else query.get("finnkode")
        if job_id:
            return f"https://finn.no/job/ad/{job_id}"

    if "linkedin.com" in host:
        match = re.search(r"/jobs/view/(?:[^/]*-)?(\d+)", path)
        if match:
            return f"https://linkedin.com/jobs/view/{match.group(1)}"

    query_pairs = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=False)
        if key.lower() not in TRACKING_PARAMS and not key.lower().startswith("utm_")
    ]
    query_pairs.sort()
    return urlunsplit(("https", host, path, urlencode(query_pairs), ""))


def clean_text(value: object, limit: int | None = None) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    text = text.replace("*", "")
    if limit and len(text) > limit:
        text = text[: limit - 1].rstrip() + "…"
    return text


def combined_text(job: dict) -> str:
    values = [
        job.get("title"), job.get("description"), job.get("requirements"),
        " ".join(job.get("skills", []) if isinstance(job.get("skills"), list) else []),
    ]
    return clean_text(" ".join(str(value or "") for value in values)).lower()


def infer_lane(job: dict) -> str:
    explicit = str(job.get("lane", "")).strip().lower()
    if explicit in VALID_LANES:
        return explicit
    text = combined_text(job)
    research_terms = (
        "research engineer", "research scientist", "research software", "applied scientist",
        "scientific machine learning", "time series", "time-series", "forecasting",
        "state space", "state-space", "sequential model", "neural sde", "stochastic",
        "probabilistic forecasting", "spatiotemporal", "signal processing",
    )
    quant_terms = (
        "quantitative", "quant developer", "systematic trading", "trading research",
        "market making", "asset management", "hedge fund", "pricing model",
    )
    ml_terms = (
        "machine learning", "deep learning", "pytorch", "transformer", "llm",
        "foundation model", "artificial intelligence", " ai ",
    )
    if any(term in text for term in research_terms):
        return "ai_research"
    if any(term in text for term in quant_terms) and any(term in text for term in ml_terms):
        return "quant_ml"
    return "ai_engineering"


def infer_seniority(job: dict) -> str:
    explicit = clean_text(job.get("seniority")).lower()
    if explicit:
        return explicit
    text = combined_text(job)
    if "intern" in text or "summer placement" in text or "working student" in text:
        return "internship"
    if any(term in text for term in ("graduate", "new grad", "new-grad", "trainee", "entry level")):
        return "graduate"
    title = clean_text(job.get("title")).lower()
    if re.search(r"\b(senior|staff|principal|lead|director|head)\b", title):
        return "senior"
    return "junior"


def content_hash(job: dict) -> str:
    stable = {
        "title": clean_text(job.get("title")),
        "company": clean_text(job.get("company")),
        "location": clean_text(job.get("location")),
        "description": clean_text(job.get("description")),
        "deadline": clean_text(job.get("deadline")),
        "requirements": clean_text(job.get("requirements")),
    }
    payload = json.dumps(stable, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:20]


def hard_gate(job: dict, now: datetime) -> str | None:
    text = combined_text(job)
    if job.get("open") is False or any(term in text for term in ("no longer accepting applications", "position closed", "vacancy closed")):
        return "closed"
    deadline = parse_datetime(job.get("deadline"))
    if deadline and deadline.date() < now.date():
        return "deadline_passed"
    posted_at = parse_datetime(job.get("posted_at"))
    if not deadline and not job.get("rolling") and posted_at and (now - posted_at).days > 42:
        return "stale_undated"
    if job.get("phd_required") is True or re.search(r"\b(ph\.?d|doctorate)\s+(is\s+)?required\b", text):
        return "phd_required"
    if job.get("security_clearance") is True or "security clearance required" in text:
        return "security_clearance"
    years_required = job.get("years_required")
    try:
        if years_required is not None and float(years_required) >= 5:
            return "experience_5_plus"
    except (TypeError, ValueError):
        pass
    if re.search(r"\b([5-9]|1\d)\+?\s+years?\b", text) and "preferred" not in text:
        return "experience_5_plus"
    seniority = infer_seniority(job)
    if seniority in {"senior", "staff", "principal", "lead", "director", "head"}:
        return "senior_role"
    if job.get("pure_frontend") is True:
        return "pure_frontend"
    if job.get("nontechnical_pm") is True:
        return "nontechnical_pm"
    if not canonicalize_url(clean_text(job.get("url"))):
        return "missing_url"
    return None


def score_job(job: dict, now: datetime) -> tuple[int, list[str]]:
    text = combined_text(job)
    lane = infer_lane(job)
    seniority = infer_seniority(job)
    score = 22
    signals: list[str] = []

    lane_points = {"ai_research": 27, "ai_engineering": 24, "quant_ml": 27}
    score += lane_points[lane]

    if seniority in {"internship", "graduate", "new_grad", "trainee"}:
        score += 18
    else:
        score += 8

    time_series_terms = (
        "time series", "time-series", "forecasting", "state space", "state-space",
        "sequential model", "neural sde", "stochastic", "probabilistic forecasting",
        "spatiotemporal", "anomaly detection", "signal processing",
    )
    if any(term in text for term in time_series_terms):
        score += 10
        signals.append("time series")

    quant_terms = ("quantitative", "trading", "finance", "asset management", "pricing", "market making")
    ml_terms = ("machine learning", "deep learning", "pytorch", "transformer", " llm", "artificial intelligence")
    if any(term in text for term in quant_terms) and any(term in text for term in ml_terms):
        score += 10
        signals.append("ML∩quant")
        job["ml_quant"] = True

    tech_groups = [
        (("pytorch",), 5, "PyTorch"),
        (("transformer", "hugging face", "foundation model", " llm"), 5, "foundation models"),
        (("cuda", " gpu", "distributed training", "training infrastructure"), 4, "GPU/distributed"),
        (("python",), 3, "Python"),
    ]
    for terms, points, label in tech_groups:
        if any(term in text for term in terms):
            score += points
            signals.append(label)

    location = f"{job.get('location', '')} {job.get('country', '')}".lower()
    if any(place in location for place in ("oslo", "amsterdam", "zurich", "zürich", "dublin", "london")):
        score += 4

    posted_at = parse_datetime(job.get("posted_at"))
    if posted_at:
        age = max(0, (now - posted_at).days)
        score += 5 if age <= 14 else 3 if age <= 28 else 0

    adjustment = job.get("manual_score_adjustment", 0)
    try:
        adjustment = max(-10, min(10, int(adjustment)))
    except (TypeError, ValueError):
        adjustment = 0
    score += adjustment
    return max(0, min(100, score)), signals[:5]


def load_ledger(path: Path, legacy_path: Path = DEFAULT_LEGACY) -> dict:
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("jobs"), dict):
                return data
        except (json.JSONDecodeError, OSError):
            pass
    jobs = {}
    if legacy_path.exists():
        try:
            legacy = json.loads(legacy_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            legacy = []
        if isinstance(legacy, list):
            for raw_url in legacy:
                fingerprint = canonicalize_url(str(raw_url))
                if fingerprint:
                    jobs[fingerprint] = {
                        "url": str(raw_url),
                        "status": "legacy_seen",
                        "first_seen": None,
                        "last_seen": None,
                    }
    return {"version": 2, "jobs": jobs}


def save_ledger(path: Path, ledger: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(ledger, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    temp.replace(path)


def prepare_candidates(payload: dict, ledger: dict, now: datetime) -> tuple[list[dict], list[dict]]:
    eligible: list[dict] = []
    processed: list[dict] = []
    for raw in payload.get("candidates", []):
        if not isinstance(raw, dict):
            continue
        job = dict(raw)
        job["url"] = canonicalize_url(clean_text(job.get("url")))
        job["country"] = clean_text(job.get("country") or "EU").upper()
        if job["country"] == "GB":
            job["country"] = "UK"
        job["lane"] = infer_lane(job)
        job["seniority"] = infer_seniority(job)
        fingerprint = job["url"]
        previous = ledger["jobs"].get(fingerprint)
        current_hash = content_hash(job)

        if previous and previous.get("status") in {"reported", "legacy_seen"} and previous.get("content_hash") in {None, current_hash}:
            continue

        rejection = hard_gate(job, now)
        if rejection:
            job["status"] = "rejected"
            job["rejection_reason"] = rejection
            job["content_hash"] = current_hash
            processed.append(job)
            continue

        score, signals = score_job(job, now)
        job["score"] = score
        job["signals"] = signals
        job["content_hash"] = current_hash
        job["status"] = "eligible_unreported"
        processed.append(job)
        if score >= int(payload.get("minimum_score", 55)):
            eligible.append(job)
    eligible.sort(key=lambda item: (-item["score"], item.get("deadline") or "9999"))
    return eligible, processed


def select_diverse(candidates: list[dict], limit: int = MAX_RESULTS) -> list[dict]:
    selected: list[dict] = []
    selected_urls: set[str] = set()
    country_counts: Counter[str] = Counter()
    employer_counts: Counter[str] = Counter()

    def can_add(job: dict) -> bool:
        employer = clean_text(job.get("company")).lower()
        return country_counts[job["country"]] < 3 and employer_counts[employer] < 2

    def add(job: dict) -> None:
        selected.append(job)
        selected_urls.add(job["url"])
        country_counts[job["country"]] += 1
        employer_counts[clean_text(job.get("company")).lower()] += 1

    for lane in ("ai_research", "ai_engineering", "quant_ml"):
        match = next((job for job in candidates if job["lane"] == lane and can_add(job)), None)
        if match:
            add(match)

    for job in candidates:
        if len(selected) >= limit:
            break
        if job["url"] not in selected_urls and can_add(job):
            add(job)

    selected.sort(key=lambda item: -item["score"])
    return selected


def seniority_label(value: str) -> str:
    value = value.lower()
    if "intern" in value or "student" in value:
        return "🧪 Internship"
    if value in {"graduate", "new_grad", "trainee", "entry level", "entry-level"}:
        return "🎓 Graduate"
    return "🌱 Junior"


def deadline_label(job: dict) -> str:
    deadline = parse_datetime(job.get("deadline"))
    if deadline:
        return f"Apply by {deadline.strftime('%-d %b')}"
    if job.get("rolling"):
        return "Rolling — open"
    posted = parse_datetime(job.get("posted_at"))
    if posted:
        return f"Posted {posted.strftime('%-d %b')} · deadline unknown"
    return "Deadline unknown"


def source_footer(payload: dict) -> str:
    sources = [source for source in payload.get("sources", []) if isinstance(source, dict)]
    countries: list[str] = []
    warnings = 0
    for source in sources:
        country = clean_text(source.get("country")).upper()
        if country and country not in countries:
            countries.append(country)
        if clean_text(source.get("status")).lower() in {"error", "blocked", "stale"}:
            warnings += 1
    flags = " ".join(COUNTRY_FLAGS.get(country, "🌍") for country in countries) or "🌍"
    suffix = f" · ⚠️ {warnings} source warning" if warnings == 1 else f" · ⚠️ {warnings} source warnings" if warnings else ""
    return f"🌍 Checked: {flags} · {len(sources)} sources{suffix}"


def validate_coverage(payload: dict) -> None:
    """Require explicit, independent attempts in every target market."""
    sources = [source for source in payload.get("sources", []) if isinstance(source, dict)]
    attempted = Counter()
    unique_ids: set[tuple[str, str]] = set()
    for source in sources:
        country = clean_text(source.get("country")).upper()
        source_id = clean_text(source.get("id"))
        if country == "GB":
            country = "UK"
        if country and source_id and (country, source_id) not in unique_ids:
            attempted[country] += 1
            unique_ids.add((country, source_id))
    requirements = {"NO": 1, "NL": 1, "CH": 2, "IE": 2, "UK": 2}
    missing = [f"{country} {attempted[country]}/{minimum}" for country, minimum in requirements.items() if attempted[country] < minimum]
    if missing:
        raise ValueError("insufficient source coverage: " + ", ".join(missing))


def render_digest(selected: list[dict], payload: dict, now: datetime) -> str:
    if not selected:
        return "💼 No new job matches this week.\n" + source_footer(payload)
    lane_counts = Counter(job["lane"] for job in selected)
    summary_bits = []
    for lane in ("ai_research", "ai_engineering", "quant_ml"):
        count = lane_counts.get(lane, 0)
        if count:
            summary_bits.append(f"{LANE_META[lane][0]} {count}")
    lines = [
        f"💼 JOB RADAR · {now.strftime('%-d %b').upper()}",
        f"{len(selected)} fresh matches · " + " · ".join(summary_bits),
        "",
    ]
    medals = ["🥇", "🥈", "🥉"]
    for index, job in enumerate(selected):
        lane_icon, lane_name = LANE_META[job["lane"]]
        prefix = medals[index] if index < len(medals) else f"{index + 1}."
        flag = COUNTRY_FLAGS.get(job["country"], "🌍")
        tags = list(job.get("signals", []))[:3]
        tag_line = " · ".join(tags) if tags else lane_name
        why = clean_text(job.get("why") or job.get("fit_reason") or f"Strong {lane_name} match for the target profile", 180)
        eligibility = clean_text(job.get("work_authorization"))
        language = clean_text(job.get("language_requirement"))
        caveats = ""
        if eligibility:
            caveats += f" · 🛂 {eligibility}"
        if language:
            caveats += f" · 🗣 {language}"
        lines.extend([
            f"{prefix} {lane_icon} {clean_text(job.get('title'), 100)}",
            f"🏢 {clean_text(job.get('company'), 55)} · 📍 {clean_text(job.get('location'), 70)} {flag}",
            f"{seniority_label(job['seniority'])} · 🎯 {job['score']}/100 · {tag_line}{caveats}",
            f"💡 {why}",
            f"⏳ {deadline_label(job)}",
            f"🔗 {job['url']}",
            "",
        ])
    lines.append(source_footer(payload))
    message = "\n".join(lines).strip()
    if len(message) > MAX_MESSAGE_CHARS:
        raise ValueError(f"rendered digest is {len(message)} chars; limit is {MAX_MESSAGE_CHARS}")
    return message


def validate_digest(message: str) -> None:
    errors = []
    if not message.startswith("💼"):
        errors.append("message must start with 💼")
    if "*" in message or "```" in message:
        errors.append("message contains forbidden Markdown")
    if len(message) > MAX_MESSAGE_CHARS:
        errors.append(f"message exceeds {MAX_MESSAGE_CHARS} characters")
    cards = sum(1 for line in message.splitlines() if line.startswith("🔗 "))
    match_count = re.search(r"^(\d+) fresh matches", message, re.MULTILINE)
    if match_count and cards != int(match_count.group(1)):
        errors.append(f"digest declares {match_count.group(1)} matches but contains {cards} links")
    if any(banned in message[:120].lower() for banned in ("now let me", "here is", "i found", "based on")):
        errors.append("message contains a reasoning preamble")
    if errors:
        raise ValueError("; ".join(errors))


def update_ledger(ledger: dict, processed: list[dict], selected: list[dict], now: datetime) -> None:
    selected_urls = {job["url"] for job in selected}
    timestamp = now.isoformat()
    for job in processed:
        fingerprint = job["url"]
        previous = ledger["jobs"].get(fingerprint, {})
        status = "reported" if fingerprint in selected_urls else job["status"]
        ledger["jobs"][fingerprint] = {
            "url": fingerprint,
            "title": clean_text(job.get("title")),
            "company": clean_text(job.get("company")),
            "country": job.get("country"),
            "lane": job.get("lane"),
            "score": job.get("score"),
            "status": status,
            "rejection_reason": job.get("rejection_reason"),
            "content_hash": job.get("content_hash"),
            "first_seen": previous.get("first_seen") or timestamp,
            "last_seen": timestamp,
            "reported_at": timestamp if status == "reported" else previous.get("reported_at"),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", type=Path, help="JSON candidate payload")
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--legacy", type=Path, default=DEFAULT_LEGACY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--source-health", type=Path, default=DEFAULT_SOURCE_HEALTH)
    parser.add_argument("--commit", action="store_true", help="persist ledger updates")
    parser.add_argument("--migrate-legacy", action="store_true", help="create v2 ledger from legacy seen state")
    parser.add_argument("--validate-only", type=Path, help="validate an existing digest")
    args = parser.parse_args()

    if args.validate_only:
        validate_digest(args.validate_only.read_text(encoding="utf-8"))
        print("digest valid")
        return 0

    ledger = load_ledger(args.ledger, args.legacy)
    if args.migrate_legacy:
        save_ledger(args.ledger, ledger)
        print(f"migrated {len(ledger['jobs'])} legacy fingerprints to {args.ledger}")
        return 0
    if not args.input:
        parser.error("input is required unless --migrate-legacy or --validate-only is used")

    payload = json.loads(args.input.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("candidates", []), list):
        raise ValueError("input must be an object with a candidates array")
    now = parse_datetime(payload.get("generated_at")) or datetime.now(timezone.utc)
    validate_coverage(payload)
    eligible, processed = prepare_candidates(payload, ledger, now)
    selected = select_diverse(eligible, min(MAX_RESULTS, int(payload.get("max_results", MAX_RESULTS))))
    while True:
        try:
            message = render_digest(selected, payload, now)
            break
        except ValueError as exc:
            if "chars; limit" not in str(exc) or len(selected) <= 1:
                raise
            selected.pop()
    validate_digest(message)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(message + "\n", encoding="utf-8")
    if args.commit:
        update_ledger(ledger, processed, selected, now)
        save_ledger(args.ledger, ledger)
        args.source_health.parent.mkdir(parents=True, exist_ok=True)
        args.source_health.write_text(
            json.dumps({"generated_at": now.isoformat(), "sources": payload.get("sources", [])}, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    print(message)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, json.JSONDecodeError, OSError) as exc:
        print(f"job pipeline failed: {exc}", file=sys.stderr)
        raise SystemExit(2)
