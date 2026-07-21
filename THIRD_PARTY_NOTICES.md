# Third-party notices

Acheon does not vendor third-party source code, fonts, images, datasets, or model
outputs. Its runtime core uses the Python standard library.

Optional and development packages are installed from their normal package indexes
and remain governed by their own licenses:

| Package | Purpose | License reported by installed package metadata |
|---|---|---|
| `openai` | Optional Responses API client | Apache-2.0 |
| `pytest` | Development tests | MIT |
| `ruff` | Development linting | MIT |
| `pillow` | Regenerating repository-owned diagrams | MIT-CMU |
| `setuptools` | Build backend | MIT |

The optional OpenAI client installs transitive dependencies under their respective
licenses. Consult `uv.lock` and the installed distributions for the exact resolved
dependency set and complete license texts. These notices are informational and do
not replace those license terms.
