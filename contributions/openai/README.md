# Acheon OpenAI contribution package

This directory is a reviewed, credential-free handoff for presenting Acheon's
observable context-governance behavior to OpenAI. It deliberately separates
reproducible engineering evidence from hypotheses about downstream model quality.

Unless explicitly stated otherwise, "reviewed" in this package means Codex/model-
agent and automated checks, not completed independent human item-level review.

The 2026 OpenAI Build Week challenge closed on July 21 at 5:00 PM PT. These files
therefore target contribution routes that remain useful after the prize deadline:

1. `showcase/` contains copy and field values for the OpenAI Showcase Gallery.
2. `evals/` contains a proposed, sanitized OpenAI Evals contribution using the
   repository's accepted data-only and model-graded formats.
3. `community/` contains a technical post that asks for methodological feedback
   without claiming an established model improvement.
4. `api-feedback/` contains synthetic cases and a protocol for optional,
   organization-approved API feedback.

`PUBLICATION_BOUNDARY.md` is authoritative for what may leave this repository.
`OFFICIAL_PATH_DECISION.md` records the chosen identity, copyright, license, and
agreement structure for the no-video routes.
`disclosure-manifest.json` records the evidence level and every operator-controlled
external action.

## Evidence status

- **Reproducible:** deterministic core behavior, 61 tests, release verification,
  and exact results on the disclosed 240-case synthetic selection workload.
- **Observed once:** one GPT-5.6 Sol Responses API smoke-test receipt, plus one
  24-sample standalone context-integrity run with a same-model grader that agreed
  with all 16 provisional labels (23/24 passing, one separately reproduced
  traceability omission). Item-level independent human review is pending.
- **Not established:** same-model answer-quality improvement, independent
  comparison attributable to Acheon, independent replication, real-workflow gains,
  or paradigm-level impact.

The project is suitable to share as a research alpha with credible high-impact
potential. It is not suitable to describe as an OpenAI-endorsed system, native
context-window expansion, permanent model memory, or a proven revolution.

## Local verification

From the repository root:

```powershell
python scripts/verify_openai_contribution.py
python -m unittest discover -s tests -v
python scripts/verify_release.py
```

No verification command submits a form, accepts a license or program agreement,
changes organization data-sharing settings, or publishes a community post.

## Operator gates

Before any external action, the project owner must personally confirm the relevant
identity, contact details, authorship and content rights, authority to accept the
applicable agreement, open-source data licensing, account identity, and final
submission. Organization-level API data sharing must remain a separate, explicit
choice; it is not required for the offline project or the eval contribution.
