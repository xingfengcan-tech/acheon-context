"""Create a deterministic, allowlisted source ZIP and SHA-256 manifest."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
ARCHIVE = DIST / "acheon-build-week.zip"
MANIFEST = DIST / "acheon-build-week.manifest.json"

EXACT_PATHS = (
    ".env.example",
    ".github/workflows/ci.yml",
    ".gitignore",
    "AGENTS.md",
    "CHANGELOG.md",
    "Dockerfile",
    "LICENSE",
    "README.md",
    "SECURITY.md",
    "THIRD_PARTY_NOTICES.md",
    "artifacts/benchmark/latest.json",
    "artifacts/online/context-integrity-failure-review.json",
    "artifacts/online/context-integrity-latest.json",
    "artifacts/online/latest.json",
    "docs/ARCHITECTURE.md",
    "docs/BUILD_WEEK_SUBMISSION.md",
    "docs/CODEX_USAGE.md",
    "docs/DEMO_SCRIPT.md",
    "docs/EVALUATION.md",
    "docs/FINAL_REPORT.md",
    "docs/IMPACT_AUDIT.md",
    "docs/LIMITATIONS.md",
    "docs/OPENAI_INTEGRATION.md",
    "docs/RELEASE_CHECKLIST.md",
    "docs/architecture.png",
    "docs/evaluation-loop.png",
    "evals/README.md",
    "evals/workload.json",
    "main.py",
    "pyproject.toml",
    "scripts/build_release.py",
    "scripts/generate_diagrams.py",
    "scripts/run_openai_context_integrity_eval.py",
    "scripts/verify_openai_contribution.py",
    "scripts/verify_release.py",
    "src/acheon/py.typed",
    "uv.lock",
)
TREE_RULES = {
    "contributions/openai": {".json", ".jsonl", ".md", ".txt", ".yaml", ".yml"},
    "src/acheon": {".py", ".html", ".css", ".js"},
    "tests": {".py"},
}
IGNORED_PARTS = {"__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache"}
FIXED_ZIP_TIME = (2026, 7, 19, 0, 0, 0)


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def included_files() -> list[Path]:
    files: set[Path] = set()
    for relative in EXACT_PATHS:
        path = ROOT / relative
        if not path.is_file():
            raise FileNotFoundError(f"required release file is missing: {relative}")
        files.add(path)
    for relative_root, suffixes in TREE_RULES.items():
        base = ROOT / relative_root
        if not base.is_dir():
            raise FileNotFoundError(f"required release directory is missing: {relative_root}")
        for path in base.rglob("*"):
            relative = path.relative_to(ROOT)
            if (
                path.is_file()
                and path.suffix.lower() in suffixes
                and not any(part in IGNORED_PARTS for part in relative.parts)
            ):
                files.add(path)
    return sorted(files, key=lambda item: item.relative_to(ROOT).as_posix())


def _archive_name(path: Path) -> str:
    relative = path.relative_to(ROOT)
    return PurePosixPath("acheon", *relative.parts).as_posix()


def main() -> None:
    DIST.mkdir(parents=True, exist_ok=True)
    files = included_files()
    with zipfile.ZipFile(
        ARCHIVE,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as bundle:
        for path in files:
            info = zipfile.ZipInfo(_archive_name(path), date_time=FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            bundle.writestr(info, path.read_bytes())
    manifest = {
        "schema_version": "1.0",
        "archive": ARCHIVE.name,
        "archive_sha256": digest(ARCHIVE),
        "files": [
            {
                "path": path.relative_to(ROOT).as_posix(),
                "size": path.stat().st_size,
                "sha256": digest(path),
            }
            for path in files
        ],
    }
    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    summary = {
        "archive": str(ARCHIVE),
        "sha256": manifest["archive_sha256"],
        "files": len(files),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
