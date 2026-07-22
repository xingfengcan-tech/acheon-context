# Impact audit source notes

## Reporting job

- Question: Does Acheon have credible major long-term impact potential, and is the
  evidence strong enough to begin an OpenAI contribution package?
- Audience: technical reviewers and project owner.
- Decision: conditional go/no-go for public contribution work.
- As-of date: 2026-07-22, Asia/Shanghai.
- Baseline: the checked-in release evidence plus primary-source comparisons to
  published context and memory systems.

## Reproducible local sources

- `artifacts/benchmark/latest.json`: fixed-seed 240-case synthetic selection report.
- `artifacts/online/latest.json`: one completed GPT-5.6 Sol runtime receipt.
- `docs/FINAL_REPORT.md`: public engineering and claim boundary.
- `docs/EVALUATION.md`: benchmark definitions and methodology.
- `docs/LIMITATIONS.md`: known technical and evidence limitations.
- `docs/IMPACT_AUDIT.md`: reviewed synthesis and decision.
- `tests/`: 61 unit and integration contracts executed on 2026-07-22.

## Validation checks

- Re-ran all 61 tests: pass.
- Re-ran Ruff check and format check: pass.
- Ran `git diff --check`: pass.
- Re-ran release archive verification: pass with only documented operator fields.
- Parsed the checked-in benchmark and independently recomputed headline aggregates.
- Confirmed 240 unique case IDs across six named configurations.
- Confirmed every case shares six relevant and four forbidden labels, one dependency,
  one current fact, 64 history records, and a 640-unit budget.
- Confirmed the online receipt has no answer text and no comparative quality score.
- Ran one standalone 24-sample GPT-5.6 Sol context-integrity observation: agreement
  with provisional grader labels was 16/16, the primary automated result was 23/24
  with no invalid grader outputs, and an agent-reviewed targeted reproduction
  confirmed the one traceability-omission failure. Item-level independent human
  review remains pending. This run did not include an Acheon condition.
- Portable-report data validation and packaging passed. The bundled report tool had
  no headless Chromium, and the in-app browser could not access the isolated local
  preview, so visual and source-dialog interaction checks remain structural-only.

## Visualization decision and chart map

One categorical bar chart compares Recall@budget across the four systems because
the systems share the same synthetic cases, gold labels, renderer, and estimated-unit
budget. The chart starts at zero, uses one blue root with no redundant legend, and
places the workload and evidence boundary in its subtitle and adjacent narrative.

No chart compares test count, synthetic case count, smoke tests, or replications:
those are different units. No chart is used to imply downstream model quality. Exact
tables preserve precision, forbidden-inclusion rates, and claim-level limitations.

| Section | Question | Family | Fields | Supported claim |
|---|---|---|---|---|
| Synthetic benchmark | How does Recall@budget differ under one disclosed budget? | Categorical bar | system, recall | Acheon satisfies its declared generator more completely than three simple controls |

## Required structure mapping

- Title: `title` block.
- Technical summary: `summary` block plus evidence-status metric strip.
- Key findings with evidence: one benchmark bar plus benchmark and claim-status tables.
- Scope, data, and definitions: `scope` block.
- Methodology: `method` block.
- Limitations and robustness: `limitations` and `competitive_context` blocks.
- Recommended next steps: `next_steps` block.
- Further questions: `further_questions` block.
