#!/usr/bin/env python3
"""Apply a small, checked, reproducible patch to Agent-Reach's private OpenCLI.

No login data or browser profiles are changed. Rerun after upstream tool updates.
"""
import argparse
from pathlib import Path
import subprocess
import sys

BASE = Path(__file__).resolve().parent
MARKER = '// job-crawler modern LinkedIn layout compatibility'
ANCHOR = '    const inline = parseInlineJobData();'


def patched_source(source):
    if MARKER in source:
        return source
    if source.count(ANCHOR) != 1:
        raise ValueError('Unrecognized upstream adapter; inspect it before applying this patch')
    return ("import { extractModernJob } from './job-crawler-detail.js';\n" + source).replace(
        '  return String.raw`(() => {',
        '  return String.raw`(() => {\n    const modern = (${extractModernJob.toString()})(document, location.href);\n    if (modern) return modern;', 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--opencli-root', type=Path, default=Path.home()/'.agent-reach/tools/npm-global/lib/node_modules/@jackwener/opencli')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    adapter = args.opencli_root/'clis/linkedin/job-detail.js'
    source = adapter.read_text()
    if "import { extractModernJob }" in source:
        if args.check:
            module = adapter.parent/'job-crawler-detail.js'
            if not module.exists() or module.read_text() != (BASE/'compat/linkedin_detail.js').read_text():
                raise ValueError('LinkedIn layout compatibility module is missing or outdated; reapply patch')
            print('LinkedIn layout compatibility installed')
            return
        if not (adapter.parent/'job-crawler-detail.js').exists():
            raise ValueError('Installed adapter references a missing compatibility module')
    elif args.check:
        raise ValueError('LinkedIn layout compatibility is not installed')
    else:
        updated = patched_source(source)
        if updated == source or 'const modern =' not in updated:
            raise ValueError('Upstream extraction entry point changed; patch not applied')
        backup = adapter.with_suffix('.js.job-crawler-original')
        if not backup.exists():
            backup.write_text(source)
        temp = adapter.with_name('job-detail.job-crawler-tmp.mjs')
        temp.write_text(updated + '\n' + MARKER + '\n')
        subprocess.run(['node','--check',str(temp)], check=True, capture_output=True)
        # Install module first so the adapter never references a missing file.
        (adapter.parent/'job-crawler-detail.js').write_text((BASE/'compat/linkedin_detail.js').read_text())
        temp.replace(adapter)
    (adapter.parent/'job-crawler-detail.js').write_text((BASE/'compat/linkedin_detail.js').read_text())
    print('LinkedIn layout compatibility installed; original adapter retained beside it')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f'LinkedIn compatibility setup failed: {exc}',file=sys.stderr)
        raise SystemExit(1)
