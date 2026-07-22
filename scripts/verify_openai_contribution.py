"""Fail-closed checks for the reviewed, non-Evals OpenAI contribution package.

The Evals directory has its own upstream-compatible validation. This verifier
intentionally does not read it. It also performs no network requests, so the
result is deterministic and cannot submit or disclose any material.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Iterable, Mapping
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
CONTRIBUTION_ROOT = ROOT / "contributions" / "openai"

SHOWCASE_FORM_URL = "https://openai.com/form/showcase-submission/"
SHOWCASE_LIMITS = {
    "use_cases": 255,
    "capability": 1000,
    "openai_models_and_apis": 500,
    "other_models_or_apis": 255,
    "building_process": 500,
    "setup_steps": 500,
    "title": 255,
    "tagline": 255,
    "description": 1000,
}
AUTHOR_NAME_LIMIT = 500

REQUIRED_FILES = {
    "README.md",
    "PUBLICATION_BOUNDARY.md",
    "disclosure-manifest.json",
    "showcase/fields.en.json",
    "showcase/description.en.md",
    "showcase/setup.txt",
    "showcase/cover-alt.txt",
    "community/technical-post.en.md",
    "community/short-summary.en.md",
    "api-feedback/expected-behavior.md",
    "api-feedback/feedback-notes.jsonl",
    "api-feedback/sanitized-cases.jsonl",
}
REQUIRED_PROJECT_FIELDS = {
    "project_type",
    "used_codex",
    "used_another_coding_agent",
    "tech_stack",
    "use_cases",
    "capability",
    "openai_models_and_apis",
    "other_models_or_apis",
    "setup_steps",
    "building_process",
    "title",
    "tagline",
    "description",
    "cover_image_url",
}
MANUAL_IDENTITY_FIELDS = {
    "first_name",
    "last_name",
    "email",
    "display_author_name",
}
MANUAL_ATTESTATIONS = {
    "owns_or_has_permission_for_cover_and_content",
    "has_authority_to_accept_program_agreement",
    "accepts_showcase_program_agreement",
    "final_submit",
}
REQUIRED_GATES = {
    "identity_and_contact_details",
    "rights_and_authority_attestation",
    "showcase_program_agreement",
    "open_source_eval_data_license_confirmation",
    "community_account_identity",
    "organization_level_data_sharing_choice",
}
REQUIRED_FEEDBACK_CATEGORIES = {
    "early_constraint_retention",
    "supersession_and_revocation",
    "conflict_visibility",
    "dependency_completeness",
    "scope_isolation",
    "untrusted_content_resistance",
    "budget_priority",
    "uncertainty_calibration",
}

SECRET_PATTERNS = {
    "OpenAI-style key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    "Slack token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "JWT": re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "quoted credential": re.compile(
        r"\b(?:api[_-]?key|secret|token|password)\b\s*[:=]\s*[\"'][^\"'\r\n]{8,}[\"']",
        re.IGNORECASE,
    ),
}
URL_PATTERN = re.compile(r"https?://[^\s<>\]\[\"']+")
FILE_REFERENCE_PATTERN = re.compile(
    r"`([^`\r\n]+\.(?:jsonl|json|md|png|txt|yaml|yml))`", re.IGNORECASE
)
ISO_DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")


def add_failure(failures: list[str], message: str) -> None:
    failures.append(message)


def read_json(path: Path, failures: list[str]) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        add_failure(failures, f"invalid JSON in {path.name}: {exc}")
        return None
    if not isinstance(value, dict):
        add_failure(failures, f"{path.name} must contain a JSON object")
        return None
    return value


def validate_public_url(
    value: object, label: str, failures: list[str], *, allowed_hosts: set[str] | None = None
) -> None:
    if not isinstance(value, str) or not value.strip():
        add_failure(failures, f"{label} must be a non-empty public URL")
        return
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        add_failure(failures, f"{label} must be an HTTPS URL without embedded credentials")
        return
    if allowed_hosts is not None and parsed.hostname.lower() not in allowed_hosts:
        add_failure(failures, f"{label} uses an unexpected host: {parsed.hostname}")


def scan_public_text(label: str, text: str, failures: list[str]) -> None:
    for name, pattern in SECRET_PATTERNS.items():
        if pattern.search(text):
            add_failure(failures, f"possible {name} in {label}")


def validate_showcase(payload: Mapping[str, Any], failures: list[str]) -> None:
    if payload.get("form_url") != SHOWCASE_FORM_URL:
        add_failure(failures, "showcase form_url does not match the official form")
    prepared_on = payload.get("prepared_on")
    if not isinstance(prepared_on, str) or not ISO_DATE_PATTERN.fullmatch(prepared_on):
        add_failure(failures, "showcase prepared_on must be an ISO date")
    else:
        try:
            date.fromisoformat(prepared_on)
        except ValueError:
            add_failure(failures, "showcase prepared_on is not a real calendar date")

    operator = payload.get("operator_fields")
    project = payload.get("project_fields")
    attestations = payload.get("operator_attestations")
    if not isinstance(operator, Mapping):
        add_failure(failures, "showcase operator_fields must be an object")
        return
    if not isinstance(project, Mapping):
        add_failure(failures, "showcase project_fields must be an object")
        return
    if not isinstance(attestations, Mapping):
        add_failure(failures, "showcase operator_attestations must be an object")
        return

    for field in sorted(MANUAL_IDENTITY_FIELDS):
        if field not in operator:
            add_failure(failures, f"missing operator field: {field}")
        elif operator[field] is not None:
            add_failure(failures, f"manual identity field must remain null: {field}")
    profile = operator.get("website_or_social_profile")
    if profile is not None:
        validate_public_url(profile, "website_or_social_profile", failures)

    for field in sorted(MANUAL_ATTESTATIONS):
        if field not in attestations:
            add_failure(failures, f"missing operator attestation: {field}")
        elif attestations[field] is not None:
            add_failure(failures, f"manual attestation must remain null: {field}")

    for field in sorted(REQUIRED_PROJECT_FIELDS):
        value = project.get(field)
        if not isinstance(value, str) or not value.strip():
            add_failure(failures, f"required showcase project field is empty: {field}")
    if not project.get("public_github_repository") and not project.get("hosted_url"):
        add_failure(failures, "showcase requires a public repository or hosted URL")

    for field, limit in SHOWCASE_LIMITS.items():
        value = project.get(field)
        if isinstance(value, str) and len(value) > limit:
            add_failure(
                failures,
                f"showcase {field} exceeds the official {limit}-character limit: {len(value)}",
            )
    author = operator.get("display_author_name")
    if isinstance(author, str) and len(author) > AUTHOR_NAME_LIMIT:
        add_failure(failures, "showcase display_author_name exceeds 500 characters")

    repository = project.get("public_github_repository")
    if repository is not None:
        validate_public_url(
            repository,
            "public_github_repository",
            failures,
            allowed_hosts={"github.com"},
        )
    hosted = project.get("hosted_url")
    if hosted is not None:
        validate_public_url(hosted, "hosted_url", failures)
    validate_public_url(
        project.get("cover_image_url"),
        "cover_image_url",
        failures,
        allowed_hosts={"raw.githubusercontent.com"},
    )


def validate_manifest(payload: Mapping[str, Any], failures: list[str]) -> tuple[set[str], set[str]]:
    if payload.get("schema_version") != "acheon.openai-contribution-disclosure.v1":
        add_failure(failures, "unexpected disclosure manifest schema_version")
    if payload.get("project") != "Acheon":
        add_failure(failures, "disclosure manifest project must be Acheon")
    reviewed_on = payload.get("reviewed_on")
    if not isinstance(reviewed_on, str) or not ISO_DATE_PATTERN.fullmatch(reviewed_on):
        add_failure(failures, "disclosure manifest reviewed_on must be an ISO date")
    else:
        try:
            date.fromisoformat(reviewed_on)
        except ValueError:
            add_failure(failures, "disclosure manifest reviewed_on is not a real calendar date")

    validate_public_url(
        payload.get("public_repository"),
        "manifest public_repository",
        failures,
        allowed_hosts={"github.com"},
    )
    validate_public_url(
        payload.get("public_release"),
        "manifest public_release",
        failures,
        allowed_hosts={"github.com"},
    )

    gates = payload.get("external_action_gates")
    if not isinstance(gates, list) or not all(isinstance(item, str) for item in gates):
        add_failure(failures, "external_action_gates must be a string list")
    else:
        missing = REQUIRED_GATES.difference(gates)
        if missing:
            add_failure(failures, f"missing external action gates: {sorted(missing)}")

    evidence = payload.get("evidence_levels")
    expected_evidence = {
        "engineering_contracts": "observed_and_reproducible",
        "synthetic_selection_results": "observed_and_scoped",
        "live_api_path": "one_smoke_test_observed",
        "standalone_context_integrity_eval": "one_24_sample_run_observed",
        "comparative_model_answer_quality": "not_yet_observed",
        "independent_replication": "not_yet_observed",
        "paradigm_level_impact": "hypothesis_only",
    }
    if evidence != expected_evidence:
        add_failure(failures, "evidence_levels must preserve the reviewed claim boundary")

    approved_value = payload.get("approved_files")
    if not isinstance(approved_value, list) or not all(
        isinstance(item, str) for item in approved_value
    ):
        add_failure(failures, "approved_files must be a string list")
        approved: set[str] = set()
    else:
        approved = set(approved_value)
        if len(approved) != len(approved_value):
            add_failure(failures, "approved_files contains duplicates")

    deferred_value = payload.get("deferred_files", {})
    if not isinstance(deferred_value, Mapping) or not all(
        isinstance(key, str) and isinstance(reason, str) and reason.strip()
        for key, reason in deferred_value.items()
    ):
        add_failure(failures, "deferred_files must map paths to non-empty reasons")
        deferred: set[str] = set()
    else:
        deferred = set(deferred_value)
    if approved.intersection(deferred):
        add_failure(failures, "a contribution file cannot be both approved and deferred")
    return approved, deferred


def validate_feedback_notes(path: Path, failures: list[str]) -> None:
    required = {
        "case_id",
        "model",
        "response_id",
        "observed_at",
        "result",
        "violated_criteria",
        "sanitized_explanation",
        "shared_via_playground",
    }
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        add_failure(failures, f"cannot read feedback notes: {exc}")
        return
    nonempty = [line for line in lines if line.strip()]
    if not nonempty:
        add_failure(failures, "feedback-notes.jsonl must contain a sanitized template")
        return
    for number, line in enumerate(nonempty, start=1):
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            add_failure(failures, f"invalid feedback JSONL line {number}: {exc}")
            continue
        if not isinstance(value, dict) or set(value) != required:
            add_failure(failures, f"feedback JSONL line {number} has unexpected fields")
            continue
        if not isinstance(value["violated_criteria"], list):
            add_failure(failures, f"feedback JSONL line {number} violated_criteria must be a list")
        if not isinstance(value["shared_via_playground"], bool):
            add_failure(
                failures, f"feedback JSONL line {number} shared_via_playground must be boolean"
            )
        if value["result"] not in {"pass", "fail", "pass_or_fail"}:
            add_failure(failures, f"feedback JSONL line {number} has invalid result")
        forbidden_payload_fields = {"prompt", "input", "output", "response_text"}
        if forbidden_payload_fields.intersection(value):
            add_failure(failures, f"feedback JSONL line {number} contains a raw payload field")


def validate_sanitized_cases(path: Path, failures: list[str]) -> None:
    required = {"case_id", "category", "domain", "input", "criteria", "reference"}
    try:
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except OSError as exc:
        add_failure(failures, f"cannot read sanitized feedback cases: {exc}")
        return
    if len(lines) != len(REQUIRED_FEEDBACK_CATEGORIES):
        add_failure(
            failures,
            "sanitized-cases.jsonl must contain one reviewed case per behavior category",
        )
    case_ids: list[str] = []
    categories: list[str] = []
    for number, line in enumerate(lines, start=1):
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            add_failure(failures, f"invalid sanitized case JSONL line {number}: {exc}")
            continue
        if not isinstance(value, dict) or set(value) != required:
            add_failure(failures, f"sanitized case line {number} has unexpected fields")
            continue
        case_ids.append(str(value["case_id"]))
        categories.append(str(value["category"]))
        if not all(
            isinstance(value[field], str) and value[field].strip() for field in required - {"input"}
        ):
            add_failure(failures, f"sanitized case line {number} has an empty text field")
        messages = value["input"]
        if (
            not isinstance(messages, list)
            or len(messages) < 2
            or not all(
                isinstance(message, dict)
                and set(message) == {"role", "content"}
                and message["role"] in {"system", "user"}
                and isinstance(message["content"], str)
                and message["content"].strip()
                for message in messages
            )
        ):
            add_failure(failures, f"sanitized case line {number} has invalid chat input")
    if len(case_ids) != len(set(case_ids)):
        add_failure(failures, "sanitized feedback case IDs must be unique")
    if set(categories) != REQUIRED_FEEDBACK_CATEGORIES or len(categories) != len(set(categories)):
        add_failure(failures, "sanitized feedback cases must cover each category exactly once")


def iter_non_eval_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if path.is_file() and "evals" not in path.relative_to(root).parts:
            yield path


def validate_references(
    root: Path, approved: set[str], deferred: set[str], failures: list[str]
) -> list[str]:
    warnings: list[str] = []
    for relative in sorted(approved):
        if "evals" in Path(relative).parts:
            continue
        path = root / relative
        if not path.is_file() or path.suffix.lower() not in {".md", ".txt", ".json", ".jsonl"}:
            continue
        text = path.read_text(encoding="utf-8")
        for raw_url in URL_PATTERN.findall(text):
            url = raw_url.rstrip(".,;:)")
            parsed = urlparse(url)
            is_loopback = parsed.hostname in {"127.0.0.1", "localhost", "::1"}
            if parsed.scheme != "https" and not is_loopback:
                add_failure(failures, f"non-HTTPS external URL in {relative}: {url}")
            if parsed.username or parsed.password:
                add_failure(failures, f"URL embeds credentials in {relative}")
        for reference in FILE_REFERENCE_PATTERN.findall(text):
            candidate = (path.parent / reference).resolve()
            if not candidate.is_relative_to(root.resolve()):
                add_failure(failures, f"file reference escapes contribution root in {relative}")
                continue
            candidate_relative = candidate.relative_to(root.resolve()).as_posix()
            if candidate.is_file():
                continue
            if candidate_relative in deferred:
                warnings.append(f"deferred file is not yet present: {candidate_relative}")
            else:
                add_failure(failures, f"missing file reference in {relative}: {reference}")
    return warnings


def verify(contribution_root: Path = CONTRIBUTION_ROOT) -> tuple[list[str], list[str]]:
    failures: list[str] = []
    warnings: list[str] = []
    if not contribution_root.is_dir():
        return [f"missing contribution directory: {contribution_root}"], warnings

    for relative in sorted(REQUIRED_FILES):
        if not (contribution_root / relative).is_file():
            add_failure(failures, f"missing required contribution file: {relative}")

    manifest = read_json(contribution_root / "disclosure-manifest.json", failures)
    showcase = read_json(contribution_root / "showcase" / "fields.en.json", failures)
    approved: set[str] = set()
    deferred: set[str] = set()
    if manifest is not None:
        approved, deferred = validate_manifest(manifest, failures)
        missing_approvals = REQUIRED_FILES.difference(approved)
        if missing_approvals:
            add_failure(
                failures,
                f"required files missing from approved_files: {sorted(missing_approvals)}",
            )
    if showcase is not None:
        validate_showcase(showcase, failures)

    actual = {
        path.relative_to(contribution_root).as_posix()
        for path in iter_non_eval_files(contribution_root)
    }
    unapproved = actual.difference(approved)
    if unapproved:
        add_failure(
            failures,
            f"non-Evals contribution files are not approved: {sorted(unapproved)}",
        )
    missing_approved = {
        relative for relative in approved if not (contribution_root / relative).is_file()
    }
    if missing_approved:
        add_failure(failures, f"approved files are missing: {sorted(missing_approved)}")

    for path in iter_non_eval_files(contribution_root):
        if path.suffix.lower() in {".md", ".txt", ".json", ".jsonl", ".yaml", ".yml"}:
            relative = path.relative_to(contribution_root).as_posix()
            try:
                scan_public_text(relative, path.read_text(encoding="utf-8"), failures)
            except UnicodeDecodeError:
                add_failure(failures, f"public text file is not valid UTF-8: {relative}")

    validate_feedback_notes(contribution_root / "api-feedback" / "feedback-notes.jsonl", failures)
    validate_sanitized_cases(contribution_root / "api-feedback" / "sanitized-cases.jsonl", failures)
    warnings.extend(validate_references(contribution_root, approved, deferred, failures))
    return failures, sorted(set(warnings))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=CONTRIBUTION_ROOT,
        help="Contribution package root (defaults to contributions/openai).",
    )
    args = parser.parse_args(argv)
    failures, warnings = verify(args.root.resolve())
    result = {
        "ok": not failures,
        "scope": "non-evals-openai-contribution",
        "showcase_form": SHOWCASE_FORM_URL,
        "failures": failures,
        "warnings": warnings,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
