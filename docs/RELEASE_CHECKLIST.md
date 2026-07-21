# Release checklist

## Automated

- [x] Unit and integration tests pass.
- [x] Offline benchmark completes and writes `artifacts/benchmark/latest.json`.
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

## Manual / operator

- [ ] Confirm every team member's eligibility under the official rules.
- [ ] Decide public repository vs private judge-shared repository.
- [ ] Initialize the submission repository from the allowlisted ZIP. Do not mirror or
      `push --all` from the development repository, whose excluded Git history/refs
      were not part of the public artifact review.
- [ ] If private, share with `testing@devpost.com` and
      `build-week-event@openai.com` before the deadline.
- [ ] Record and upload a narrated YouTube demo under three minutes; test it in an
      incognito window without login.
- [ ] Add the correct Codex `/feedback` session ID.
- [ ] Add repository, demo, and video URLs to the submission.
- [ ] Review all IP, licenses, names, screenshots, voice, music, and sample data.
- [ ] Submit before **2026-07-21 17:00 PDT / 2026-07-22 08:00 Asia/Shanghai**.

Official sources: [challenge](https://openai.devpost.com/),
[rules](https://openai.devpost.com/rules),
[latest deadline note](https://openai.devpost.com/updates/45371-tuesday-last-minute-tips).
