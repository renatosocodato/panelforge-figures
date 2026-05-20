# Spec: Vision-Driven Recipe Selection + Iterative Refinement

**Status:** Draft (v2.0 roadmap, W5 swarm output)
**Owner:** TBD
**Target release:** v2.0.0
**Depends on:** Wave 3 intake pipeline (`manifest/intake.py`, `manifest/project_scan.py`), Wave 3 LLM helper (`manifest/data_bridge._llm_pass`), CLAUDE_CODE_AUTONOMOUS.md privacy disclosure (PR #55).

---

## TL;DR

Add two new modes to panelforge-figures:

1. **Vision-driven scan** — `figures profile scan --reference-figure example.png` sends a reference image to Claude (Anthropic vision endpoint) and receives an `IntakeAnswer` dict that pre-fills the same intake pipeline used by the text-based scanner. High-confidence (≥0.8) inferences auto-apply; low-confidence drops back to interactive ask.
2. **Iterative refinement** — after a first render, `figures refine fig.pdf "make y-axis log-scale"` sends the rendered PNG + the source recipe Python + the user's natural-language instruction to Claude, which returns a JSON-patch on the recipe contract (or a list of recipe-level alternative suggestions). The user confirms before re-render.

Both modes degrade gracefully when `ANTHROPIC_API_KEY` is missing and cache responses by image SHA-256 to bound cost.

---

## 1. Problem statement

Today's intake (v1.6.1) is text-only. The Wave-3 scanner reads `manuscript.tex`, `methods.md`, and CSV headers; the interactive intake walks 8 questions. This works when the user can articulate **what they want in words**. But a recurring pattern in collaborative science is:

> "Make a figure that looks like Figure 3 in this Nature paper. Here's a screenshot."

The user has the visual target in front of them but cannot easily map it onto the 8-question intake. They don't know whether the figure is a `coef_forest` or a `compartment_paired_delta_scatter`; they don't know whether the equivalence bands they see are TOST-derived or just shaded ranges. Vision can collapse the gap.

A second, related friction surfaces post-render: the first attempt is rarely the final figure. Today the user must re-edit the recipe Python by hand, recompile the manifest, and re-render. A vision-aware refinement loop — read the rendered PNG, read the source recipe, read the user's edit instruction, emit a structured patch — closes that loop in seconds rather than minutes.

This spec covers both: **vision-in** (initial recipe selection) and **vision-loop** (iterative refinement).

---

## 2. Vision input mode

### 2.1 CLI surface

```bash
figures profile scan --reference-figure path/to/example.png
```

The flag is additive to the existing `figures profile scan`. With `--reference-figure`, the scanner runs as today (text scan of `manuscript.{md,tex}`, `data/*.csv` headers, etc.) **and** invokes the vision pipeline against the supplied image. The two inference streams are merged at the `IntakeAnswer` level — see §3 below.

### 2.2 Prompt template

The vision call sends a single user-message with two content blocks: an `image` block (base64-encoded PNG/JPEG/PDF-page-1) and a `text` block with the structured prompt:

```
You are an expert in scientific figure conventions.

Analyse the attached figure. Identify, in JSON:
- family: one of {coef_forest, scatter_collapse, matrix, split_violin,
  paired_delta_scatter, kymograph, ridgeplot, ...}  (closed taxonomy
  pulled from recipes_index.json)
- visual_style: palette hint (slate / teal / coral / muted_neutral /
  high_contrast)
- markers: {forest_dots: bool, error_bars: bool, equivalence_bands: bool,
  significance_stars: bool, panel_labels: bool}
- layout: {n_panels: int, gridspec_like: bool}
- plausible_modalities: ranked list (max 3) drawn from
  {actin_microtubule_morphometry, biophysics_scaling, intravital_imaging,
  factorial_design_companion, cytoskeletal_morphometry_companion, ...}

For each top-level key, include a 0..1 confidence score that you self-rate.

Return ONLY valid JSON conforming to schemas/vision_inference.schema.json.
```

The closed taxonomy is loaded from `recipes_index.json` so the prompt template stays in sync with whatever new families ship in recipe packs. Hallucinated values outside the taxonomy are rejected on parse.

### 2.3 What Claude returns

```json
{
  "family": {"value": "coef_forest", "confidence": 0.92},
  "visual_style": {"value": "slate", "confidence": 0.71},
  "markers": {
    "forest_dots": {"value": true, "confidence": 0.98},
    "error_bars": {"value": true, "confidence": 0.95},
    "equivalence_bands": {"value": true, "confidence": 0.82},
    "significance_stars": {"value": false, "confidence": 0.66},
    "panel_labels": {"value": true, "confidence": 0.99}
  },
  "layout": {"n_panels": 1, "gridspec_like": false, "confidence": 0.88},
  "plausible_modalities": [
    {"value": "cytoskeletal_morphometry_companion", "confidence": 0.74},
    {"value": "actin_microtubule_morphometry", "confidence": 0.51},
    {"value": "biophysics_scaling", "confidence": 0.34}
  ]
}
```

---

## 3. Pre-fill mechanism

Vision-derived inferences feed the **same** `IntakeAnswer` pipeline that the existing text scanner emits to. The merge happens in a new helper:

```python
def merge_vision_into_intake(
    text_inferences: dict[str, IntakeAnswer],
    vision_inferences: dict[str, InferredAnswer],
) -> dict[str, IntakeAnswer]:
    ...
```

Rules:

- **Both sources agree** → keep the higher confidence, mark `source="text+vision"`.
- **Both sources disagree** → keep the higher confidence; if both ≥0.7, mark `source="conflict"` and force interactive ask regardless of confidence (the user resolves).
- **Vision-only inference** → if confidence ≥0.8, auto-fill with `[auto — vision]` annotation; if 0.7–0.8, auto-fill with `[auto — review]`; if <0.7, fall through to interactive ask.

The 0.8 threshold for vision-only auto-fill is **stricter** than the 0.7 used for text inferences, because vision hallucination has a higher prior than text-pattern hallucination — see §13.

### Worked mapping

A vision result of `family=coef_forest, equivalence_bands=true, plausible_modalities=[cytoskeletal_morphometry_companion@0.74]` maps to:

| Intake field | Inferred value | Confidence |
|---|---|---|
| `factorial_design` | `false` (forest layout = single-coefficient comparison) | 0.78 |
| `equivalence_claims` | `true` | 0.82 |
| `manuscript_anchor` | `EXAMPLE_ANCHOR` | 0.74 |
| `dynamics_needed` | `static` (no time axis seen) | 0.85 |
| `dimensionality` | `2D` | 0.99 |

`factorial_design` and `manuscript_anchor` land below the 0.8 vision-only auto-fill cutoff and drop to interactive ask. `equivalence_claims`, `dynamics_needed`, and `dimensionality` auto-fill.

---

## 4. Iterative refinement mode

### 4.1 CLI surface

```bash
figures refine <figure.pdf | recipe.py> "<natural-language edit>"
figures refine fig.pdf "make y-axis log-scale and add CI bands"
figures refine recipes/example_a/forest_v3.py "drop the bottom-3 markers by score"
figures vision-explain fig.pdf       # describes the figure, no edit
```

### 4.2 Two-pass execution

`figures refine` runs two LLM calls (or one combined call when token budget allows):

1. **Vision pass** — sends the rendered PNG (rasterised from PDF if needed) plus the user instruction. Claude returns a structured description of *what's in the figure now* and a candidate edit plan.
2. **Code pass** — sends the source recipe Python file plus the edit plan. Claude returns either:
   - a **JSON-patch on the contract** (RFC 6902-style) that the user can preview before re-render, or
   - a **recipe-level suggestion list** (e.g. "this edit needs a different family — try `compartment_paired_delta_scatter` instead of `forest_v3`").

### 4.3 User confirmation

Before re-render, `figures refine` always prints the proposed patch and waits for `Confirm patch? [Y/n]`. The patch is a strict subset of the contract's JSON-Schema, so it cannot mutate fields outside the contract surface.

### 4.4 Bounded iteration

`RefinementRequest.max_iterations` defaults to 3. If the user re-runs `figures refine` against the same figure four times in a row, the loop emits a warning suggesting either (a) starting from a fresh recipe selection or (b) hand-editing the recipe Python directly.

---

## 5. Worked examples

### Example A — vision-driven shortlist

```bash
$ figures profile scan --reference-figure nature_paper_figure_3.png
[scan] reading manuscript.md ............................... 4 signals
[scan] reading data/example_effects.csv headers ............ 12 columns
[vision] sending figure to Anthropic vision endpoint ....... 380 KB
[vision] family=coef_forest (conf=0.92)
[vision] markers: forest_dots, error_bars, equivalence_bands
[vision] visual_style=slate, n_panels=1
[merge] auto-filling 5 of 8 intake fields
[merge] interactive prompts needed for: factorial_design, manuscript_anchor, hard_filters

panelforge-figures intake — 3 of 8 questions remaining
[1/8] [auto — vision] equivalence_claims = true (conf=0.82)
[2/8] [auto — vision] dynamics_needed = static (conf=0.85)
...
[3/8] Is your project a factorial design? [y/N]: n
...

Top-1 result: actin_mt.compartment_paired_delta_scatter (score=0.84)
```

### Example B — refinement: log-scale Y axis

```bash
$ figures refine figures/forest_v3.pdf "make y-axis log-scale"
[vision] reading figures/forest_v3.pdf (page 1, 1.2 MB rasterised)
[vision] figure recognised as coef_forest with 8 markers
[code] reading recipes/example_a/forest_v3.py (98 LOC)
[code] proposed contract patch:
   {"y_log_scale": true}

Confirm patch? [Y/n]: y
[render] re-rendering forest_v3 with patch ...
[render] wrote figures/forest_v3.pdf  (delta: 14 ms)
```

### Example C — refinement that needs a CLI flag

```bash
$ figures refine figures/forest_v3.pdf "use only 6 markers, drop the bottom-3 by score"
[vision] figure recognised as coef_forest with 9 markers
[code] this edit is a top-N filter, not a contract field
[code] proposed change: invoke with `--top-n 6`

Confirm? [Y/n]: y
$ figures render figures.manifest.yaml --top-n 6
```

When the requested edit doesn't have a contract field, the refinement layer surfaces the equivalent CLI flag (or, if no flag exists, a recipe-level alternative).

---

## 6. API design

```python
# src/panelforge_figures/manifest/vision_input.py

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class InferredAnswer:
    """One vision-derived intake inference with self-rated confidence."""
    field_name: str
    value: object
    confidence: float                        # 0.0 .. 1.0
    source: Literal["vision"] = "vision"


def vision_scan_reference_figure(
    image_path: Path,
    *,
    confidence_threshold: float = 0.7,
    cache_dir: Path = Path("panelforge_workspace/vision_cache"),
) -> dict[str, InferredAnswer]:
    """Send `image_path` to the Anthropic vision endpoint, return the
    InferredAnswer dict keyed by intake field_name.

    Caches by SHA-256(image bytes) so repeat calls are free.

    Returns an empty dict if ANTHROPIC_API_KEY is missing or the
    `anthropic` package is not installed.
    """


@dataclass(frozen=True)
class RefinementRequest:
    target: Path                             # figure PDF/PNG to refine
    instruction: str                         # natural-language edit
    max_iterations: int = 3


@dataclass(frozen=True)
class RefinementOutcome:
    patch: dict[str, object] | None          # contract JSON-patch, or None
    cli_flag_suggestions: tuple[str, ...]    # e.g. ("--top-n 6",)
    recipe_alternatives: tuple[str, ...]     # full_names of better recipes
    rationale: str                           # human-readable explanation


def refine_figure(request: RefinementRequest) -> RefinementOutcome:
    """Run the two-pass refinement loop. Returns the proposed
    outcome — caller is responsible for prompting user confirmation
    and triggering re-render."""
```

---

## 7. CLI surface

```
figures profile scan --reference-figure <png>     # vision-augmented scan
figures refine <figure-or-recipe> "<instruction>" # iterative
figures vision-explain <figure>                   # describe, no edit
```

Each command warns about cost if `--quiet` is not set (see §10).

---

## 8. Privacy considerations

The reference image is sent to Anthropic. The disclosure block in `CLAUDE_CODE_AUTONOMOUS.md` (added in PR #55, currently covers **column-name** payloads only) must be **extended** to cover vision payloads.

Additions to the privacy block:

**What IS sent to Anthropic when vision modes are used:**

| Field | Example | Sourced from |
|---|---|---|
| Image bytes (base64-encoded) | the reference figure or rendered PNG | `--reference-figure` argument or `figures refine <pdf>` argument |
| Image SHA-256 (for cache key only, sent in metadata) | `9f86d081...` | computed locally |
| Recipe source code | the contents of `recipes/<modality>/<recipe>.py` | the recipe package |
| User's edit instruction (for `refine` only) | `"make y-axis log-scale"` | CLI argument |

**What is NEVER sent to Anthropic in vision modes:**

- The user's data files (CSV/Parquet contents are never read by vision modes — they read images and recipe Python only).
- The user's manuscript or methods text (covered by Pass-3 disclosure already).
- Project filesystem paths beyond the recipe module path.

**To opt out of vision modes**: simply omit the `--reference-figure` flag and the `figures refine` / `figures vision-explain` subcommands. Text-based scan and intake never invoke vision.

This must be a **separate disclosure block** in `CLAUDE_CODE_AUTONOMOUS.md` because users may opt into Pass-3 column mapping (low-entropy column names) but opt out of vision (high-entropy figure content) — the consent surface differs.

---

## 9. Cost considerations

Vision tokens are substantially more expensive than text tokens. Rough budget per call (Claude Sonnet 4.5 with vision, indicative pricing as of late 2025):

| Mode | Tokens (text) | Tokens (image) | Approx cost per call |
|---|---|---|---|
| `figures profile scan --reference-figure` | ~800 in + ~600 out | ~1500 (1 image) | ~$0.012 |
| `figures refine` (vision pass + code pass) | ~3500 in + ~800 out | ~1500 (1 image) | ~$0.025 |
| `figures vision-explain` | ~600 in + ~400 out | ~1500 (1 image) | ~$0.009 |

`figures vision-explain` and `figures refine` print a one-line cost warning before the API call:

```
[vision] sending 1.2 MB image to Anthropic; estimated cost ~$0.02. Continue? [Y/n]
```

Suppressed by `--quiet` or by setting `PANELFORGE_VISION_NO_PROMPT=1`. The estimate is computed from `len(base64-image) / 750` (a rough tokens-per-byte heuristic for image content blocks) plus a fixed text overhead.

---

## 10. Files to create / modify

### New

- **`src/panelforge_figures/manifest/vision_input.py`** (~250 LOC)
  Implements `vision_scan_reference_figure`, `refine_figure`, the JSON-patch validator, the SHA-256 cache, and the cost estimator. Lazy-imports `anthropic` mirroring the `data_bridge._llm_pass` pattern.

- **`schemas/vision_inference.schema.json`** (~80 LOC)
  Closed-taxonomy schema for vision inference output. Validated on parse to reject hallucinated families.

- **`tests/test_vision_input.py`** (~200 LOC)
  See §11.

### Edit

- **`src/panelforge_figures/manifest/data_bridge.py`** — extend the Pass-3 LLM helper to accept image content blocks (currently text-only). The lazy-import pattern is reused. Refactor: extract a private `_anthropic_client_factory` so both `data_bridge` and `vision_input` share retry/error semantics.

- **`src/panelforge_figures/cli.py`** — add `refine` and `vision-explain` subcommands; extend `profile scan` with the `--reference-figure` flag; add the cost-warning prompt.

- **`src/panelforge_figures/manifest/intake.py`** — accept `InferredAnswer` (the vision shape) alongside the existing `IntakeAnswer`. Add `merge_vision_into_intake` helper.

- **`CLAUDE_CODE_AUTONOMOUS.md`** — extend the privacy disclosure block with the vision-payload section in §8.

- **`pyproject.toml`** — bump the `claude-autonomous` extra to require `anthropic >= 0.40` (the version that supports image content blocks reliably) and add `Pillow` for PDF→PNG rasterisation.

---

## 11. Test surface

`tests/test_vision_input.py` covers:

1. **Mocked vision response → correct InferredAnswer dict** — patch `anthropic.Anthropic.messages.create` to return a canned JSON; assert that the parsed `InferredAnswer` map has the right field names, values, and confidences.
2. **Confidence threshold filtering** — with `confidence_threshold=0.8` and a mock that returns `{family: 0.75}`, assert that `family` is dropped from the returned map.
3. **Hallucination guard** — mock returns a `family` value not in the closed taxonomy; assert that the parser rejects it cleanly (returns `{}`, logs a warning).
4. **SHA-256 cache hit** — call twice with the same image bytes; assert that the second call does not invoke `messages.create`.
5. **Graceful degradation** — unset `ANTHROPIC_API_KEY`; call returns `{}` without raising.
6. **Refinement: valid contract patch** — given a coef_forest recipe and an instruction `"make y log-scale"`, assert that the returned patch has `{"y_log_scale": True}` and that the patch passes Pydantic validation against the recipe contract.
7. **Refinement: CLI-flag suggestion** — given an instruction `"only 6 markers"` for which no contract field exists, assert that `cli_flag_suggestions` contains `"--top-n 6"`.
8. **Intake integration** — vision output + a stub text-scan output both feed `merge_vision_into_intake`; assert that conflicting high-confidence answers force interactive ask.

Test fixtures live in `tests/fixtures/vision/` and include three small reference PNGs (one coef_forest, one matrix, one split_violin) plus three canned response JSONs.

---

## 12. Risks + mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Vision hallucination — Claude says "coef_forest" for a heatmap | Medium | Strict 0.8 cutoff for auto-fill; closed-taxonomy schema rejection; conflicting text+vision answers force interactive ask. |
| API rate limits / cost runaway | Low | SHA-256 cache (free repeat calls); per-call cost warning; `PANELFORGE_VISION_BUDGET_USD` env var that hard-stops when exceeded. |
| Privacy: the figure may contain unpublished data | Medium | Explicit opt-in (separate flag); disclosure block extended; never auto-invoked. The user must type `--reference-figure` or `figures refine`. |
| PDF→PNG rasterisation fails (e.g. encrypted PDF) | Low | Pillow + `pdf2image` fallback; if both fail, surface the original error and fall through to text-only scan. |
| Refinement loop diverges (user iterates 5+ times without converging) | Medium | `max_iterations=3` cap; warning to switch to manual edit. |
| Closed-taxonomy drift — new family added to recipes_index.json but not to the prompt template | Medium | Generate the taxonomy section of the prompt at runtime from `recipes_index.json`'s `families` field; smoke test asserts coverage. |

---

## 13. Acceptance criteria

A v2.0.0 release ships vision input only when **all** of the following hold:

1. The example image (committed at `tests/fixtures/vision/example_paired_delta.png`) produces a top-1 recipe drawn from the `cytoskeletal_morphometry_companion` pack with score ≥ 0.7.
2. Refinement of a rendered coef_forest with `"make y log-scale"` returns a contract patch `{"y_log_scale": true}` that passes contract validation and yields a re-rendered PDF differing from the original.
3. The vision pipeline returns `{}` (no exceptions) when `ANTHROPIC_API_KEY` is unset; the rest of the flow continues to work.
4. Calling `vision_scan_reference_figure` twice with the same image makes exactly **one** API call (cache hit on the second).
5. The privacy disclosure in `CLAUDE_CODE_AUTONOMOUS.md` contains a dedicated "Vision payloads" subsection that explicitly lists: image bytes, recipe source code, edit instruction.
6. `figures vision-explain` always prompts before the API call (unless `--quiet`).
7. `tests/test_vision_input.py` covers all eight test cases in §11 and has ≥ 95% line coverage on `vision_input.py`.

---

## 14. Out of scope (deferred)

- **Text → figure (the inverse problem).** Generating figures from natural-language descriptions without a reference image. Defer to a later wave; intake + scoring already covers the text path.
- **Multi-image input.** Comparing two reference figures side-by-side ("make it look like A but with the colours of B"). Defer; single-image input covers the dominant use case.
- **Sketch-to-recipe.** Hand-drawn / whiteboard input. Different OCR + structure-extraction problem; defer.
- **Auto-evaluation of refinement results.** Have Claude verify "does the re-rendered PDF actually match the user's instruction?" Useful but a self-licking-cone risk; defer until v2.1.
- **Batch refinement.** `figures refine --batch instructions.yaml` to apply the same edit across N figures. Defer until single-figure refinement stabilises.

---

## 15. Open questions (flagged for review)

- **Vision model selection.** Spec assumes Claude Sonnet 4.5 with vision. Should we make the model configurable (`PANELFORGE_VISION_MODEL` env var)? Probably yes for future-proofing, but defaults must be locked.
- **Caching invalidation.** SHA-256 cache never expires. Should we add a TTL (e.g. 30 days) to force re-evaluation when the prompt template changes? Recommend: include the prompt-template hash in the cache key.
- **`figures vision-explain` output format.** Markdown? JSON? Plain text? Spec leaves this open. Recommend: markdown by default, `--json` flag for scripting.
- **Cost-warning threshold.** Should the prompt fire only when estimated cost exceeds some threshold (e.g. $0.05)? This lets `figures profile scan --reference-figure` proceed silently for cheap calls. Spec assumes always-prompt; flag for review.

---

## Reference paths

- `src/panelforge_figures/manifest/vision_input.py` — new module (this spec)
- `src/panelforge_figures/manifest/intake.py` — `InferredAnswer` consumer
- `src/panelforge_figures/manifest/data_bridge.py` — Pass-3 LLM helper, shared client factory
- `src/panelforge_figures/cli.py` — `figures refine`, `figures vision-explain`, `--reference-figure`
- `CLAUDE_CODE_AUTONOMOUS.md` — privacy disclosure (extended in this spec)
- `schemas/vision_inference.schema.json` — closed-taxonomy schema
- `tests/test_vision_input.py` — coverage matrix per §11
- `tests/fixtures/vision/` — reference PNGs + canned response JSONs
