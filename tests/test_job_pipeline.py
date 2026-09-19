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
        for index, lane in enumerate(("ai_research", "ai_engineering", "quant_ml")):
            job = candidate(
                title=f"Role {index}",
                company=f"Company {index}",
                country=("CH", "IE", "UK")[index],
                location=("Zürich", "Dublin", "London")[index],
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
