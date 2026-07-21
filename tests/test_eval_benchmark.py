from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from acheon.evals.benchmark import (  # noqa: E402
    ABLATION_FLAGS,
    REFERENCE_SYSTEM,
    run_benchmark,
)
from acheon.evals.dataset import SCENARIOS, generate_workload  # noqa: E402
from acheon.evals.run import main  # noqa: E402


class OfflineBenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cases = generate_workload(cases_per_scenario=1, history_size=32)
        cls.report = run_benchmark(cls.cases, bootstrap_samples=100)

    def test_report_contains_all_controls_and_ablations(self) -> None:
        expected = {
            REFERENCE_SYSTEM,
            "recent_tail",
            "chronological_prefix",
            "lexical_topk",
            *ABLATION_FLAGS,
        }
        self.assertEqual(set(self.report["systems"]), expected)
        self.assertEqual(set(self.report["paired_bootstrap_95"]), expected - {REFERENCE_SYSTEM})

    def test_report_has_machine_readable_workload_gold_and_failures(self) -> None:
        self.assertEqual(self.report["reproducibility"]["case_count"], len(SCENARIOS))
        self.assertEqual(len(self.report["workload"]), len(SCENARIOS))
        self.assertTrue(all("gold" in case for case in self.report["workload"]))
        self.assertIsInstance(self.report["failures"], list)
        json.dumps(self.report)

    def test_reference_respects_budget_and_is_deterministic(self) -> None:
        aggregate = self.report["systems"][REFERENCE_SYSTEM]["aggregate"]
        self.assertEqual(aggregate["budget_violation_rate"], 0.0)
        self.assertEqual(aggregate["determinism_rate"], 1.0)
        self.assertEqual(aggregate["forbidden_inclusion_rate"], 0.0)

    def test_dependency_ablation_exposes_dependency_contract(self) -> None:
        full = self.report["systems"][REFERENCE_SYSTEM]["aggregate"]
        ablated = self.report["systems"]["ablation_no_dependencies"]["aggregate"]
        self.assertGreater(full["dependency_recall"], ablated["dependency_recall"])

    def test_evidence_boundary_disallows_model_capability_extrapolation(self) -> None:
        boundary = self.report["evidence_boundary"]
        self.assertIn("synthetic", boundary["workload"])
        self.assertIn("general language-model intelligence", boundary["does_not_measure"])
        self.assertIn("must not", boundary["claim_rule"])

    def test_report_configuration_uses_workload_budget_and_final_renderer(self) -> None:
        budget = self.report["configuration"]["selector"]["budget_tokens"]
        self.assertEqual(budget["source"], "workload")
        self.assertEqual(budget["values"], [self.cases[0].budget_tokens])
        aggregate = self.report["systems"][REFERENCE_SYSTEM]["aggregate"]
        self.assertEqual(aggregate["budget_violation_rate"], 0.0)

    def test_cli_writes_requested_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            status = main(
                (
                    "--output",
                    str(output),
                    "--cases-per-scenario",
                    "1",
                    "--history-size",
                    "32",
                    "--bootstrap-samples",
                    "100",
                )
            )
            self.assertEqual(status, 0)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema_version"], self.report["schema_version"])


if __name__ == "__main__":
    unittest.main()
