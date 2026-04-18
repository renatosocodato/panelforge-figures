# Quickstart

## Install

```bash
pip install git+https://github.com/renatosocodato/panelforge-figures.git
```

For development (editable install with test / lint extras):

```bash
git clone https://github.com/renatosocodato/panelforge-figures.git
cd panelforge-figures
pip install -e .[dev]
```

Verify:

```bash
figures --version
figures stats
```

## First figure — declarative manifest

Create `figures.manifest.yaml`:

```yaml
version: 1
theme: pnas
palette: okabe_ito
figures:
  - id: fig_sobol
    size: single
    suptitle: "Figure 1 · Parameter sensitivity"
    panels:
      - id: A
        recipe: sensitivity_analysis.sobol_first_total_pair
        data:
          adapter: passthrough
          source:
            parameter_names: [k_on, k_off, V_max, Km]
            S1: [0.42, 0.05, 0.18, 0.08]
            ST: [0.52, 0.15, 0.28, 0.30]
export:
  formats: [pdf, png, svg]
  outdir: figures/outputs
```

Render:

```bash
figures validate figures.manifest.yaml
figures render figures.manifest.yaml
```

## First figure — from Python

```python
import matplotlib.pyplot as plt
from panelforge_figures.core import apply_base_style
from panelforge_figures.core.contract import get_recipe, ensure_all_imported

ensure_all_imported()
apply_base_style()

recipe = get_recipe("sensitivity_analysis.sobol_first_total_pair")
contract = recipe.contract(
    parameter_names=["k_on", "k_off", "V_max", "Km"],
    S1=[0.42, 0.05, 0.18, 0.08],
    ST=[0.52, 0.15, 0.28, 0.30],
)
fig, ax = plt.subplots(figsize=(5.2, 3.6))
recipe.render(contract, ax=ax)
fig.savefig("sobol.pdf")
```

## Agentic bootstrap (inside any manuscript repo)

1. `cd` into the manuscript repo.
2. Run `claude`.
3. Ask Claude to "use the panelforge-figures skill". It reads the catalog,
   surveys the repo, proposes figures with per-recipe justifications
   against alternatives in the same modality, writes
   `figures.manifest.yaml`, and runs the first render.
4. After bootstrap, re-renders are agent-free:

   ```bash
   figures render figures.manifest.yaml
   ```
