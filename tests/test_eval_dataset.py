from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from acheon.evals.dataset import (  # noqa: E402
    DEFAULT_HISTORY_SIZE,
    SCENARIOS,
    generate_workload,
)


class EvaluationDatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workload = generate_workload()

    def test_default_workload_has_240_long_history_cases(self) -> None:
        self.assertEqual(len(self.workload), 240)
        self.assertEqual({case.scenario for case in self.workload}, set(SCENARIOS))
        self.assertTrue(all(len(case.records) == DEFAULT_HISTORY_SIZE for case in self.workload))

    def test_every_case_has_valid_explicit_gold_roles(self) -> None:
        for case in self.workload:
            known = {record.record_id for record in case.records}
            self.assertTrue(case.relevant_ids)
            self.assertTrue(case.forbidden_ids)
            self.assertTrue(case.dependency_ids)
            self.assertTrue(case.current_fact_ids)
            self.assertLessEqual(case.relevant_ids | case.forbidden_ids, known)
            self.assertFalse(case.relevant_ids & case.forbidden_ids)
            self.assertLessEqual(case.dependency_ids, case.relevant_ids)
            self.assertLessEqual(case.current_fact_ids, case.relevant_ids)

    def test_fixed_seed_is_order_and_content_deterministic(self) -> None:
        first = generate_workload(seed=11, cases_per_scenario=1, history_size=32)
        second = generate_workload(seed=11, cases_per_scenario=1, history_size=32)
        different = generate_workload(seed=12, cases_per_scenario=1, history_size=32)
        self.assertEqual(first, second)
        self.assertNotEqual(first, different)

    def test_manifest_is_json_safe_and_excludes_record_content(self) -> None:
        manifest = self.workload[0].manifest()
        encoded = json.dumps(manifest)
        self.assertIn('"gold"', encoded)
        self.assertNotIn("records", manifest)
        self.assertEqual(manifest["history_records"], DEFAULT_HISTORY_SIZE)

    def test_checked_in_workload_manifest_matches_generator_defaults(self) -> None:
        path = Path(__file__).resolve().parents[1] / "evals" / "workload.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["case_count"], len(self.workload))
        self.assertEqual(manifest["history_records_per_case"], DEFAULT_HISTORY_SIZE)
        self.assertEqual(manifest["scenarios"], list(SCENARIOS))

    def test_generator_rejects_short_histories_and_empty_scenario_counts(self) -> None:
        with self.assertRaises(ValueError):
            generate_workload(cases_per_scenario=0)
        with self.assertRaises(ValueError):
            generate_workload(cases_per_scenario=1, history_size=31)


if __name__ == "__main__":
    unittest.main()
