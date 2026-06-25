---
name: Bug report
about: Report a defect in panelforge-figures (CLI, a recipe, the index, or the skill)
title: "[bug] "
labels: bug
assignees: ''
---

## What happened

<!-- A clear, concise description of the bug. -->

## What you expected

<!-- What you expected to happen instead. -->

## Reproduction

<!--
Minimal steps. If it involves a recipe, give the full name
(`<modality>.<recipe>`) and, if possible, the command:

    figures render figures.manifest.yaml
    figures show-recipe <modality>.<recipe>
-->

```
# commands / manifest / code that triggers it
```

## Environment

- panelforge-figures version: <!-- `figures --version` -->
- Python version: <!-- `python --version` -->
- OS:
- Installed extras (if any): <!-- e.g. .[dev,power,mcp] -->

## Logs / traceback

<!-- Paste the full error output. Run with `-v` for debug logging:  figures -v <command> -->

```
```

## Data-class context (if relevant)

<!--
panelforge gates LLM / vision / telemetry by data class. If the bug involves
those channels, state the project's data_class (clinical / research / public).
Do NOT paste any real clinical or personally identifying data.
-->
