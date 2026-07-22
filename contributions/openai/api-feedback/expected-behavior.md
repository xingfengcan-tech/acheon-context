# Sanitized API feedback protocol

Use these cases only in a dedicated OpenAI project whose data-sharing controls have
been explicitly selected by the organization owner. Do not enable general input and
output sharing merely to run this package.

`sanitized-cases.jsonl` contains eight fictional, public cases—one representative
case from each behavior family in the proposed OpenAI Evals package. It contains no
production conversation, credential, provider response, or private research note.

For each case:

1. send only the synthetic prompt contained in `sanitized-cases.jsonl`;
2. retain the exact model snapshot, parameters, timestamp, and response ID;
3. compare the answer with the case's public reference and rubric;
4. share a Playground thumbs-down only when the observed failure is reproducible;
5. explain the violated behavior in `feedback-notes.jsonl` without adding private
   theory, personal data, secrets, or proprietary material;
6. retain successful cases as well as failures to prevent cherry-picking.

The feedback package is intended to reveal model behavior failures, not Acheon's
selection policy. It should test constraint retention, current-state resolution,
conflict disclosure, dependency completeness, scope isolation, and treatment of
untrusted history.

Data sharing is an operator decision. The official control is available at:

https://platform.openai.com/settings/organization/data-controls/sharing
