#!/usr/bin/env python3
"""Preview/install the LinkedIn prefetch cron entry after live acceptance."""
import argparse
import json
from pathlib import Path
import shlex
import shutil
import subprocess

from fetch_linkedin import fresh_staging

BASE = Path(__file__).resolve().parents[1]
MARKER = '# job-crawler-linkedin-prefetch'


def cron_text(existing, repo=BASE, uv=None):
    uv = uv or shutil.which('uv')
    if not uv:
        raise ValueError('uv is not on PATH')
    # cron treats percent specially, including inside shell quotes.
    if '%' in str(repo) or '%' in uv:
        raise ValueError('cron paths must not contain percent signs')
    line = ('35 7 * * 1 cd ' + shlex.quote(str(repo)) + ' && ' + shlex.quote(uv)
            + ' run --locked python scripts/fetch_linkedin.py >> '
            + shlex.quote(str(repo / 'state/fetch_linkedin.log')) + ' 2>&1 ' + MARKER)
    lines = [s for s in existing.splitlines() if MARKER not in s]
    return '\n'.join([*lines, line]) + '\n'


def accepted(data):
    return (fresh_staging(data) and not data.get('errors') and any(a.get('action') == 'jobs' and a.get('status') == 'ok'
                                      for a in data.get('attempts', []))
            and any(j.get('detail_status') == 'fetched' and j.get('description')
                    for j in data.get('candidates', [])))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install', action='store_true')
    parser.add_argument('--acceptance-file', type=Path, default=BASE / 'state/linkedin_candidates.json')
    args = parser.parse_args()
    current = subprocess.run(['crontab','-l'], capture_output=True, text=True)
    if current.returncode and 'no crontab' not in current.stderr.lower():
        parser.error('could not read crontab')
    updated = cron_text(current.stdout)
    if not args.install:
        print(updated, end='')
        return
    tz = subprocess.check_output(['timedatectl','show','-p','Timezone','--value'], text=True).strip()
    if tz != 'Europe/Oslo':
        parser.error('host timezone must be Europe/Oslo before installing this schedule')
    if not args.acceptance_file.exists() or not accepted(json.loads(args.acceptance_file.read_text())):
        parser.error('first run an authenticated collector smoke test with a successful search and full detail read')
    subprocess.run(['crontab','-'], input=updated, text=True, check=True)
    print('LinkedIn prefetch scheduled: Monday 07:35 Europe/Oslo')


if __name__ == '__main__':
    main()
