#!/usr/bin/env python3
"""Bounded Agent-Reach collection. Output is unverified leads, never pipeline input."""
from __future__ import annotations

import argparse
from collections import defaultdict, deque
from datetime import datetime, timezone
import fcntl
import json
import math
from pathlib import Path
import shutil
import subprocess
import time
from urllib.parse import urlsplit
import re

import job_pipeline as pipeline

BASE = Path(__file__).resolve().parents[1]
STOP_CODES = {'NEED_SETUP', 'NEED_LOGIN', 'PLATFORM_BLOCKED', 'RATE_LIMITED', 'BUSY', 'TIMEOUT', 'UPSTREAM_BROKEN'}


class ReachFailure(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def call_reach(executable, args, deadline):
    remaining = deadline - time.monotonic()
    if remaining <= 1:
        raise ReachFailure('BUDGET_EXHAUSTED')
    timeout = min(60, remaining - 0.5)
    try:
        result = subprocess.run(
            [executable, 'linkedin', *args, '--backend', 'opencli', '--timeout', str(timeout)],
            capture_output=True, text=True, timeout=remaining if remaining < 65 else 65,
        )
        data = json.loads(result.stdout)
    except FileNotFoundError:
        raise ReachFailure('NEED_SETUP') from None
    except subprocess.TimeoutExpired:
        raise ReachFailure('TIMEOUT') from None
    except (ValueError, OSError):
        raise ReachFailure('UPSTREAM_BROKEN') from None
    if not isinstance(data, dict) or data.get('schema_version') != 1 or type(data.get('ok')) is not bool:
        raise ReachFailure('UPSTREAM_BROKEN')
    if not data['ok']:
        error = data.get('error')
        code = error.get('code') if isinstance(error, dict) else None
        # Agent-Reach 1.6.1 mislabels a successful empty OpenCLI search as broken.
        if (args[0] == 'jobs' and code == 'UPSTREAM_BROKEN'
                and error.get('message') == 'OpenCLI finished but returned no items'):
            raise ReachFailure('NOT_FOUND')
        # Do not persist arbitrary upstream messages, stdout, or browser credentials.
        raise ReachFailure(code if code in STOP_CODES | {'NOT_FOUND', 'BAD_INPUT'} else 'UPSTREAM_BROKEN')
    if result.returncode or not isinstance(data.get('items'), list):
        raise ReachFailure('UPSTREAM_BROKEN')
    return [item for item in data['items'] if isinstance(item, dict)]


def job_url(value):
    if not isinstance(value, str):
        return None
    try:
        parts = urlsplit(value)
        host = parts.hostname or ''
    except ValueError:
        return None
    if parts.scheme != 'https' or not (host == 'linkedin.com' or host.endswith('.linkedin.com')):
        return None
    match = re.fullmatch(r'/jobs/view/(?:[^/]+-)?([0-9]+)/?', parts.path)
    return f'https://linkedin.com/jobs/view/{match[1]}' if match else None


def lead_from_item(item, country, family):
    raw = item.get('raw') if isinstance(item.get('raw'), dict) else {}
    url = job_url(item.get('url') or raw.get('url'))
    if not url:
        return None
    listed = raw.get('listed') or item.get('published_at')
    return {
        'linkedin_id': url.rsplit('/', 1)[-1], 'url': url,
        'title': raw.get('title') or item.get('title'), 'company': raw.get('company'),
        'location': raw.get('location'), 'query_country': country,
        'query_families': [family], 'listed_text': listed,
        'posted_at': listed if isinstance(listed, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', listed) else None,
        'salary_text': raw.get('salary'), 'description': '', 'detail_status': 'pending',
        'evidence_verified': False,
    }


def detail_order(leads, ledger):
    known = {url for key, record in ledger.get('jobs', {}).items()
             for url in pipeline.record_urls(dict(record, url=key))}
    buckets = defaultdict(deque)
    ranked = sorted(leads, key=lambda j: (j['url'] in known, not pipeline.priority_employer(j), int(j['linkedin_id'])))
    for lead in ranked:
        buckets[(lead['query_country'], lead['query_families'][0])].append(lead)
    order = []
    for primary in (True, False):
        keys = sorted(k for k in buckets if (k[0] in pipeline.PRIMARY_COUNTRIES) == primary)
        while any(buckets[k] for k in keys):
            for key in keys:
                if buckets[key]:
                    order.append(buckets[key].popleft())
    return order


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    temp.replace(path)


def collect(config, output, budget, *, executable=None):
    start = time.monotonic()
    deadline = start + budget
    search_deadline = start + min(config['search_budget_seconds'], budget / 2)
    executable = executable or shutil.which('agent-reach') or str(Path.home() / '.local/bin/agent-reach')
    report = {'schema_version': 1, 'fetched_at': datetime.now(timezone.utc).isoformat(),
              'completed_at': None, 'status': 'running', 'partial': True,
              'attempts': [], 'sources': [], 'candidates': [], 'errors': []}
    leads = {}
    source_map = {}
    stopped = False
    countries = config['countries']
    primary = [c for c in countries if c in pipeline.PRIMARY_COUNTRIES]
    secondary = [c for c in countries if c not in pipeline.PRIMARY_COUNTRIES]
    queries = [(c, family) for group in (primary, secondary)
               for family in config['queries'] for c in group]

    def checkpoint():
        report['candidates'] = list(leads.values())
        report['sources'] = list(source_map.values())
        atomic_write(output, report)

    checkpoint()  # A fresh failure must not look like last week's successful data.
    for country, family in queries:
        if time.monotonic() >= search_deadline - 1:
            break
        source = source_map.setdefault(country, {'id': f'linkedin_{country.lower()}', 'country': country,
                                                 'status': 'nothing_new', 'new_count': 0})
        variants = family.get('query_variants') or [family['query']]
        week = datetime.now(timezone.utc).date().isocalendar().week
        query = variants[(week - 1) % len(variants)]
        attempt = {'country': country, 'family': family['id'], 'action': 'jobs', 'query': query}
        report['attempts'].append(attempt)
        try:
            items = call_reach(executable, ['jobs', query, '--location', countries[country],
                                           '--limit', str(config['results_per_query'])], search_deadline)
            attempt['status'] = 'ok' if items else 'nothing_new'
            for item in items:
                lead = lead_from_item(item, country, family['id'])
                if lead and lead['url'] not in leads:
                    leads[lead['url']] = lead
                    source['new_count'] += 1
                elif lead:
                    old = leads[lead['url']]
                    old['query_families'] = sorted(set(old['query_families'] + lead['query_families']))
            if source['new_count'] and source['status'] not in {'error', 'blocked'}:
                source['status'] = 'ok'
        except ReachFailure as exc:
            attempt['status'] = 'nothing_new' if exc.code == 'NOT_FOUND' else 'error'
            if exc.code != 'NOT_FOUND':
                source['status'] = 'blocked' if exc.code in {'NEED_LOGIN', 'PLATFORM_BLOCKED', 'RATE_LIMITED'} else 'error'
                attempt['error_code'] = exc.code
                report['errors'].append({'code': exc.code, 'country': country})
                stopped = exc.code in STOP_CODES
        checkpoint()
        if stopped:
            break
    searched_all = sum(a['action'] == 'jobs' for a in report['attempts']) == len(queries)
    ledger = pipeline.load_ledger(pipeline.DEFAULT_LEDGER)
    if not stopped:
        for lead in detail_order(list(leads.values()), ledger)[:config['max_details']]:
            if time.monotonic() >= deadline - 1:
                break
            attempt = {'country': lead['query_country'], 'action': 'read', 'url': lead['url']}
            report['attempts'].append(attempt)
            try:
                items = call_reach(executable, ['read', lead['url']], deadline)
                raw = items[0].get('raw') if items else None
                raw = raw if isinstance(raw, dict) else {}
                description = raw.get('description') or (items[0].get('text') if items else '')
                lead['description'] = description or ''
                lead['detail_status'] = 'fetched' if description else 'incomplete'
                # Keep the original search URL even when detail returns /jobs/search/.
                for key in ('company', 'location', 'workplace_type', 'job_type', 'apply_url', 'company_url'):
                    if raw.get(key):
                        lead[key] = raw[key]
                attempt['status'] = lead['detail_status']
            except ReachFailure as exc:
                lead['detail_status'] = 'unavailable' if exc.code == 'NOT_FOUND' else 'error'
                attempt.update(status=lead['detail_status'], error_code=exc.code)
                if exc.code != 'NOT_FOUND':
                    report['errors'].append({'code': exc.code, 'country': lead['query_country']})
                    source_map[lead['query_country']]['status'] = 'blocked' if exc.code in {'NEED_LOGIN', 'PLATFORM_BLOCKED', 'RATE_LIMITED'} else 'error'
                stopped = exc.code in STOP_CODES
            checkpoint()
            if stopped:
                break
    report['partial'] = not searched_all or bool(report['errors']) or any(j['detail_status'] in {'pending', 'incomplete', 'error'} for j in leads.values())
    report['status'] = 'partial' if report['partial'] else 'complete'
    report['completed_at'] = datetime.now(timezone.utc).isoformat()
    if not searched_all and not report['errors']:
        report['errors'].append({'code': 'SEARCH_BUDGET_EXHAUSTED'})
    checkpoint()
    return report


def fresh_staging(data, now=None):
    """A partial run may contain usable leads, but never counts as verified evidence."""
    now = now or datetime.now(timezone.utc)
    stamp = pipeline.parse_datetime(data.get('fetched_at'))
    return (data.get('schema_version') == 1 and data.get('status') in {'complete', 'partial'}
            and stamp is not None and 0 <= (now - stamp).total_seconds() <= 86400)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registry', type=Path, default=BASE / 'source_registry.json')
    parser.add_argument('--output', type=Path, default=BASE / 'state/linkedin_candidates.json')
    parser.add_argument('--budget-seconds', type=float)
    args = parser.parse_args()
    config = json.loads(args.registry.read_text())['linkedin']
    budget = args.budget_seconds if args.budget_seconds is not None else config['budget_seconds']
    if not math.isfinite(budget) or budget <= 0:
        parser.error('budget must be finite and positive')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.with_suffix('.lock').open('w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('linkedin: another collector owns this output')
            return 1
        report = collect(config, args.output, budget)
    print(f"linkedin: {report['status']}, {len(report['candidates'])} unverified leads, {len(report['errors'])} errors")
    return 0 if not report['errors'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
