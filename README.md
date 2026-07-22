# Acheon

**Auditable context orchestration for long-running AI workflows.**

Acheon turns a large, noisy history into a small, inspectable context packet for
the task at hand. It keeps active instructions, current decisions, linked evidence,
dependencies, and unresolved conflicts visible under a fixed estimated-token budget, then can
hand the packet to GPT-5.6 through the OpenAI Responses API.

The deterministic core runs fully offline. It does **not** modify model weights,
extend a provider context window, or claim permanent model memory.

## Why it exists

Long-running assistants usually face a bad choice: resend too much history, keep
only the latest turns, or retrieve a few semantically similar snippets. Each option
can drop an old constraint, resurrect an obsolete decision, mix projects, or hide
why a memory was selected.

Acheon adds an application-layer control plane:

- versioned SQLite records with explicit scope and lifecycle;
- protected instructions and current decisions under a hard estimated-unit budget;
- standard rank fusion, linked-record expansion, and diversity control;
- explicit supersession, revocation, expiry, and unresolved-conflict handling;
- selection and omission reason codes for every current record;
- hash-chained audit events and deterministic packet digests;
- an offline demo, reproducible baselines, ablations, and optional GPT-5.6 runtime.

## 60-second local demo

Requires Python 3.11 or newer.

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\acheon demo
```

macOS/Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/acheon demo
```

### Supported platforms

- Windows 10/11, macOS, and Linux;
- CPython 3.11 or newer;
- no GPU, model download, JavaScript build toolchain, or OpenAI credential is
  required for the offline demo and benchmark.

### Judge fast path (no source build)

Download the prebuilt `acheon_context-0.1.0-py3-none-any.whl` from the
[GitHub release](https://github.com/xingfengcan-tech/acheon-context/releases/tag/v0.1.0),
then run:

```powershell
python -m pip install .\acheon_context-0.1.0-py3-none-any.whl
acheon demo
acheon serve --port 8000
```

This path installs the ready-made wheel; judges do not need to clone, compile, or
rebuild the project. The source workflow below remains available for full
reproduction.

Start the local product demo:

```powershell
.venv\Scripts\acheon serve --port 8000
```

Then open `http://127.0.0.1:8000`. The offline path needs no account, key, network,
or model download. `/health` is available for readiness checks.

The HTTP demo is loopback-only and preview-only by default. A non-loopback bind
requires `ACHEON_HTTP_TOKEN`; live HTTP model calls also require the explicit
`--enable-live-http` flag. For a local Docker preview, bind the published port to
loopback and provide a bearer token:

```powershell
docker build -t acheon .
docker run --rm -e ACHEON_HTTP_TOKEN=replace-with-16-plus-random-characters `
  -p 127.0.0.1:8000:8000 acheon
```

Enter the same token under **Protected HTTP access** in the local page before using
POST actions. The page keeps it only in memory and does not add it to packets.

## GPT-5.6 path

Install the optional official client and set a key through your normal secure
environment workflow:

```powershell
.venv\Scripts\python -m pip install -e ".[openai]"
.venv\Scripts\acheon seed --namespace demo
.venv\Scripts\acheon ask "What constraints govern the release?" --namespace demo
```

The default is `gpt-5.6-sol`, configurable with `ACHEON_MODEL`. Acheon sends a
static developer policy separately from the compiled packet; stored history remains
untrusted user data. `store=False` is used so the controlled path does not depend on
hidden server-side conversation history.

A machine-readable receipt at [`artifacts/online/latest.json`](artifacts/online/latest.json)
records a single completed GPT-5.6 Sol call over the public seeded demo: returned
model, request/response IDs, usage, 11,530.3 ms latency, packet digest, selected IDs,
timestamp, and failures. It proves the live runtime path completed; it is not a
raw-versus-Acheon comparison or evidence of general answer-quality improvement.

A separate aggregate receipt at
[`artifacts/online/context-integrity-latest.json`](artifacts/online/context-integrity-latest.json)
records one GPT-5.6 Sol run over 24 project-specific synthetic context-integrity cases
primarily drafted and checked by Codex/model agents: 16/16 agreement with
provisional grader labels and 23/24
automated primary passes, with no invalid grader outputs. A targeted reproduction
check of `lhci-016` omitted two required traceability details. The labels and
reference answers have not yet received independent human review. This run did not
include an Acheon condition, used the same model for answers and grading, retained
no raw outputs, and had one repetition. It supports further evaluation of the
public Eval, not a claim that Acheon improved the model.

## Reproduce the evaluation

```powershell
.venv\Scripts\python -m unittest discover -s tests -v
$benchmarkCheck = Join-Path $env:TEMP "acheon-benchmark-check.json"
.venv\Scripts\python -m acheon.evals.run --output $benchmarkCheck
.venv\Scripts\python scripts/verify_openai_contribution.py
.venv\Scripts\python scripts/verify_release.py --compare-benchmark $benchmarkCheck
```

The offline suite compares Acheon with chronological-prefix, recent-tail, and
lexical top-k baselines under the same budget. It reports absolute metrics, paired
bootstrap intervals, ablations, determinism, failures, and scope. See
[evaluation methodology](docs/EVALUATION.md) and the generated artifact rather
than treating a demo as evidence.

On the checked-in 240-case synthetic selection workload, the full compiler records
1.000 Recall@budget, 0.857 precision, 0 forbidden inclusion, 0 budget violations,
and 1.000 determinism. Recent-tail records 0.167 recall; chronological-prefix and
lexical top-k each record 0.000. These are deliberately scoped engineering-contract
results from a disclosed generator, not downstream GPT-5.6 answer-quality results.

## Architecture

```text
typed records -> versioned SQLite store -> lifecycle/scope gate
              -> standard multi-rank candidate fusion
              -> protected lanes + linked-record closure + diversity
              -> strict estimated-unit context packet + reason trace + digest
              -> offline preview or GPT-5.6 Responses API
```

More detail: [architecture](docs/ARCHITECTURE.md),
[OpenAI integration](docs/OPENAI_INTEGRATION.md), and [security](SECURITY.md).

## OpenAI contribution package

The 2026 OpenAI Build Week challenge closed on July 21 at 5:00 PM PT, so this
repository no longer presents its prepared materials as an active prize submission.
The same quality standard now feeds three still-relevant contribution paths:

- an OpenAI Showcase application package;
- a sanitized OpenAI Evals proposal for long-horizon context integrity;
- a Developer Community technical post and optional sanitized API feedback cases.

The reviewed public materials and disclosure boundary live in
[`contributions/openai/`](contributions/openai/). Identity, rights, license,
data-sharing, agreement acceptance, and final external submission remain explicit
operator decisions. See the [impact audit](docs/IMPACT_AUDIT.md) for the conditional
go decision and the evidence required before stronger model-behavior claims.

Build the allowlisted, credential-free handoff archive after verification:

```powershell
.venv\Scripts\python scripts/build_release.py
.venv\Scripts\python scripts/verify_release.py --require-archive
```

Initialize any public repository from that ZIP. Do not mirror or `push --all` from
the development repository: Git history and refs are deliberately outside the
reviewed artifact and may contain unrelated local metadata.

## Evidence boundary

Offline synthetic evaluation can verify selection contracts, budget compliance,
isolation, determinism, and performance on the disclosed generator. It cannot prove
that the base model became more intelligent, that every real workload improves, or
that a model gained permanent memory. Those claims are outside this project.

## License

MIT. See [LICENSE](LICENSE) and [third-party notices](THIRD_PARTY_NOTICES.md).

---

中文简介：Acheon 是一个面向长时程 AI 工作流的应用层上下文治理编译器。
它在固定预算内选择并组织当前有效的指令、决策、证据和依赖，输出可审计的
选择轨迹；它不修改模型权重，也不扩大服务商提供的上下文窗口。
