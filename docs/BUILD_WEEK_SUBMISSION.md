# Build Week submission draft

## Category

Developer Tools

## Project name

Acheon

## Tagline

Auditable context orchestration for long-running AI workflows.

## Short description

Acheon compiles noisy project history into a strict estimated-token-budget context packet for
GPT-5.6. It preserves active constraints, current decisions, linked evidence, and
unresolved conflicts while excluding expired, revoked, superseded, and out-of-scope
records. Every selection and omission has a reason code, every packet has a stable
digest, and every mutation or compilation enters a tamper-evident local audit chain.

## The problem

Long-running coding and agent workflows accumulate more history than should be sent
on every turn. Recency windows forget early requirements. Raw keyword retrieval can
resurrect obsolete decisions or omit dependencies. Full history is expensive and
still becomes lossy once truncated. Developers rarely get an inspectable answer to
"why did the model see this memory?"

The primary users are developers and platform teams maintaining long-running coding
or agent workflows. A concrete failure is an early release constraint disappearing
from a recency window while a later, explicitly superseded deployment plan is
retrieved because it shares more query words.

## The solution

Acheon adds a deterministic application layer between project history and GPT-5.6.
Records are typed, scoped, versioned, and lifecycle-aware. Standard rank fusion and
diversity ranking generate candidates; protected lanes and required-link closure
assemble a bounded packet. A local web demo shows selected records, omissions,
budget use, and packet integrity before the optional OpenAI call.

## What makes it different

- The packet is inspectable before inference.
- Lifecycle and scope are hard gates, not soft similarity hints.
- Dependencies and unresolved conflicts stay visible.
- Offline behavior is deterministic and independently testable.
- Claims are tied to machine-readable baselines, ablations, and failure cases.

## How GPT-5.6 is used

GPT-5.6 Sol is the quality runtime for answering with the compiled packet. The
Responses API integration keeps dynamic history as untrusted user data, disables
stored response state for controlled runs, and records the provider-returned model
ID and usage in the runtime result. The application layer controls available
evidence; GPT-5.6 performs the final reasoning and response.

The checked-in [`artifacts/online/latest.json`](../artifacts/online/latest.json)
receipt records one completed GPT-5.6 Sol Responses API call over the public demo
records, including provider IDs, token usage, latency, packet digest, selected IDs,
timestamp, and an empty failure list. This validates the live path only; no
comparative answer-quality improvement is claimed.

## How Codex was used

Codex drove the public implementation: architecture, code, local product
experience, tests, benchmark generator, failure analysis, iteration, and release
materials. See `docs/CODEX_USAGE.md` and the submission's operator-provided
`/feedback` session ID.

## Technical stack

Python 3.11, SQLite, standard-library HTTP server, optional official OpenAI Python
client, deterministic local evaluation, and a zero-build static web interface.

## Judging-criteria mapping

- **Technological implementation:** versioned store, audit chain, strict estimated-unit budget,
  multi-rank retrieval, dependencies, ablations, and OpenAI integration.
- **Design:** one-command seed/demo, visual selection trace, offline fallback, and
  clear failure states.
- **Potential impact:** more reliable long-running coding, research, support, and
  operations agents with lower context waste and easier debugging.
- **Quality of idea:** treats context selection as a compiled, inspectable artifact
  rather than an opaque retrieval side effect.

On the disclosed 240-case synthetic selection-contract suite, Acheon records 1.000
Recall@budget, 0 forbidden inclusion, 0 budget violations, and 1.000 determinism.
These are selector-contract results, not evidence of general GPT-5.6 answer-quality
improvement.

## Required operator fields before submission

- Repository URL: `https://github.com/xingfengcan-tech/acheon-context`
- Demo URL or test path: prebuilt `v0.1.0` wheel plus local `acheon demo` / `acheon serve`
- Public/unlisted YouTube URL under three minutes: `PENDING`
- Codex `/feedback` session ID: `PENDING`
- Team members and legal eligibility: `PENDING`
- Live GPT-5.6 artifact: `artifacts/online/latest.json` (single-run smoke-test scope)

Official requirements: [Devpost challenge](https://openai.devpost.com/),
[rules](https://openai.devpost.com/rules), and
[FAQ](https://openai.devpost.com/details/faqs).
