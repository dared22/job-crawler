import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "job_pipeline.py"
SPEC = importlib.util.spec_from_file_location("job_pipeline", MODULE_PATH)
pipeline = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pipeline)


NOW = datetime(2026, 9, 19, 12, 0, tzinfo=timezone.utc)


def candidate(**overrides):
    result = {
        "title": "Research Engineer — Time Series",
        "company": "Example AI",
        "location": "Zürich",
        "country": "CH",
        "url": "https://example.ai/jobs/123?utm_source=linkedin",
        "description": "Build PyTorch foundation models for probabilistic time-series forecasting using Python.",
        "seniority": "graduate",
        "posted_at": "2026-09-15T10:00:00Z",
        "deadline": "2026-10-15T23:59:59Z",
        "open": True,
        "why": "Direct match for time-series research, PyTorch and probabilistic modelling.",
    }
    result.update(overrides)
    return result


class CanonicalUrlTests(unittest.TestCase):
    def test_strips_tracking_and_normalizes_host(self):
        self.assertEqual(
            pipeline.canonicalize_url("https://WWW.Example.com/jobs/1/?utm_source=x&b=2"),
            "https://example.com/jobs/1?b=2",
        )

    def test_normalizes_finn_ids(self):
        self.assertEqual(
            pipeline.canonicalize_url("https://www.finn.no/job/fulltime/ad.html?finnkode=474777851"),
            "https://finn.no/job/ad/474777851",
        )


class GateAndScoreTests(unittest.TestCase):
    def test_time_series_role_is_research_and_scores_highly(self):
        job = candidate()
        self.assertEqual(pipeline.infer_lane(job), "ai_research")
        score, signals = pipeline.score_job(job, NOW)
        self.assertGreaterEqual(score, 85)
        self.assertIn("time series", signals)

    def test_data_science_employer_and_eligibility_gates(self):
        job = candidate(title="Data Scientist Intern", company="Google", description="Python SQL experimentation and statistical modelling", lane="data_science")
        self.assertEqual(pipeline.infer_lane(job), "data_science")
        self.assertIsNone(pipeline.hard_gate(job, NOW))
        self.assertEqual(pipeline.hard_gate(dict(job, company="Generic BI Consultancy"), NOW), "data_science_employer_not_priority")
        self.assertEqual(pipeline.hard_gate(dict(job, phd_required=True), NOW), "phd_required")
        self.assertIsNone(pipeline.hard_gate(dict(job, company="Comparable Firm", employer_tier="elite", employer_evidence="Verified technical and compensation evidence", employer_evidence_url="https://example.com/evidence"), NOW))

    def test_expired_job_is_rejected(self):
        self.assertEqual(
            pipeline.hard_gate(candidate(deadline="2026-09-01"), NOW),
            "deadline_passed",
        )

    def test_phd_required_is_rejected_but_preferred_is_not(self):
        self.assertEqual(pipeline.hard_gate(candidate(phd_required=True), NOW), "phd_required")
        self.assertIsNone(
            pipeline.hard_gate(candidate(description="PhD preferred; MSc candidates welcome"), NOW)
        )


class SelectionAndRenderingTests(unittest.TestCase):
    def test_coverage_requires_two_sources_for_new_countries(self):
        payload = {
            "sources": [
                {"id": "finn", "country": "NO"},
                {"id": "optiver", "country": "NL"},
                {"id": "jobs_ch", "country": "CH"},
                {"id": "gradireland", "country": "IE"},
                {"id": "gradcracker", "country": "UK"},
            ]
        }
        with self.assertRaisesRegex(ValueError, "insufficient source coverage"):
            pipeline.validate_coverage(payload)

    def test_selection_represents_all_available_lanes(self):
        jobs = []
        for index, lane in enumerate(pipeline.LANE_META):
            job = candidate(
                title=f"Role {index}",
                company=f"Company {index}",
                country=("CH", "IE", "UK", "NL")[index],
                location=("Zürich", "Dublin", "London", "Amsterdam")[index],
                url=f"https://example.com/jobs/{index}",
                lane=lane,
            )
            job["score"] = 90 - index
            job["signals"] = ["Python"]
            jobs.append(job)
        selected = pipeline.select_diverse(jobs)
        self.assertEqual({job["lane"] for job in selected}, pipeline.VALID_LANES)

    def test_rendered_digest_is_valid_and_compact(self):
        job = candidate()
        job.update(lane="ai_research", score=94, signals=["PyTorch", "time series"])
        payload = {
            "sources": [
                {"id": "jobs_ch", "country": "CH", "status": "ok"},
                {"id": "gradireland", "country": "IE", "status": "error"},
            ]
        }
        message = pipeline.render_digest([job], payload, NOW)
        pipeline.validate_digest(message)
        self.assertTrue(message.startswith("💼"))
        self.assertIn("🔬", message)
        self.assertIn("time series", message)
        self.assertIn("⚠️ 1 source warning", message)
        self.assertLessEqual(len(message), pipeline.MAX_MESSAGE_CHARS)

    def test_twenty_job_report_can_exceed_single_telegram_message(self):
        jobs = []
        for index in range(20):
            job = candidate(company=f"Company {index}", country=("NO", "NL", "CH", "IE", "UK")[index % 5], url=f"https://example.com/jobs/{index}")
            job.update(lane="ai_research", score=90, signals=["Python"])
            jobs.append(job)
        selected = pipeline.select_diverse(jobs)
        self.assertEqual(len(selected), 20)
        message = pipeline.render_digest(selected, {}, NOW)
        pipeline.validate_digest(message)
        self.assertGreater(len(message), 4096)
        self.assertEqual(sum(line.startswith("🔗 ") for line in message.splitlines()), 20)

    def test_small_result_limit_is_respected_with_four_lanes(self):
        jobs = [dict(candidate(url=f"https://example.com/{index}"), lane=lane, score=90) for index, lane in enumerate(pipeline.LANE_META)]
        self.assertEqual(len(pipeline.select_diverse(jobs, 1)), 1)
        self.assertEqual(pipeline.select_diverse(jobs, 0), [])

    def test_pay_is_sourced_and_estimates_are_labeled(self):
        job = candidate(lane="data_science", compensation="GBP 80–100k base/year", compensation_basis="estimate", compensation_source_url="https://example.com/pay")
        self.assertIn("Estimated pay", pipeline.compensation_label(job))
        self.assertIn("Pay not disclosed", pipeline.compensation_label(dict(job, compensation_source_url="")))
        self.assertIn("Published pay", pipeline.compensation_label(dict(job, compensation_basis="employer_disclosed")))

    def test_expanded_employers_keep_data_science_roles_eligible(self):
        for company in ("Cognite", "Mastercard", "ASML", "Booking.com", "UBS", "Swiss Re"):
            with self.subTest(company=company):
                job = candidate(company=company, lane="data_science")
                self.assertIsNone(pipeline.hard_gate(job, NOW))
        self.assertFalse(pipeline.priority_employer(candidate(company="Unrelated ASML Recruitment")))

    def test_four_company_results_share_alias_cap(self):
        names = ("Google", "Google Inc", "DeepMind", "Google DeepMind", "Google")
        jobs = [dict(candidate(company=name, url=f"https://example.com/{i}"), lane="ai_research", score=90-i) for i, name in enumerate(names)]
        self.assertEqual(len(pipeline.select_diverse(jobs)), 4)

    def test_primary_markets_take_slots_before_secondary_markets(self):
        jobs = [dict(candidate(company=f"Employer {i}", country=country, url=f"https://example.com/{i}"), lane="ai_research", score=score)
                for i, (country, score) in enumerate((("UK", 100), ("NO", 80), ("IE", 79), ("NL", 78), ("CH", 77)))]
        selected = pipeline.select_diverse(jobs, 4)
        self.assertEqual({job["country"] for job in selected}, pipeline.PRIMARY_COUNTRIES)

    def test_coverage_requires_two_attempts_in_each_primary_market(self):
        sources = [{"id": f"source-{i}", "country": country} for country in ("NO", "IE", "NL", "CH") for i in range(2)]
        sources.append({"id": "uk-secondary", "country": "UK"})
        pipeline.validate_coverage({"sources": sources})
        with self.assertRaises(ValueError):
            pipeline.validate_coverage({"sources": sources[1:]})

    def test_legacy_migration_preserves_seen_urls(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy = root / "seen.json"
            ledger_path = root / "jobs.json"
            legacy.write_text(json.dumps(["https://example.com/jobs/1?utm_source=x"]), encoding="utf-8")
            ledger = pipeline.load_ledger(ledger_path, legacy)
            self.assertIn("https://example.com/jobs/1", ledger["jobs"])
            self.assertEqual(ledger["jobs"]["https://example.com/jobs/1"]["status"], "legacy_seen")


if __name__ == "__main__":
    unittest.main()
