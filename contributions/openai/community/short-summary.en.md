Acheon is an open-source alpha for deterministic, auditable context governance in
long-running AI workflows. It applies lifecycle and scope gates, preserves protected
constraints and dependencies, keeps unresolved conflicts visible, and produces a
bounded context packet with reason codes for every selected or omitted record. The
public release includes 61 tests and a reproducible 240-case synthetic selection
benchmark. Those artifacts establish engineering contracts, not universal model
improvement. A proposed 24-sample OpenAI Evals contribution now covers eight
context-integrity failure families, with 16 labeled grader checks. One preliminary
GPT-5.6 Sol run recorded 23/24 automated passes and one human-reproduced traceability
omission; it does not measure Acheon's effect. I would value feedback on stronger
baselines and missing governance failure modes.

https://github.com/xingfengcan-tech/acheon-context
