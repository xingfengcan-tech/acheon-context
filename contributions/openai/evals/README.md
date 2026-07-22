# Long-Horizon Context Integrity eval contribution package

This directory is a PR-ready staging package for the public
[`openai/evals`](https://github.com/openai/evals) registry. It evaluates an
observable model behavior: reconstructing the current, authorized, scoped, and
supportable answer from a long chronological record.

The package contains no custom Python eval class and performs no API calls. It uses
the existing `ModelBasedClassify` class, one declarative registry file, one
declarative model-graded rubric, 24 hand-authored task samples, and 16
human-labeled grader-validation candidates.

## Files

```text
registry/
├── data/long-horizon-context-integrity/
│   ├── samples.jsonl
│   └── grader_validation.jsonl
├── evals/long-horizon-context-integrity.yaml
└── modelgraded/long-horizon-context-integrity.yaml
DATASET_CARD.md
PR_BODY.md
VALIDATION.md
```

When preparing an upstream fork, copy the three `registry` children into the
matching paths under the upstream repository's `evals/registry/` directory:

```text
evals/registry/data/long-horizon-context-integrity/
evals/registry/evals/long-horizon-context-integrity.yaml
evals/registry/modelgraded/long-horizon-context-integrity.yaml
```

## Evaluation surfaces

- `long-horizon-context-integrity` runs the 24 primary samples.
- `long-horizon-context-integrity-meta` runs 16 positive/negative candidate
  answers with human `choice` labels to validate the rubric.
- Each primary sample has chat-formatted `input`, an exhaustive `criteria` field,
  and a human-authored `ideal` answer for audit and spot checking.
- The rubric returns `Y` only when every material criterion is satisfied.

The cases cover eight behavior families with three primary examples each:

1. early constraint retention;
2. supersession and revocation;
3. unresolved-conflict visibility;
4. dependency completeness;
5. scope isolation;
6. resistance to untrusted embedded instructions;
7. priority under a strict answer budget; and
8. calibrated uncertainty when evidence is missing.

## Upstream compatibility

The structure follows the current official guidance:

- [Building an eval](https://github.com/openai/evals/blob/main/docs/build-eval.md)
- [Existing eval templates](https://github.com/openai/evals/blob/main/docs/eval-templates.md)
- [Current pull-request template](https://github.com/openai/evals/blob/main/.github/PULL_REQUEST_TEMPLATE.md)

The upstream repository currently asks contributors not to submit custom-code
evals, permits custom model-graded YAML, requires at least 15 high-quality samples,
and asks for JSON data to be stored with Git LFS. This package supplies 24 samples
and adds no executable eval implementation.

After copying into an upstream fork, verify Git LFS before committing:

```bash
git lfs install
git lfs track "evals/registry/data/long-horizon-context-integrity/*.jsonl"
git add .gitattributes evals/registry/data/long-horizon-context-integrity
git check-attr filter -- evals/registry/data/long-horizon-context-integrity/*.jsonl
```

Expected `filter` value: `lfs`.

## Structural verification

Run the offline checks documented in [VALIDATION.md](VALIDATION.md). They parse
every JSONL line, reject duplicate identifiers, check required fields and label
balance, inspect category coverage, parse both YAML files, and scan this package
for credential-shaped strings and prohibited private terms.

A preliminary direct Responses API observation is documented in `PR_BODY.md` and
the Acheon repository's credential-free aggregate receipt. It recorded 16/16 grader
meta-eval agreement and 23/24 passing primary cases on one GPT-5.6 Sol run; one
separately reproduced failure omitted required traceability details. The same model
generated and graded answers, raw outputs were not retained, and there was only one
repetition. This is useful triage evidence, not a stable leaderboard result.

An upstream `oaieval` run still requires a chosen solver, API credentials, and may
incur cost. Once the contributor authorizes that run in an upstream checkout:

```bash
oaieval <solver> long-horizon-context-integrity
oaieval <solver> long-horizon-context-integrity-meta
```

Do not represent structural validation or the single preliminary run as broad
model-performance evidence.

## Publication boundary

All scenarios are fictional and hand-authored. They contain no raw user
conversations, credentials, personal data, provider request identifiers, private
design notes, or claims that a model's weights, native context window, or permanent
memory changed. The contribution specifies behavior and evaluation criteria only;
it does not disclose a private derivation or implementation recipe.

By contributing these files upstream, the contributor would agree to the upstream
MIT license terms and permit OpenAI to use the data for future service
improvements. Those legal and publication decisions are intentionally left for the
human contributor; this package has not been submitted externally.
