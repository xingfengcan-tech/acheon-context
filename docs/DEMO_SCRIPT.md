# 2:40 demo script

The video must be under three minutes, visible on YouTube without login, and contain
spoken English audio.

## 0:00-0:20 — Problem

Show a long project history. Say:

> Long-running agents accumulate instructions, decisions, corrections, artifacts,
> and noise. Sending everything wastes context; keeping only recent or similar text
> can drop an old constraint or revive an obsolete decision.

## 0:20-0:45 — Baseline failure

Open the benchmark JSON or console comparison. Highlight one case where a recency baseline misses an
early requirement and one where lexical retrieval includes a replaced record.

> These baselines have no lifecycle or dependency model. They cannot explain why a
> record entered the prompt.

## 0:45-1:40 — Product

Run `acheon demo`, then `acheon serve --port 8000`. In the browser:

1. select the seeded developer project;
2. enter the release-readiness query;
3. set the estimated-token budget;
4. compile;
5. show the ordered sections that are present;
6. show selected and omitted reason codes;
7. point out the superseded record excluded from the packet;
8. show the packet digest and audit verification.

> Acheon treats context like a compiled artifact. The local selector is
> deterministic, strict estimated-budget, scoped, version-aware, and inspectable before a model
> call.

## 1:40-2:05 — GPT-5.6

Show the checked-in live receipt and the observed answer summary.

> GPT-5.6 Sol receives the compiled packet through the Responses API and performs the
> final reasoning. Dynamic history remains untrusted user data, controlled runs use
> no hidden prior response state, and the tool records the returned model ID and
> usage. The checked-in receipt proves this one public-demo call completed; it is
> not a general answer-quality comparison.

## 2:05-2:25 — Evidence

Show `artifacts/benchmark/latest.json` and the console summary.

> We compare against three equal-budget baselines and publish absolute results,
> paired intervals, ablations, deterministic checks, and every failure. This measures
> application-layer selection on a disclosed synthetic suite—not a change to model
> weights or the official context window.

## 2:25-2:40 — Codex and close

> Codex was the primary engineering collaborator across audit, architecture,
> implementation, adversarial tests, benchmark iteration, and release preparation.
> Acheon makes the model's available context smaller, safer, and explainable.

End on the project name, repository URL, and one-command demo.
