# Validation instructions and preparation receipt

## Recorded structural receipt

The staging package was checked locally on 2026-07-22. The receipt below covers
deterministic file validation only; the separate online observation is described
later in this document.

```text
PASS jsonl_parse=40/40 primary=24 validation=16
PASS primary_ids=24 input_digests=24 domains=24 categories=8x3
PASS grader_ids=16 labels=Y8/N8 categories=8x2
PASS output_contract_examples=4_bullets,<=60_words,5_lines
PASS yaml_shape=2/2 no_tabs=true required_keys=true
PASS yaml_parse=2/2 parser=PyYAML-6.0.3
PASS executable_eval_files=0 publication_denylist_matches=0
```

Core file digests at preparation time:

```text
e11ee0b0011c9c65939a10d1aaf17419d203b806061b4a0d9db6e8a395d2ad45  registry/data/long-horizon-context-integrity/samples.jsonl
162ab04a0e00fe1b278cb5c5950953de4d95e50b6b36e058eef2eb3c6ceeaf4d  registry/data/long-horizon-context-integrity/grader_validation.jsonl
6bf7c340baf7463ef1903696f0995b70514ef05cb0b04493cb5041ca19cc42f4  registry/evals/long-horizon-context-integrity.yaml
2118836337bd4e730e82bc24c6f9ca547ca4ea9fb7964ea325987ddd676cf5d2  registry/modelgraded/long-horizon-context-integrity.yaml
```

Both YAML files were also parsed successfully with PyYAML 6.0.3 in an isolated
validation environment. Resolving the aliases through the upstream registry and
running the eval remain pre-submission gates because they depend on an upstream
checkout and an explicitly selected solver.

## Repeat the JSONL checks

Run the following standard-library script from this staging directory, or change
`root` to the copied upstream paths:

```python
import collections
import json
from pathlib import Path

root = Path("registry/data/long-horizon-context-integrity")

def load(name):
    rows = []
    for line_number, line in enumerate((root / name).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            raise AssertionError(f"{name}:{line_number}: blank line")
        rows.append(json.loads(line))
    return rows

samples = load("samples.jsonl")
grader = load("grader_validation.jsonl")

assert len(samples) == 24
assert len({row["sample_id"] for row in samples}) == 24
assert len({json.dumps(row["input"], sort_keys=True) for row in samples}) == 24
assert len({row["domain"] for row in samples}) == 24
assert set(collections.Counter(row["category"] for row in samples).values()) == {3}

required = {"sample_id", "category", "domain", "input", "criteria", "ideal"}
for row in samples:
    assert required <= row.keys()
    assert isinstance(row["input"], list) and row["input"][-1]["role"] == "user"
    assert all(set(message) == {"role", "content"} for message in row["input"])

assert len(grader) == 16
assert len({row["validation_id"] for row in grader}) == 16
assert collections.Counter(row["choice"] for row in grader) == {"Y": 8, "N": 8}
assert set(collections.Counter(row["category"] for row in grader).values()) == {2}

for category in {row["category"] for row in samples}:
    assert {row["choice"] for row in grader if row["category"] == category} == {"Y", "N"}

print("JSONL validation passed")
```

On PowerShell, the block can be placed in a here-string and piped to `python -`.
On a POSIX shell, it can be passed with a standard `python - <<'PY'` heredoc.

## Repeat the YAML parse in the upstream environment

With PyYAML available:

```bash
python -c "from pathlib import Path; import yaml; paths=list(Path('evals/registry').rglob('long-horizon-context-integrity.yaml')); assert len(paths)==2; [yaml.safe_load(p.read_text(encoding='utf-8')) for p in paths]; print('YAML validation passed')"
```

Then confirm that the eval registry can resolve both aliases using the upstream
project's normal test or listing command before running a solver.

## Verify Git LFS

The current upstream PR template requires Eval JSON data to use Git LFS. After
copying into the fork:

```bash
git lfs install
git lfs track "evals/registry/data/long-horizon-context-integrity/*.jsonl"
git add .gitattributes evals/registry/data/long-horizon-context-integrity
git check-attr filter -- evals/registry/data/long-horizon-context-integrity/*.jsonl
git lfs ls-files
```

Both JSONL paths must report `filter: lfs` and appear in `git lfs ls-files`.

## Model and grader verification gate

Structural validation does not measure model behavior. A preliminary direct
Responses API run used GPT-5.6 Sol for both answer generation and grading with
`store=false`: the labeled grader meta-eval was 16/16, and the primary result was
23/24 with no invalid grader outputs. The only automated failure was `lhci-016`; a
separate human-inspected reproduction omitted required version and issue-ID details.
Public synthetic inputs are retained in the Eval dataset. Model completion text,
assembled grader payloads, and provider request IDs were not retained. See the aggregate receipt at
`artifacts/online/context-integrity-latest.json` and the narrow human-review receipt
at `artifacts/online/context-integrity-failure-review.json` in the Acheon repository.

Before an external PR, repeat both aliases in an upstream checkout with a currently
supported solver:

```bash
oaieval <solver> long-horizon-context-integrity
oaieval <solver> long-horizon-context-integrity-meta
```

Review every failure and every invalid grader output. Report the exact evaluated
model, grader model, configuration, aggregate accuracy, per-category accuracy,
meta-eval accuracy, and repeated-run policy. Do not submit a claimed score that was
not actually observed.
