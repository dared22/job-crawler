import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import fetch_linkedin as collector
import job_pipeline as pipeline

FIXTURE = json.loads((Path(__file__).parent / 'fixtures/linkedin_reach.json').read_text())
NOW = datetime(2026, 11, 17, tzinfo=timezone.utc)


class CollectorTests(unittest.TestCase):
    def config(self):
        return {'search_budget_seconds':450, 'results_per_query':5, 'max_details':30,
                'countries':{'NO':'Norway'}, 'queries':[{'id':'time_series', 'query':'forecasting intern'}]}

    def run_collect(self, responses, config=None):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'leads.json'
            with patch.object(collector, 'call_reach', side_effect=responses), patch.object(pipeline, 'load_ledger', return_value={'jobs':{}}):
                report = collector.collect(config or self.config(), output, 900, executable='test-reach')
            self.assertEqual(report, json.loads(output.read_text()))
            return report

    def test_real_field_mapping_and_stable_detail_id(self):
        report = self.run_collect([FIXTURE['search']['items'], FIXTURE['detail']['items']])
        lead = report['candidates'][0]
        self.assertEqual(lead['url'], 'https://linkedin.com/jobs/view/123')
        self.assertEqual(lead['company'], 'Cognite')
        self.assertEqual(lead['posted_at'], '2026-11-16')
        self.assertFalse(lead['evidence_verified'])
        self.assertNotIn('compensation', lead)
        self.assertNotIn('open', lead)
        self.assertEqual(report['status'], 'complete')

    def test_queries_share_one_source_and_one_detail_read(self):
        config = self.config()
        config['queries'] *= 2
        report = self.run_collect([FIXTURE['search']['items'], FIXTURE['search']['items'], FIXTURE['detail']['items']], config)
        self.assertEqual(len(report['candidates']), 1)
        self.assertEqual(len(report['sources']), 1)
        self.assertEqual(len(report['attempts']), 3)

    def test_login_rate_limit_and_setup_stop_and_replace_old_output(self):
        for code in ['NEED_LOGIN','PLATFORM_BLOCKED','RATE_LIMITED','NEED_SETUP','TIMEOUT','UPSTREAM_BROKEN']:
            with self.subTest(code=code):
                report = self.run_collect([collector.ReachFailure(code)])
                self.assertTrue(report['partial'])
                self.assertEqual(len(report['attempts']), 1)
                self.assertEqual(report['candidates'], [])
                self.assertEqual(report['errors'][0]['code'], code)

    def test_empty_search_not_a_failure(self):
        report = self.run_collect([collector.ReachFailure('NOT_FOUND')])
        self.assertEqual(report['status'], 'complete')
        self.assertEqual(report['sources'][0]['status'], 'nothing_new')

    def test_detail_failure_keeps_lead(self):
        report = self.run_collect([FIXTURE['search']['items'], collector.ReachFailure('NEED_LOGIN')])
        self.assertEqual(report['candidates'][0]['detail_status'], 'error')
        self.assertEqual(report['sources'][0]['status'], 'blocked')

    def test_incomplete_description_is_not_verified(self):
        report = self.run_collect([FIXTURE['search']['items'], [{'raw':{}}]])
        self.assertEqual(report['candidates'][0]['detail_status'], 'incomplete')
        self.assertFalse(report['candidates'][0]['evidence_verified'])

    def test_relative_date_not_guessed(self):
        item = copy.deepcopy(FIXTURE['search']['items'][0])
        item['raw']['listed'] = '2 weeks ago'
        lead = collector.lead_from_item(item, 'NO', 'research')
        self.assertIsNone(lead['posted_at'])
        self.assertEqual(lead['listed_text'], '2 weeks ago')

    def test_host_and_job_path_validation(self):
        self.assertIsNone(collector.job_url('https://[malformed/jobs/view/123'))
        self.assertIsNone(collector.job_url('https://evil-linkedin.com/jobs/view/123'))
        self.assertIsNone(collector.job_url('https://linkedin.com/jobs/view/123/extra'))
        self.assertEqual(collector.job_url('https://no.linkedin.com/jobs/view/title-123'), 'https://linkedin.com/jobs/view/123')

    def test_deadline_stops_without_inventing_attempts(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(collector.time, 'monotonic', side_effect=[0, 500]), patch.object(pipeline, 'load_ledger', return_value={'jobs':{}}):
            report = collector.collect(self.config(), Path(tmp)/'out.json', 900)
        self.assertEqual(report['attempts'], [])
        self.assertEqual(report['sources'], [])
        self.assertTrue(report['partial'])

    def test_freshness_rejects_stale_future_running_and_unknown_schema(self):
        data = {'schema_version':1, 'status':'partial','fetched_at':NOW.isoformat()}
        self.assertTrue(collector.fresh_staging(data, NOW))
        for patch_data in [{'fetched_at':(NOW-timedelta(days=2)).isoformat()}, {'fetched_at':(NOW+timedelta(seconds=1)).isoformat()}, {'status':'running'}, {'schema_version':2}]:
            self.assertFalse(collector.fresh_staging(dict(data, **patch_data), NOW))

    def test_json_errors_invalid_json_and_timeout(self):
        for data, code in [({'schema_version':1,'ok':False,'error':{'code':'NEED_LOGIN'}}, 'NEED_LOGIN'), ({'schema_version':2,'ok':True,'items':[]}, 'UPSTREAM_BROKEN'), ({'schema_version':1,'ok':True,'items':None}, 'UPSTREAM_BROKEN')]:
            with patch.object(collector.subprocess, 'run', return_value=subprocess.CompletedProcess([],0,json.dumps(data),'')):
                with self.assertRaises(collector.ReachFailure) as ctx:
                    collector.call_reach('reach', ['jobs','test'], collector.time.monotonic()+30)
                self.assertEqual(ctx.exception.code, code)
        for effect in [subprocess.TimeoutExpired('reach',1), FileNotFoundError()]:
            with patch.object(collector.subprocess,'run',side_effect=effect):
                with self.assertRaises(collector.ReachFailure):
                    collector.call_reach('reach',['jobs','test'],collector.time.monotonic()+30)


class AliasTests(unittest.TestCase):
    def job(self, **kw):
        return dict({'url':'https://example.com/jobs/1','title':'Research Engineer Intern', 'company':'Cognite',
                     'country':'NO','description':'Python PyTorch time series MSc internship', 'open':True}, **kw)

    def test_same_job_prefers_employer_and_persists_alias(self):
        linkedin = 'https://no.linkedin.com/jobs/view/title-123?trk=test'
        payload = {'candidates':[self.job(url=linkedin), self.job(alternate_urls=[linkedin])]}
        ledger = {'version':2, 'jobs':{}}
        eligible, processed = pipeline.prepare_candidates(payload, ledger, NOW)
        self.assertEqual(len(eligible), 1)
        self.assertEqual(eligible[0]['url'], 'https://example.com/jobs/1')
        pipeline.update_ledger(ledger, processed, eligible, NOW)
        eligible2, _ = pipeline.prepare_candidates({'candidates':[self.job(url=linkedin)]}, ledger, NOW)
        self.assertEqual(eligible2, [])
        self.assertEqual(len(ledger['jobs']), 1)

    def test_suppression_learns_alias_and_preserves_timestamp(self):
        job = self.job()
        ledger = {'version':2,'jobs':{job['url']:{'url':job['url'],'status':'reported','content_hash':pipeline.content_hash(job), 'reported_at':'2026-11-01T00:00:00+00:00', 'first_seen':'2026-10-01T00:00:00+00:00'}}}
        eligible, processed = pipeline.prepare_candidates({'candidates':[self.job(alternate_urls=['https://linkedin.com/jobs/view/1'])]},ledger,NOW)
        self.assertEqual(eligible, [])
        pipeline.update_ledger(ledger,processed,eligible,NOW)
        self.assertEqual(ledger['jobs'][job['url']]['reported_at'], '2026-11-01T00:00:00+00:00')
        self.assertEqual(ledger['jobs'][job['url']]['alternate_urls'], ['https://linkedin.com/jobs/view/1'])

    def test_changed_posting_reconsidered(self):
        job = self.job()
        ledger = {'jobs':{job['url']:{'status':'reported','content_hash':pipeline.content_hash(job)}}}
        eligible, _ = pipeline.prepare_candidates({'candidates':[self.job(description='New PyTorch forecasting MSc internship requirements')]},ledger,NOW)
        self.assertEqual(len(eligible),1)

    def test_different_jobs_not_merged_by_title(self):
        eligible, _ = pipeline.prepare_candidates({'candidates':[self.job(), self.job(url='https://example.com/jobs/2')]},{'jobs':{}},NOW)
        self.assertEqual(len(eligible),2)

    def test_legacy_record_and_alias_are_suppressed(self):
        ledger = {'jobs':{'https://linkedin.com/jobs/view/1':{'status':'legacy_seen'}}}
        eligible, processed = pipeline.prepare_candidates({'candidates':[self.job(alternate_urls=['https://linkedin.com/jobs/view/1'])]},ledger,NOW)
        self.assertEqual(eligible,[])
        pipeline.update_ledger(ledger,processed,[],NOW)
        self.assertEqual(len(ledger['jobs']),1)

    def test_unreviewed_lead_cannot_be_reported(self):
        eligible, processed = pipeline.prepare_candidates({'candidates':[self.job(evidence_verified=False)]},{'jobs':{}},NOW)
        self.assertEqual(eligible,[])
        self.assertEqual(processed[0]['rejection_reason'],'unverified_evidence')


class SchedulingAndEndToEndTests(unittest.TestCase):
    def test_cron_is_idempotent_and_preserves_bindeleddet(self):
        import schedule_linkedin
        old = '55 7 * * 1 /usr/bin/python3 fetch_bindeleddet.py\n'
        first = schedule_linkedin.cron_text(old, uv='/home/test/.local/bin/uv')
        self.assertTrue(first.startswith(old))
        self.assertEqual(first, schedule_linkedin.cron_text(first, uv='/home/test/.local/bin/uv'))
        self.assertEqual(first.count(schedule_linkedin.MARKER), 1)

    def test_schedule_requires_fresh_successful_search_and_details(self):
        import schedule_linkedin
        data = {'schema_version':1, 'status':'complete', 'fetched_at':datetime.now(timezone.utc).isoformat(),
                'attempts':[{'action':'jobs','status':'ok'}], 'candidates':[{'detail_status':'fetched','description':'Full JD'}]}
        self.assertTrue(schedule_linkedin.accepted(data))
        self.assertFalse(schedule_linkedin.accepted(dict(data, candidates=[])))
        self.assertFalse(schedule_linkedin.accepted(dict(data, attempts=[])))
        self.assertFalse(schedule_linkedin.accepted(dict(data, fetched_at='2020-01-01')))

    def test_reviewed_sample_pipeline_with_only_temporary_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidate = collector.lead_from_item(FIXTURE['search']['items'][0], 'NO', 'time_series')
            candidate.update(description=FIXTURE['detail']['items'][0]['text'], country='NO',
                             evidence_verified=True, open=True, seniority='internship',
                             lane='ai_research', why='Time-series research with Python and PyTorch')
            payload = {'generated_at':NOW.isoformat(), 'candidates':[candidate],
                       'sources':[{'id':f'board-{n}', 'country':c, 'status':'ok'}
                                  for c in ['NO','IE','NL','CH','UK'] for n in range(2)]}
            source = root/'input.json'
            source.write_text(json.dumps(payload))
            cmd = [sys.executable, str(collector.BASE/'scripts/job_pipeline.py'), str(source), '--commit',
                   '--ledger',str(root/'ledger.json'),'--legacy',str(root/'legacy.json'),
                   '--output',str(root/'digest.txt'),'--source-health',str(root/'health.json')]
            result = subprocess.run(cmd,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            ledger = json.loads((root/'ledger.json').read_text())
            self.assertEqual(ledger['jobs'][candidate['url']]['status'],'reported')
            pipeline.validate_digest((root/'digest.txt').read_text())
            self.assertIn('Research Engineer Intern',(root/'digest.txt').read_text())


class CollectionLimitsTests(unittest.TestCase):
    def test_primary_searches_first_and_max_detail_limit(self):
        config = {'search_budget_seconds':450, 'results_per_query':5, 'max_details':1,
                  'countries':{'UK':'United Kingdom', 'NO':'Norway'},
                  'queries':[{'id':'research','query':'research intern'}]}
        def response(executable, args, deadline):
            if args[0] == 'read':
                return FIXTURE['detail']['items']
            item = copy.deepcopy(FIXTURE['search']['items'][0])
            if args[args.index('--location')+1] == 'United Kingdom':
                item['url'] = 'https://linkedin.com/jobs/view/456'
            return [item]
        with tempfile.TemporaryDirectory() as tmp, patch.object(collector,'call_reach',side_effect=response), patch.object(pipeline,'load_ledger',return_value={'jobs':{}}):
            report = collector.collect(config,Path(tmp)/'leads.json',900,executable='test-reach')
        self.assertEqual([a['country'] for a in report['attempts'] if a['action']=='jobs'],['NO','UK'])
        self.assertEqual(sum(a['action']=='read' for a in report['attempts']),1)
        self.assertTrue(report['partial'])
        self.assertEqual(report['candidates'][1]['detail_status'],'pending')

    def test_malformed_stdout_is_a_structured_failure(self):
        with patch.object(collector.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'not JSON','')):
            with self.assertRaises(collector.ReachFailure) as ctx:
                collector.call_reach('reach',['jobs','intern'],collector.time.monotonic()+30)
        self.assertEqual(ctx.exception.code,'UPSTREAM_BROKEN')

    def test_merging_existing_records_preserves_earliest_first_seen(self):
        direct = 'https://example.com/jobs/1'
        linkedin = 'https://linkedin.com/jobs/view/1'
        job = AliasTests().job(alternate_urls=[linkedin])
        ledger = {'jobs':{
            direct:{'status':'reported', 'content_hash':pipeline.content_hash(job),'first_seen':'2026-11-01T00:00:00Z','reported_at':'2026-11-02T00:00:00Z'},
            linkedin:{'status':'eligible_unreported','first_seen':'2026-10-01T00:00:00Z'}}}
        eligible, processed = pipeline.prepare_candidates({'candidates':[job]},ledger,NOW)
        pipeline.update_ledger(ledger,processed,eligible,NOW)
        self.assertEqual(list(ledger['jobs']),[direct])
        self.assertEqual(ledger['jobs'][direct]['first_seen'],'2026-10-01T00:00:00Z')
        self.assertEqual(ledger['jobs'][direct]['reported_at'],'2026-11-02T00:00:00Z')
