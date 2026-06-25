# `panelforge_figures.safety` — package map

`safety/` is the **privacy-by-construction layer**. It resolves a single runtime
*data class* into a behaviour policy and exposes pure predicates that every
network-touching or state-persisting feature consults before acting. It is a
small, leaf-ish package: it imports only the standard library, so any gate site
(`data_bridge`, `caption`, `vision_input`, `provenance`, `status_dashboard`, the
MCP server, the CLI) can import it without pulling in `core`/`manifest`.

For the design rationale, read
[`docs/spec_data_class_safety.md`](../../../docs/spec_data_class_safety.md) and
[`docs/architecture_deep_dive.md`](../../../docs/architecture_deep_dive.md) §1.4,
§3.9, §4.1.

---

## The data-class model (`__init__.py`)

Three modes, set once and read globally:

| `DataClass` | LLM Pass-3 | Vision | Telemetry | Provenance hashes | Network plugins |
|---|---|---|---|---|---|
| `clinical` | disabled | disabled | off | redacted | disallowed |
| `research` *(default)* | opt-in | opt-in | opt-in | full | allowed |
| `public` | enabled | enabled | opt-in | full | allowed |

`research` is the default because clinical-by-default would silently break demo
users and public-by-default would silently expose regulated ones.

Policy cells are **documented strings, not booleans** (`enabled` / `opt_in` /
`disabled` / `off` / `redacted` / `full` / `allowed` / `disallowed`), because the
spec distinguishes *forced-OFF-no-override* (`disabled`/`off`) from
*default-OFF-but-opt-in-able* (`opt_in`) — a bool would collapse the two.

Key symbols: `DataClass` (StrEnum), `DataClassPolicy` (frozen dataclass),
`DataClassError`, the `_POLICIES` table, and the module-global
`_CURRENT_DATA_CLASS` (the single source of truth).

- `get_data_class()` / `set_data_class()` — read/write the current mode.
  `set_data_class` is reachable only via the CLI (`figures config set
  data_class`) or a future project-YAML loader — **never** an env var (spec §11).
- `get_policy()` — the resolved `DataClassPolicy`.
- `is_llm_allowed()`, `is_vision_allowed()`, `is_telemetry_allowed()`,
  `is_plugin_network_allowed()`, `should_redact_provenance_hashes()` — pure
  predicates of the resolved policy, so gate sites are unit-testable in isolation.
  For `opt_in`, LLM/vision treat the presence of `ANTHROPIC_API_KEY` as the
  explicit opt-in; telemetry stays OFF until a project flag enables it.

---

## PHI/PII column scanner (`phi_pattern_scanner.py`)

A **name-only** scanner: it inspects column *names*, never cell values. Names are
normalised (lowercased, non-alphanumerics → single space — see `_normalise`) so
`Patient-DOB`, `patient_dob`, and `PatientDOB` all match the same patterns.

Two risk tiers, higher wins on overlap:

- **High-risk** (`HIGH_RISK_PATTERNS`) — definite PHI/PII (`mrn`, `ssn`,
  `patient_dob`, `email`, `phone`, …).
- **Medium-risk** (`MEDIUM_RISK_PATTERNS`) — potential PHI when combined
  (`subject_id`, `zip`, `age_at_event`, `sex`, …).

Public API: `match_column(name)` returns `"high"`/`"medium"`/`None`;
`scan_columns_for_phi(columns)` returns at most one `PHIScanFinding` per column
(carrying the original name, tier, and the regex that triggered).

---

## How it fits the architecture

`safety/` sits beside `core/` in the layering: feature subsystems call *into* it,
never the reverse. It is the enforcement point for the **privacy-by-construction**
principle — a feature cannot reach the network or persist a hash without first
passing one of these predicates.
