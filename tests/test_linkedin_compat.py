"""Regression checks for the live-observed LinkedIn layout change."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('linkedin_patch', ROOT/'scripts/patch_linkedin_adapter.py')
patcher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(patcher)


class CompatibilityTests(unittest.TestCase):
    def test_unknown_adapter_is_not_modified(self):
        with self.assertRaises(ValueError):
            patcher.patched_source('a different upstream implementation')

    def test_patch_is_checked_and_idempotent(self):
        original = "function buildExtractionScript() {\n  return String.raw`(() => {\n    const inline = parseInlineJobData();\n  })()`;\n}\n"
        patched = patcher.patched_source(original) + '\n' + patcher.MARKER
        self.assertIn('extractModernJob.toString()', patched)
        self.assertIn('const inline = parseInlineJobData()',patched)
        self.assertEqual(patcher.patched_source(patched),patched)

    def test_new_layout_scopes_full_description_and_rejects_wrong_pages(self):
        module = (ROOT/'scripts/compat/linkedin_detail.js').as_uri()
        script = '''
import {extractModernJob} from MODULE;
const text = 'Build forecasting models with Python and PyTorch. MSc students are welcome. '.repeat(8);
const box={textContent:text,innerText:text.slice(0,50)};
const card={tagName:'DIV',querySelector:s=>s.includes('expandable-text-box')?box:null};
const parent={tagName:'DIV',parentElement:card,querySelector:()=>null};
const heading={textContent:'About the job',parentElement:parent};
const doc={title:'Research Engineer Intern | Example AI | LinkedIn',querySelectorAll:()=>[heading]};
const read=url=>extractModernJob(doc,url);
const job=read('https://www.linkedin.com/jobs/search-results/?currentJobId=123&keywords=jobs');
if(job.description.trim()!==text.trim() || job.title!=='Research Engineer Intern' || job.company!=='Example AI') throw Error('lost full job evidence');
if(job.url!=='https://www.linkedin.com/jobs/view/123') throw Error('lost identity');
doc.title='Data Scientist | Remote | Crossing Hurdles | LinkedIn';
const piped=read('https://www.linkedin.com/jobs/view/123');
if(piped.title!=='Data Scientist | Remote' || piped.company!=='Crossing Hurdles') throw Error('split title at wrong separator');
if(read('https://www.linkedin.com/feed/')) throw Error('accepted feed');
if(read('https://evil-linkedin.com/jobs/view/123')) throw Error('accepted foreign host');
if(read('https://www.linkedin.com/jobs/search/?keywords=jobs')) throw Error('accepted unspecified job');
// No h1 is needed. A missing new-layout box returns null so the old extractor runs.
card.querySelector=()=>null;
card.parentElement={tagName:'BODY',querySelector:()=>({textContent:'unrelated page content'.repeat(100)})};
if(read('https://www.linkedin.com/jobs/view/123')) throw Error('read unrelated body content');
console.log('modern layout regression checks passed');
'''.replace('MODULE',json.dumps(module))
        result = subprocess.run(['node','--input-type=module','-e',script],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_install_check_and_reinstall_retain_original(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            folder=root/'clis/linkedin'
            folder.mkdir(parents=True)
            source="function buildExtractionScript() {\n  return String.raw`(() => {\n    const inline = parseInlineJobData();\n  })()`;\n}\n"
            (folder/'job-detail.js').write_text(source)
            command=['python3',str(ROOT/'scripts/patch_linkedin_adapter.py'),'--opencli-root',str(root)]
            for args in [[],['--check'],[]]:
                result=subprocess.run(command+args,capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual((folder/'job-detail.js.job-crawler-original').read_text(),source)


class EmptySearchRegressionTests(unittest.TestCase):
    def test_only_known_empty_search_error_becomes_not_found(self):
        import sys
        from unittest.mock import patch
        sys.path.insert(0,str(ROOT/'scripts'))
        import fetch_linkedin as collector
        import time
        envelope={'schema_version':1,'ok':False,'items':[], 'error':{'code':'UPSTREAM_BROKEN','message':'OpenCLI finished but returned no items'}}
        for action, expected in [('jobs','NOT_FOUND'),('read','UPSTREAM_BROKEN')]:
            with patch.object(collector.subprocess,'run',return_value=subprocess.CompletedProcess([],1,json.dumps(envelope),'')):
                with self.assertRaises(collector.ReachFailure) as ctx:
                    collector.call_reach('reach',[action,'test'],time.monotonic()+30)
                self.assertEqual(ctx.exception.code,expected)
