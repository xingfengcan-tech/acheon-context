# Release checklist

## Automated

- [x] Unit and integration tests pass.
- [x] Offline benchmark completes to a temporary receipt and its stable fields
      match `artifacts/benchmark/latest.json`.
- [x] Budget violations are zero.
- [x] Deterministic packet digest checks pass.
- [x] Audit chain verifies.
- [x] Release verifier passes.
- [x] Architecture diagrams are regenerated.
- [x] No credentials, databases, private conversations, paid payloads, internal
      research vocabulary, or Git metadata exist in the allowlisted release archive.

## Evidence review

- [x] README numbers match the machine-readable artifact.
- [x] Final report distinguishes contract, synthetic, and live evidence.
- [x] Failures are included, not only averages.
- [x] Live GPT-5.6 claims exist only if a real artifact records returned model ID,
      usage, timestamp, and failures.
- [x] The live artifact states its single-run scope and rejects comparative or
      general model-improvement claims.
- [x] No claim says model weights or the official context window changed.

## Historical Build Week operator record (closed)

These items are retained only as provenance for the closed 2026 Build Week route.
They are not requirements for the active Showcase, OpenAI Evals, or Developer
Community paths.

- [ ] Confirm every team member's eligibility under the official rules.
- [x] Publish the reviewed source repository publicly.
- [x] Initialize the submission repository from the allowlisted ZIP. Do not mirror or
      `push --all` from the development repository, whose excluded Git history/refs
      were not part of the public artifact review.
- [ ] If private, share with `testing@devpost.com` and
      `build-week-event@openai.com` before the deadline.
- [ ] Record and upload a narrated YouTube demo under three minutes; test it in an
      incognito window without login.
- [x] Record the current Codex primary task/session ID for the submission.
- [ ] Add repository, demo, and video URLs to the submission.
- [ ] Rights holder confirms all IP, licenses, names, screenshots, and sample data;
      an independent human reviews every proposed Eval item and provisional label.
- [ ] Submit before **2026-07-21 17:00 PDT / 2026-07-22 08:00 Asia/Shanghai**.

Official sources: [challenge](https://openai.devpost.com/),
[rules](https://openai.devpost.com/rules),
[latest deadline note](https://openai.devpost.com/updates/45371-tuesday-last-minute-tips).

## Current official paths — no YouTube required

- [x] Public repository is available on the default branch with passing CI.
- [x] Showcase project fields, repository URL, setup steps, public author, and cover
      URL are prepared.
- [ ] Rights holder supplies truthful legal first name, last name, and durable
      contact email for Showcase.
- [ ] Rights holder confirms content and cover rights and personally accepts the
      Showcase Program Agreement before final submission.
- [x] OpenAI Evals four-file contribution is structurally staged without custom
      executable eval code.
- [ ] An independent human reviews all 24 tasks, criteria, reference answers, all
      16 candidates, and every provisional label.
- [ ] Upstream Evals checkout passes LF/hash, Git LFS, registry, dummy-run, and
      supported-model checks.
- [ ] Rights holder personally accepts the Evals MIT, data-rights, Usage Policies,
      and limited-availability acknowledgments before opening the pull request.
- [x] Developer Community technical post and short summary are prepared.
- [ ] Account holder logs in, reviews the public draft, and creates the Community
      topic.

