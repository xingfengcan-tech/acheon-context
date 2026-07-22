# Long-Horizon Context Integrity eval contribution package

This directory is a pre-submission staging package for the public
[`openai/evals`](https://github.com/openai/evals) registry. It evaluates an
observable model behavior: reconstructing the current, authorized, scoped, and
supportable answer from a long chronological record.

The package contains no custom Python eval class and performs no API calls. It uses
the existing `ModelBasedClassify` class, one declarative registry file, one
declarative model-graded rubric, 24 project-specific synthetic task samples primarily
drafted and checked by Codex/model agents, and 16 provisionally labeled
grader-validation candidates. No item-level independent human review has been
completed.

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
  answers with provisional `choice` labels to exercise the rubric.
- Each primary sample has chat-formatted `input`, an exhaustive `criteria` field,
  and a reference `ideal` answer for audit and spot checking.
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

On 2026-07-22, the final four files were copied into a local checkout of upstream
commit `8eac7a7de5215c907fbddc30efdaf316913eccdd`. Full Registry parsing succeeded,
both aliases resolved, Git LFS OIDs matched the LF-normalized hashes, and complete
`oaieval dummy` smoke runs traversed 24 primary plus 16 meta samples with exit code
zero. Dummy outputs are intentionally invalid and provide no model-performance
evidence. A real run with an upstream-supported model remains pending.

The upstream repository already defines the JSONL Git LFS attribute. After copying
and normalizing all four files to UTF-8 without BOM and LF line endings, verify the
existing attribute before committing:

```bash
git lfs install
git check-attr filter diff merge text -- evals/registry/data/long-horizon-context-integrity/*.jsonl
git add evals/registry/data/long-horizon-context-integrity \
  evals/registry/evals/long-horizon-context-integrity.yaml \
  evals/registry/modelgraded/long-horizon-context-integrity.yaml
git lfs ls-files -l
git diff --cached -- .gitattributes
```

Expected: both JSONL paths report `filter: lfs`, appear in `git lfs ls-files`, and
the staged `.gitattributes` diff is empty. Only add a new LFS rule if the upstream
attribute is actually absent.

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

The project-specific fictional scenarios were primarily drafted and checked by
Codex/model agents. Automated scans found no raw user conversations, credentials,
personal data, provider request identifiers, private design notes, or claims that a
model's weights, native context window, or permanent memory changed. Independent
human rights and privacy review is pending. The contribution specifies behavior
and evaluation criteria only; it does not disclose a private derivation or
implementation recipe.

By contributing these files upstream, the contributor would agree to the upstream
MIT license terms and permit OpenAI to use the data for future service
improvements. Those legal and publication decisions are intentionally left for the
human contributor; this package has not been submitted externally.

Before an upstream pull request, an independent human must review all 24 task
records, criteria, and reference answers plus all 16 candidate answers and
provisional labels. Until that receipt exists, the package must not claim human
authorship, human labeling, or completed human review.
