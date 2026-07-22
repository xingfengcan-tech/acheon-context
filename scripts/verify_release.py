"""Fail-closed checks for a reproducible, credential-free release tree."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

from build_release import ARCHIVE, MANIFEST, included_files

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "README.md",
    "LICENSE",
    "SECURITY.md",
    "THIRD_PARTY_NOTICES.md",
    "pyproject.toml",
    ".env.example",
    ".gitattributes",
    "main.py",
    "docs/ARCHITECTURE.md",
    "docs/EVALUATION.md",
    "docs/BUILD_WEEK_SUBMISSION.md",
    "docs/DEMO_SCRIPT.md",
    "docs/FINAL_REPORT.md",
    "docs/IMPACT_AUDIT.md",
    "docs/architecture.png",
    "docs/evaluation-loop.png",
    "artifacts/benchmark/latest.json",
    "artifacts/online/context-integrity-failure-review.json",
    "artifacts/online/context-integrity-latest.json",
    "artifacts/online/latest.json",
    "contributions/openai/README.md",
    "contributions/openai/PUBLICATION_BOUNDARY.md",
    "contributions/openai/disclosure-manifest.json",
    "contributions/openai/evals/registry/data/long-horizon-context-integrity/samples.jsonl",
    "scripts/verify_openai_contribution.py",
)
TEXT_SUFFIXES = {
    ".py",
    ".md",
    ".toml",
    ".json",
    ".jsonl",
    ".html",
    ".js",
    ".css",
    ".yaml",
    ".yml",
}
IGNORED_SCAN_PARTS = {
    ".git",
    ".venv",
    ".codex",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "build",
}
SECRET_PATTERNS = (
    ("OpenAI-style key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    (
        "JWT",
        re.compile(
            r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\."
            r"[A-Za-z0-9_-]{10,}\b"
        ),
    ),
    (
        "private key",
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    ),
    (
        "quoted credential assignment",
        re.compile(
            r"\b(?:api[_-]?key|secret|token|password)\b\s*[:=]\s*"
            r"[\"'][^\"'\r\n]{8,}[\"']",
            re.IGNORECASE,
        ),
    ),
)
ASSIGNMENT_PATTERN = re.compile(r"OPENAI_API_KEY\s*=\s*[^\s#]+")
BENCHMARK_SCHEMA = "acheon.offline-selection-benchmark.v1"
ONLINE_EVIDENCE_SCHEMA = "acheon.live-runtime-observation.v1"
CONTEXT_INTEGRITY_SCHEMA = "acheon.context-integrity-online-observation.v1"
CONTEXT_INTEGRITY_REVIEW_SCHEMA = "acheon.context-integrity-agent-review.v1"
VOLATILE_BENCHMARK_FIELDS = {
    "implementation",
    "latency_ms",
    "platform",
    "python_version",
    "report_digest",
    "runtime_ms",
    "timing_note",
}


def digest_json(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def fail(message: str, failures: list[str]) -> None:
    failures.append(message)


def digest_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def scan_text(label: str, text: str, failures: list[str]) -> None:
    for name, pattern in SECRET_PATTERNS:
        if pattern.search(text):
            fail(f"possible {name} in {label}", failures)
    if not label.endswith(".env.example") and ASSIGNMENT_PATTERN.search(text):
        fail(f"non-example API key assignment in {label}", failures)


def stable_benchmark_view(value: object) -> object:
    """Drop only declared host/timing fields before source-to-artifact comparison."""

    if isinstance(value, dict):
        return {
            key: stable_benchmark_view(item)
            for key, item in value.items()
            if key not in VOLATILE_BENCHMARK_FIELDS
        }
    if isinstance(value, list):
        return [stable_benchmark_view(item) for item in value]
    return value


def verify_benchmark_comparison(
    reference: dict[str, object], candidate_path: Path, failures: list[str]
) -> None:
    try:
        candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"invalid comparison benchmark {candidate_path}: {exc}", failures)
        return
    if digest_json(stable_benchmark_view(reference)) != digest_json(
        stable_benchmark_view(candidate)
    ):
        fail(
            "generated benchmark stable fields differ from artifacts/benchmark/latest.json",
            failures,
        )


def verify_documented_evidence(benchmark: dict[str, object], failures: list[str]) -> None:
    """Keep the human-facing headline evidence tied to the checked-in receipt."""

    systems = benchmark.get("systems")
    configuration = benchmark.get("configuration")
    reproducibility = benchmark.get("reproducibility")
    if not all(isinstance(value, dict) for value in (systems, configuration, reproducibility)):
        fail("benchmark cannot drive documentation checks: invalid evidence shape", failures)
        return
    aggregate = systems.get("acheon_full", {}).get("aggregate", {})
    budget_contract = configuration.get("selector", {}).get("budget_tokens", {})
    budget_values = budget_contract.get("values", [])
    try:
        case_count = int(aggregate["case_count"])
        budget = int(budget_values[0])
        report_digest = str(benchmark["report_digest"])
        workload_digest = str(reproducibility["workload_digest"])
        configuration_digest = str(reproducibility["configuration_digest"])
        recall = float(aggregate["recall_at_budget"])
        precision = float(aggregate["precision"])
        forbidden = float(aggregate["forbidden_inclusion_rate"])
        dependency = float(aggregate["dependency_recall"])
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        fail(f"benchmark cannot drive documentation checks: {exc}", failures)
        return

    documents = {
        "README.md": (
            f"{case_count}-case synthetic selection workload",
            f"{recall:.3f} Recall@budget",
            f"{precision:.3f} precision",
        ),
        "docs/FINAL_REPORT.md": (
            f"contains {case_count} fixed-seed synthetic record-selection cases",
            f"same {budget} estimated-token-unit packet budget",
            (
                f"| Acheon full | {recall:.3f} | {precision:.3f} | "
                f"{forbidden:.3f} | {dependency:.3f} |"
            ),
            report_digest,
            workload_digest,
            configuration_digest,
        ),
    }
    for relative, fragments in documents.items():
        path = ROOT / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for fragment in fragments:
            if fragment not in text:
                fail(
                    f"documented evidence in {relative} does not match the benchmark: {fragment!r}",
                    failures,
                )


def verify_online_evidence(path: Path, failures: list[str]) -> None:
    """Validate the narrow receipt and its explicit non-comparative claim boundary."""

    try:
        evidence = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"invalid online evidence artifact: {exc}", failures)
        return
    if evidence.get("schema_version") != ONLINE_EVIDENCE_SCHEMA:
        fail(f"online evidence schema_version must be {ONLINE_EVIDENCE_SCHEMA}", failures)
    if evidence.get("evidence_level") != "live_model_observation":
        fail("online evidence must declare the live_model_observation level", failures)
    if not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?\+00:00",
        str(evidence.get("observed_at", "")),
    ):
        fail("online evidence observed_at must be an explicit UTC timestamp", failures)

    request = evidence.get("request")
    response = evidence.get("response")
    packet = evidence.get("context_packet")
    boundary = evidence.get("claim_boundary")
    if not all(isinstance(value, dict) for value in (request, response, packet, boundary)):
        fail("online evidence has an invalid receipt shape", failures)
        return

    if request.get("requested_model") != "gpt-5.6-sol":
        fail("online evidence must identify the requested GPT-5.6 Sol model", failures)
    if not str(request.get("query", "")).strip():
        fail("online evidence must identify the public smoke-test query", failures)
    if request.get("preview_only") is not False or request.get("store") is not False:
        fail("online evidence must be a non-preview call with store=False", failures)
    if response.get("returned_model") != "gpt-5.6-sol" or response.get("status") != "completed":
        fail("online evidence must record a completed GPT-5.6 Sol response", failures)
    if not re.fullmatch(r"req_[A-Za-z0-9]+", str(response.get("request_id", ""))):
        fail("online evidence request_id is missing or invalid", failures)
    if not re.fullmatch(r"resp_[A-Za-z0-9]+", str(response.get("response_id", ""))):
        fail("online evidence response_id is missing or invalid", failures)
    try:
        latency_ms = float(response["latency_ms"])
        usage = response["usage"]
        input_tokens = int(usage["input_tokens"])
        output_tokens = int(usage["output_tokens"])
        reasoning_tokens = int(usage["reasoning_tokens"])
        total_tokens = int(usage["total_tokens"])
    except (KeyError, TypeError, ValueError) as exc:
        fail(f"online evidence usage or latency is invalid: {exc}", failures)
    else:
        if latency_ms <= 0 or min(input_tokens, output_tokens, reasoning_tokens) < 0:
            fail("online evidence usage and latency must be non-negative", failures)
        if total_tokens != input_tokens + output_tokens:
            fail(
                "online evidence total_tokens must equal input_tokens plus output_tokens",
                failures,
            )
        if reasoning_tokens > output_tokens:
            fail("online evidence reasoning_tokens cannot exceed output_tokens", failures)

    try:
        budget = int(packet["budget_estimated_units"])
        used = int(packet["used_estimated_units"])
        selected = packet["selected_record_ids"]
    except (KeyError, TypeError, ValueError) as exc:
        fail(f"online evidence packet receipt is invalid: {exc}", failures)
    else:
        if budget <= 0 or used < 0 or used > budget:
            fail("online evidence packet violates its declared budget", failures)
        if (
            not isinstance(selected, list)
            or not selected
            or not all(isinstance(item, str) and item for item in selected)
            or len(selected) != len(set(selected))
        ):
            fail("online evidence selected_record_ids must be a non-empty unique list", failures)
    if not re.fullmatch(r"[0-9a-f]{64}", str(packet.get("digest", ""))):
        fail("online evidence packet digest is missing or invalid", failures)
    if evidence.get("failures") != []:
        fail("completed online smoke-test evidence must not hide or contain failures", failures)
    if boundary.get("runtime_path_observed") is not True:
        fail("online evidence must state that the runtime path was observed", failures)
    if boundary.get("comparative_answer_quality_evaluated") is not False:
        fail("single-run evidence must not claim comparative answer-quality evaluation", failures)
    if boundary.get("general_model_improvement_claimed") is not False:
        fail("online evidence must not claim general model improvement", failures)

    documents = {
        "README.md": ("artifacts/online/latest.json", "single completed GPT-5.6 Sol"),
        "docs/FINAL_REPORT.md": ("artifacts/online/latest.json", "11,530.3 ms"),
        "docs/BUILD_WEEK_SUBMISSION.md": ("artifacts/online/latest.json",),
    }
    for relative, fragments in documents.items():
        document = ROOT / relative
        if not document.is_file():
            continue
        text = document.read_text(encoding="utf-8", errors="replace")
        for fragment in fragments:
            if fragment not in text:
                fail(f"online evidence is not reflected in {relative}: {fragment!r}", failures)


def _contains_forbidden_raw_key(value: object) -> bool:
    forbidden = {
        "api_key",
        "completion",
        "input",
        "output",
        "output_text",
        "prompt",
        "request_id",
        "response_id",
        "response_text",
    }
    if isinstance(value, dict):
        return bool(forbidden.intersection(value)) or any(
            _contains_forbidden_raw_key(item) for item in value.values()
        )
    if isinstance(value, list):
        return any(_contains_forbidden_raw_key(item) for item in value)
    return False


def verify_context_integrity_evidence(
    path: Path,
    review_path: Path,
    failures: list[str],
) -> None:
    """Validate the credential-free online eval receipts and their claim boundary."""

    try:
        evidence = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"invalid context-integrity evidence artifact: {exc}", failures)
        return
    if evidence.get("schema_version") != CONTEXT_INTEGRITY_SCHEMA:
        fail(f"context-integrity schema_version must be {CONTEXT_INTEGRITY_SCHEMA}", failures)
    if evidence.get("evidence_level") != "live_model_behavior_observation":
        fail("context-integrity evidence level is invalid", failures)
    if not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?\+00:00",
        str(evidence.get("observed_at", "")),
    ):
        fail("context-integrity observed_at must be an explicit UTC timestamp", failures)
    expected_digest = evidence.get("report_digest")
    digest_payload = dict(evidence)
    digest_payload.pop("report_digest", None)
    if expected_digest != digest_json(digest_payload):
        fail("context-integrity report_digest is missing or invalid", failures)
    if _contains_forbidden_raw_key(evidence):
        fail(
            "context-integrity receipt contains completion text, input text, or provider ID",
            failures,
        )

    dataset = evidence.get("dataset")
    configuration = evidence.get("configuration")
    meta = evidence.get("grader_meta_eval")
    primary = evidence.get("primary_eval")
    usage = evidence.get("usage")
    boundary = evidence.get("claim_boundary")
    if not all(
        isinstance(value, dict)
        for value in (dataset, configuration, meta, primary, usage, boundary)
    ):
        fail("context-integrity receipt has an invalid top-level shape", failures)
        return

    if dataset.get("samples") != 24 or dataset.get("grader_validation_candidates") != 16:
        fail("context-integrity dataset counts must be 24 primary and 16 validation", failures)
    for name in ("samples_sha256", "grader_validation_sha256"):
        if not re.fullmatch(r"[0-9a-f]{64}", str(dataset.get(name, ""))):
            fail(f"context-integrity {name} is invalid", failures)
    if (
        configuration.get("solver_model") != "gpt-5.6-sol"
        or configuration.get("grader_model") != "gpt-5.6-sol"
        or configuration.get("store") is not False
        or configuration.get("model_completions_or_assembled_grader_payloads_retained") is not False
        or configuration.get("provider_request_ids_retained") is not False
        or configuration.get("repetitions") != 1
    ):
        fail("context-integrity configuration does not match the recorded run", failures)

    meta_cases = meta.get("cases")
    if (
        meta.get("correct") != 16
        or meta.get("total") != 16
        or meta.get("accuracy") != 1.0
        or meta.get("invalid_outputs") != 0
        or not isinstance(meta_cases, list)
        or len(meta_cases) != 16
    ):
        fail("context-integrity grader meta-eval receipt is invalid", failures)
    primary_cases = primary.get("cases")
    failed_ids = primary.get("failed_sample_ids")
    if (
        primary.get("passing") != 23
        or primary.get("total") != 24
        or primary.get("accuracy") != 23 / 24
        or primary.get("invalid_grader_outputs") != 0
        or failed_ids != ["lhci-016"]
        or not isinstance(primary_cases, list)
        or len(primary_cases) != 24
    ):
        fail("context-integrity primary result does not match the recorded run", failures)
    elif (
        len({str(row.get("sample_id")) for row in primary_cases}) != 24
        or sum(row.get("pass") is True for row in primary_cases) != 23
        or any(row.get("choice") not in {"Y", "N"} for row in primary_cases)
    ):
        fail("context-integrity primary case receipts are inconsistent", failures)
    by_category = primary.get("by_category")
    if (
        not isinstance(by_category, dict)
        or len(by_category) != 8
        or any(row.get("total") != 3 for row in by_category.values())
    ):
        fail("context-integrity category coverage must be eight categories of three", failures)
    if usage.get("api_calls") != 64 or int(usage.get("total_tokens", 0)) <= 0:
        fail("context-integrity usage receipt is invalid", failures)
    if (
        boundary.get("single_run_only") is not True
        or boundary.get("same_model_self_grading") is not True
        or boundary.get("acheon_vs_baseline_comparison") is not False
        or boundary.get("general_model_improvement_claimed") is not False
        or boundary.get("raw_answer_quality_human_reviewed") is not False
        or boundary.get("suitable_for_paradigm_level_claim") is not False
    ):
        fail("context-integrity claim boundary is invalid", failures)

    try:
        review = json.loads(review_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"invalid context-integrity agent-review receipt: {exc}", failures)
        return
    review_boundary = review.get("claim_boundary")
    agent_review = review.get("agent_review")
    if (
        review.get("schema_version") != CONTEXT_INTEGRITY_REVIEW_SCHEMA
        or review.get("sample_id") != "lhci-016"
        or review.get("public_synthetic_input_retained_in_dataset") is not True
        or review.get("model_completion_or_assembled_payload_retained") is not False
        or review.get("provider_request_id_retained") is not False
        or review.get("source_eval_report_digest") != expected_digest
        or not isinstance(review_boundary, dict)
        or not isinstance(agent_review, dict)
    ):
        fail("context-integrity agent-review receipt identity is invalid", failures)
        return
    if (
        agent_review.get("reviewer_type") != "codex_model_agent"
        or agent_review.get("result") != "fail"
        or agent_review.get("satisfied_safety_boundary") is not True
        or not isinstance(agent_review.get("violated_criteria"), list)
        or len(agent_review["violated_criteria"]) != 2
        or review_boundary.get("same_failure_reproduced") is not True
        or review_boundary.get("exact_original_completion_agent_reviewed") is not False
        or review_boundary.get("independent_human_review_completed") is not False
        or review_boundary.get("acheon_effect_evaluated") is not False
    ):
        fail("context-integrity agent-review result or boundary is invalid", failures)
    for name in ("source_eval_completion_digest", "reproduction_completion_digest"):
        if not re.fullmatch(r"[0-9a-f]{64}", str(review.get(name, ""))):
            fail(f"context-integrity review {name} is invalid", failures)


def verify_archive(failures: list[str], *, required: bool) -> None:
    if not ARCHIVE.exists() and not MANIFEST.exists():
        if required:
            fail("release archive and manifest are required but absent", failures)
        return
    if not ARCHIVE.is_file() or not MANIFEST.is_file():
        fail("release archive and manifest must either both exist or both be absent", failures)
        return
    try:
        sources = included_files()
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"invalid release archive or manifest: {exc}", failures)
        return
    if set(manifest) != {"schema_version", "archive", "archive_sha256", "files"}:
        fail("release manifest has unexpected or missing top-level fields", failures)
    if manifest.get("schema_version") != "1.0" or manifest.get("archive") != ARCHIVE.name:
        fail("release manifest identity is invalid", failures)
    if manifest.get("archive_sha256") != digest_file(ARCHIVE):
        fail("release archive SHA-256 does not match its manifest", failures)
    manifest_rows = manifest.get("files")
    if not isinstance(manifest_rows, list):
        fail("release manifest files must be an array", failures)
        return
    if any(
        not isinstance(row, dict) or set(row) != {"path", "size", "sha256"} for row in manifest_rows
    ):
        fail("release manifest file entries have an invalid shape", failures)
        return
    rows_by_path = {str(row["path"]): row for row in manifest_rows}
    if len(rows_by_path) != len(manifest_rows):
        fail("release manifest contains duplicate file paths", failures)

    source_by_relative = {path.relative_to(ROOT).as_posix(): path for path in sources}
    expected_names = {f"acheon/{relative}" for relative in source_by_relative}
    if set(rows_by_path) != set(source_by_relative):
        fail("release manifest paths do not match the explicit allowlist", failures)
    try:
        with zipfile.ZipFile(ARCHIVE) as bundle:
            names = bundle.namelist()
            if set(names) != expected_names or len(names) != len(expected_names):
                fail("release archive members do not match the explicit allowlist", failures)
            if any(name.startswith("/") or ".." in Path(name).parts for name in names):
                fail("release archive contains an unsafe member path", failures)
            forbidden_markers = (
                "/.codex/",
                ".egg-info/",
                "/docs/BUILD_BRIEF.md",
                "/smoke",
            )
            if any(any(marker in f"/{name}" for marker in forbidden_markers) for name in names):
                fail("release archive contains an internal or generated file", failures)
            bad_member = bundle.testzip()
            if bad_member is not None:
                fail(f"release archive has a corrupt member: {bad_member}", failures)
            for relative, source in source_by_relative.items():
                name = f"acheon/{relative}"
                if name not in names:
                    continue
                data = bundle.read(name)
                source_data = source.read_bytes()
                data_digest = hashlib.sha256(data).hexdigest()
                row = rows_by_path.get(relative, {})
                if data != source_data:
                    fail(f"release member is stale or altered: {relative}", failures)
                if row.get("size") != len(data) or row.get("sha256") != data_digest:
                    fail(f"release manifest receipt mismatch: {relative}", failures)
                if source.suffix.lower() in TEXT_SUFFIXES or source.name == ".env.example":
                    scan_text(
                        f"archive:{relative}",
                        data.decode("utf-8", errors="replace"),
                        failures,
                    )
    except (OSError, KeyError, zipfile.BadZipFile) as exc:
        fail(f"invalid release archive: {exc}", failures)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--require-archive",
        action="store_true",
        help="fail unless the allowlisted ZIP and manifest both exist and validate",
    )
    parser.add_argument(
        "--compare-benchmark",
        type=Path,
        metavar="PATH",
        help="compare a fresh benchmark with the checked-in artifact, ignoring host timing",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    failures: list[str] = []
    warnings: list[str] = []
    for relative in REQUIRED:
        if not (ROOT / relative).is_file():
            fail(f"missing required file: {relative}", failures)

    for path in ROOT.rglob("*"):
        relative_parts = path.relative_to(ROOT).parts
        if not path.is_file() or any(part in IGNORED_SCAN_PARTS for part in relative_parts):
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name != ".env.example":
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        relative = path.relative_to(ROOT).as_posix()
        scan_text(relative, text, failures)
        if "PENDING" in text and (relative == "README.md" or relative.startswith("docs/")):
            warnings.append(f"manual release field remains in {relative}")

    benchmark_path = ROOT / "artifacts/benchmark/latest.json"
    if benchmark_path.is_file():
        try:
            benchmark = json.loads(benchmark_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            fail(f"invalid benchmark artifact: {exc}", failures)
        else:
            if benchmark.get("schema_version") != BENCHMARK_SCHEMA:
                fail(f"benchmark schema_version must be {BENCHMARK_SCHEMA}", failures)
            aggregate = benchmark.get("systems", {}).get("acheon_full", {}).get("aggregate", {})
            if aggregate.get("case_count", 0) < 200:
                fail("benchmark must contain at least 200 reference cases", failures)
            if aggregate.get("budget_violation_rate", 1) != 0:
                fail("benchmark reports budget violations", failures)
            if aggregate.get("determinism_rate", 0) != 1:
                fail("benchmark reports determinism failures", failures)
            if benchmark.get("evidence_boundary", {}).get("does_not_measure") is None:
                fail("benchmark is missing its evidence boundary", failures)
            expected_digest = benchmark.get("report_digest")
            digest_payload = dict(benchmark)
            digest_payload.pop("report_digest", None)
            if not expected_digest or expected_digest != digest_json(digest_payload):
                fail("benchmark report_digest is missing or invalid", failures)
            verify_documented_evidence(benchmark, failures)
            if args.compare_benchmark is not None:
                verify_benchmark_comparison(benchmark, args.compare_benchmark, failures)

    online_path = ROOT / "artifacts/online/latest.json"
    if online_path.is_file():
        verify_online_evidence(online_path, failures)

    context_integrity_path = ROOT / "artifacts/online/context-integrity-latest.json"
    context_integrity_review_path = ROOT / "artifacts/online/context-integrity-failure-review.json"
    if context_integrity_path.is_file() and context_integrity_review_path.is_file():
        verify_context_integrity_evidence(
            context_integrity_path,
            context_integrity_review_path,
            failures,
        )

    verify_archive(failures, required=args.require_archive)

    result = {"ok": not failures, "failures": failures, "warnings": sorted(set(warnings))}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
