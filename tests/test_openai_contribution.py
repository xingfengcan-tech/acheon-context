from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "verify_openai_contribution.py"
SPEC = importlib.util.spec_from_file_location("verify_openai_contribution", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)


class OpenAIContributionVerificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.showcase = json.loads(
            (ROOT / "contributions/openai/showcase/fields.en.json").read_text(encoding="utf-8")
        )

    def test_current_non_evals_package_passes(self) -> None:
        failures, warnings = verifier.verify()
        self.assertEqual(failures, [])
        self.assertEqual(warnings, [])

    def test_showcase_limit_is_enforced(self) -> None:
        payload = copy.deepcopy(self.showcase)
        payload["project_fields"]["tagline"] = "x" * 256
        failures: list[str] = []
        verifier.validate_showcase(payload, failures)
        self.assertTrue(any("tagline exceeds" in failure for failure in failures))

    def test_manual_attestation_cannot_be_prefilled(self) -> None:
        payload = copy.deepcopy(self.showcase)
        payload["operator_attestations"]["final_submit"] = True
        failures: list[str] = []
        verifier.validate_showcase(payload, failures)
        self.assertIn("manual attestation must remain null: final_submit", failures)

    def test_secret_patterns_are_rejected(self) -> None:
        failures: list[str] = []
        verifier.scan_public_text("example.md", "sk-" + "a" * 24, failures)
        self.assertTrue(any("OpenAI-style key" in failure for failure in failures))

    def test_non_https_public_url_is_rejected(self) -> None:
        failures: list[str] = []
        verifier.validate_public_url("http://example.com/project", "project", failures)
        self.assertEqual(failures, ["project must be an HTTPS URL without embedded credentials"])

    def test_bad_feedback_jsonl_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "feedback.jsonl"
            path.write_text('{"prompt":"raw"}\n', encoding="utf-8")
            failures: list[str] = []
            verifier.validate_feedback_notes(path, failures)
        self.assertTrue(any("unexpected fields" in failure for failure in failures))


if __name__ == "__main__":
    unittest.main()
