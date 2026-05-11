"""Reporting checklists — Elevation 12 (v3.6.0).

Four standardised reporting checklists, ready to attach to a manuscript
submission:

* **ARRIVE 2.0** (10 essential items) — animal research.
* **CONSORT 2010** (25 items) — randomised controlled trials.
* **STARD 2015** (30 items) — diagnostic accuracy studies.
* **MIQE** (40+ items) — qPCR experiments.

For each item the auto-classifier (:func:`auto_classify_item`) inspects:

* the manuscript text (if a path is supplied)
* the recipe registry's ``StatisticalContract`` (sample sizes,
  randomisation seeds, blinding flags)
* ``panelforge.project.yaml`` (species/strain/sex blocks for ARRIVE)
* ``panelforge_workspace/figures/*.provenance.json`` (randomisation
  seeds, data SHAs)

and returns ``(status, evidence, location_hint)``.  Anything the
classifier can't decide is left as ``unknown`` so the author is forced
to consciously mark each item before submission — we never silently
mark items as ``present``.

See ``docs/spec_reporting_checklists.md`` for the full per-item
classifier rules (forthcoming).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

__all__ = [
    "ARRIVE_2_0_ITEMS",
    "CONSORT_2010_ITEMS",
    "Checklist",
    "ChecklistError",
    "ChecklistItem",
    "ChecklistItemStatus",
    "ChecklistKind",
    "MIQE_ITEMS",
    "STARD_2015_ITEMS",
    "auto_classify_item",
    "generate_arrive_checklist",
    "generate_consort_checklist",
    "generate_miqe_checklist",
    "generate_stard_checklist",
    "render_checklist_latex",
    "render_checklist_markdown",
]


# --------------------------------------------------------------------------- #
# Enums + dataclasses                                                         #
# --------------------------------------------------------------------------- #


class ChecklistKind(StrEnum):
    arrive = "ARRIVE 2.0"
    consort = "CONSORT 2010"
    stard = "STARD 2015"
    miqe = "MIQE"


class ChecklistItemStatus(StrEnum):
    present = "present"
    absent = "absent"
    not_applicable = "n/a"
    unknown = "unknown"


@dataclass(frozen=True)
class ChecklistItem:
    """One row of a reporting checklist."""

    item_id: str
    section: str
    description: str
    status: ChecklistItemStatus = ChecklistItemStatus.unknown
    evidence: str = ""
    location_hint: str = ""


@dataclass(frozen=True)
class Checklist:
    """A fully-populated reporting checklist."""

    kind: ChecklistKind
    items: tuple[ChecklistItem, ...]
    n_present: int
    n_absent: int
    n_not_applicable: int
    n_unknown: int
    pass_threshold: float = 0.85


class ChecklistError(RuntimeError):
    """Raised on bad project root, unreadable manuscript, etc."""


# --------------------------------------------------------------------------- #
# ARRIVE 2.0 — 10 essential items                                             #
# --------------------------------------------------------------------------- #


ARRIVE_2_0_ITEMS: tuple[tuple[str, str, str], ...] = (
    (
        "ARRIVE-1a",
        "Study design",
        "Groups being compared, including control groups; whether and "
        "how groups were randomised; experimental unit.",
    ),
    (
        "ARRIVE-2a",
        "Sample size",
        "Sample size for each experimental group; how the sample size "
        "was decided (including any a priori sample-size calculation).",
    ),
    (
        "ARRIVE-3a",
        "Inclusion and exclusion criteria",
        "Criteria used for including and excluding animals (or "
        "experimental units) during the experiment, and data points "
        "during the analysis.",
    ),
    (
        "ARRIVE-4a",
        "Randomisation",
        "Strategy used to randomise animals to experimental groups, "
        "minimise potential confounders (e.g. order of treatments).",
    ),
    (
        "ARRIVE-5a",
        "Blinding",
        "Whether the investigators were blinded to group allocation "
        "during the experiment and/or when assessing the outcome.",
    ),
    (
        "ARRIVE-6a",
        "Outcome measures",
        "All outcome measures assessed; which were pre-specified as "
        "primary or secondary; how/when they were assessed.",
    ),
    (
        "ARRIVE-7a",
        "Statistical methods",
        "Statistical methods used for each analysis; the experimental "
        "unit analysed; software and any specific routines.",
    ),
    (
        "ARRIVE-8a",
        "Experimental animals",
        "Species, strain, sex, age, weight at start of experiment; "
        "source; genetic modifications; health/immune status.",
    ),
    (
        "ARRIVE-9a",
        "Experimental procedures",
        "For each experimental group (including controls): what was "
        "done, how, when, where, by whom, and why; humane endpoints; "
        "pain relief; specific protocols/SOPs.",
    ),
    (
        "ARRIVE-10a",
        "Results",
        "Number of analysed experimental units; descriptive statistics "
        "(mean / median / variability / range); effect sizes and "
        "confidence intervals.",
    ),
)


# --------------------------------------------------------------------------- #
# CONSORT 2010 — 25 items                                                     #
# --------------------------------------------------------------------------- #


CONSORT_2010_ITEMS: tuple[tuple[str, str, str], ...] = (
    (
        "CONSORT-1a",
        "Title and abstract",
        "Identification as a randomised trial in the title.",
    ),
    (
        "CONSORT-1b",
        "Title and abstract",
        "Structured summary of trial design, methods, results, and "
        "conclusions (see CONSORT extension for abstracts).",
    ),
    (
        "CONSORT-2a",
        "Introduction",
        "Scientific background and explanation of rationale.",
    ),
    (
        "CONSORT-2b",
        "Introduction",
        "Specific objectives or hypotheses.",
    ),
    (
        "CONSORT-3a",
        "Methods: trial design",
        "Description of trial design (parallel, factorial, …) including "
        "allocation ratio.",
    ),
    (
        "CONSORT-3b",
        "Methods: trial design",
        "Important changes to methods after trial commencement (e.g. "
        "eligibility criteria), with reasons.",
    ),
    (
        "CONSORT-4a",
        "Methods: participants",
        "Eligibility criteria for participants.",
    ),
    (
        "CONSORT-4b",
        "Methods: participants",
        "Settings and locations where the data were collected.",
    ),
    (
        "CONSORT-5",
        "Methods: interventions",
        "Interventions for each group with sufficient detail to allow "
        "replication, including how and when they were actually "
        "administered.",
    ),
    (
        "CONSORT-6a",
        "Methods: outcomes",
        "Completely defined pre-specified primary and secondary outcome "
        "measures, including how and when they were assessed.",
    ),
    (
        "CONSORT-6b",
        "Methods: outcomes",
        "Any changes to trial outcomes after the trial commenced, with "
        "reasons.",
    ),
    (
        "CONSORT-7a",
        "Methods: sample size",
        "How sample size was determined.",
    ),
    (
        "CONSORT-7b",
        "Methods: sample size",
        "When applicable, explanation of any interim analyses and "
        "stopping guidelines.",
    ),
    (
        "CONSORT-8a",
        "Methods: randomisation — sequence generation",
        "Method used to generate the random allocation sequence.",
    ),
    (
        "CONSORT-8b",
        "Methods: randomisation — sequence generation",
        "Type of randomisation; details of any restriction (such as "
        "blocking and block size).",
    ),
    (
        "CONSORT-9",
        "Methods: randomisation — allocation concealment",
        "Mechanism used to implement the random allocation sequence "
        "(such as sequentially numbered containers), describing any "
        "steps taken to conceal the sequence until interventions were "
        "assigned.",
    ),
    (
        "CONSORT-10",
        "Methods: randomisation — implementation",
        "Who generated the random allocation sequence, who enrolled "
        "participants, and who assigned participants to interventions.",
    ),
    (
        "CONSORT-11a",
        "Methods: blinding",
        "If done, who was blinded after assignment to interventions "
        "(for example, participants, care providers, those assessing "
        "outcomes) and how.",
    ),
    (
        "CONSORT-11b",
        "Methods: blinding",
        "If relevant, description of the similarity of interventions.",
    ),
    (
        "CONSORT-12a",
        "Methods: statistical methods",
        "Statistical methods used to compare groups for primary and "
        "secondary outcomes.",
    ),
    (
        "CONSORT-12b",
        "Methods: statistical methods",
        "Methods for additional analyses, such as subgroup analyses and "
        "adjusted analyses.",
    ),
    (
        "CONSORT-13a",
        "Results: participant flow",
        "For each group, the numbers of participants who were randomly "
        "assigned, received intended treatment, and were analysed for "
        "the primary outcome.",
    ),
    (
        "CONSORT-13b",
        "Results: participant flow",
        "For each group, losses and exclusions after randomisation, "
        "together with reasons.",
    ),
    (
        "CONSORT-14a",
        "Results: recruitment",
        "Dates defining the periods of recruitment and follow-up.",
    ),
    (
        "CONSORT-14b",
        "Results: recruitment",
        "Why the trial ended or was stopped.",
    ),
)


# --------------------------------------------------------------------------- #
# STARD 2015 — 30 items                                                       #
# --------------------------------------------------------------------------- #


STARD_2015_ITEMS: tuple[tuple[str, str, str], ...] = (
    (
        "STARD-1",
        "Title or abstract",
        "Identification as a study of diagnostic accuracy using at "
        "least one measure of accuracy (such as sensitivity, "
        "specificity, predictive values, or AUC).",
    ),
    (
        "STARD-2",
        "Abstract",
        "Structured summary of study design, methods, results, and "
        "conclusions (for specific guidance, see STARD for Abstracts).",
    ),
    (
        "STARD-3",
        "Introduction",
        "Scientific and clinical background, including the intended "
        "use and clinical role of the index test.",
    ),
    (
        "STARD-4",
        "Introduction",
        "Study objectives and hypotheses.",
    ),
    (
        "STARD-5",
        "Methods: study design",
        "Whether data collection was planned before the index test and "
        "reference standard were performed (prospective study) or "
        "after (retrospective study).",
    ),
    (
        "STARD-6",
        "Methods: participants",
        "Eligibility criteria.",
    ),
    (
        "STARD-7",
        "Methods: participants",
        "On what basis potentially eligible participants were "
        "identified (such as symptoms, results from previous tests, "
        "inclusion in a registry).",
    ),
    (
        "STARD-8",
        "Methods: participants",
        "Where and when potentially eligible participants were "
        "identified (setting, location, dates).",
    ),
    (
        "STARD-9",
        "Methods: participants",
        "Whether participants formed a consecutive, random, or "
        "convenience series.",
    ),
    (
        "STARD-10a",
        "Methods: test methods",
        "Index test, in sufficient detail to allow replication.",
    ),
    (
        "STARD-10b",
        "Methods: test methods",
        "Reference standard, in sufficient detail to allow replication.",
    ),
    (
        "STARD-11",
        "Methods: test methods",
        "Rationale for choosing the reference standard (if alternatives "
        "exist).",
    ),
    (
        "STARD-12a",
        "Methods: test methods",
        "Definition of and rationale for test positivity cut-offs or "
        "result categories of the index test, distinguishing pre-"
        "specified from exploratory.",
    ),
    (
        "STARD-12b",
        "Methods: test methods",
        "Definition of and rationale for test positivity cut-offs or "
        "result categories of the reference standard, distinguishing "
        "pre-specified from exploratory.",
    ),
    (
        "STARD-13a",
        "Methods: test methods",
        "Whether clinical information and reference-standard results "
        "were available to the performers/readers of the index test.",
    ),
    (
        "STARD-13b",
        "Methods: test methods",
        "Whether clinical information and index-test results were "
        "available to the assessors of the reference standard.",
    ),
    (
        "STARD-14",
        "Methods: analysis",
        "Methods for estimating or comparing measures of diagnostic "
        "accuracy.",
    ),
    (
        "STARD-15",
        "Methods: analysis",
        "How indeterminate index-test or reference-standard results "
        "were handled.",
    ),
    (
        "STARD-16",
        "Methods: analysis",
        "How missing data on the index test and reference standard "
        "were handled.",
    ),
    (
        "STARD-17",
        "Methods: analysis",
        "Any analyses of variability in diagnostic accuracy, "
        "distinguishing pre-specified from exploratory.",
    ),
    (
        "STARD-18",
        "Methods: analysis",
        "Intended sample size and how it was determined.",
    ),
    (
        "STARD-19",
        "Results: participants",
        "Flow of participants, using a diagram.",
    ),
    (
        "STARD-20",
        "Results: participants",
        "Baseline demographic and clinical characteristics of "
        "participants.",
    ),
    (
        "STARD-21a",
        "Results: participants",
        "Distribution of severity of disease (define criteria) in "
        "those with the target condition.",
    ),
    (
        "STARD-21b",
        "Results: participants",
        "Distribution of alternative diagnoses (define criteria) in "
        "those without the target condition.",
    ),
    (
        "STARD-22",
        "Results: participants",
        "Time interval and any clinical interventions between index "
        "test and reference standard.",
    ),
    (
        "STARD-23",
        "Results: test results",
        "Cross tabulation of the index-test results (or their "
        "distribution) by the results of the reference standard.",
    ),
    (
        "STARD-24",
        "Results: test results",
        "Estimates of diagnostic accuracy and their precision (such as "
        "95% confidence intervals).",
    ),
    (
        "STARD-25",
        "Results: test results",
        "Any adverse events from performing the index test or the "
        "reference standard.",
    ),
    (
        "STARD-26",
        "Discussion",
        "Study limitations, including sources of potential bias, "
        "statistical uncertainty, and generalisability.",
    ),
)


# --------------------------------------------------------------------------- #
# MIQE — 40+ items                                                            #
# --------------------------------------------------------------------------- #


MIQE_ITEMS: tuple[tuple[str, str, str], ...] = (
    (
        "MIQE-1",
        "Experimental design",
        "Definition of experimental and control groups.",
    ),
    (
        "MIQE-2",
        "Experimental design",
        "Number within each group.",
    ),
    (
        "MIQE-3",
        "Experimental design",
        "Assay carried out by core laboratory or investigator's "
        "laboratory.",
    ),
    (
        "MIQE-4",
        "Experimental design",
        "Acknowledgement of authors' contributions.",
    ),
    (
        "MIQE-5",
        "Sample",
        "Description (species, tissue type, processing method).",
    ),
    (
        "MIQE-6",
        "Sample",
        "Volume / mass of sample processed.",
    ),
    (
        "MIQE-7",
        "Sample",
        "Microdissection or macrodissection.",
    ),
    (
        "MIQE-8",
        "Sample",
        "Processing procedure / preservation.",
    ),
    (
        "MIQE-9",
        "Sample",
        "If frozen — how and how quickly?",
    ),
    (
        "MIQE-10",
        "Sample",
        "If fixed — with what, how quickly?",
    ),
    (
        "MIQE-11",
        "Sample",
        "Sample storage conditions and duration (especially for FFPE "
        "samples).",
    ),
    (
        "MIQE-12",
        "Nucleic acid extraction",
        "Procedure and/or instrumentation; commercial kit and "
        "reference; details of any modifications.",
    ),
    (
        "MIQE-13",
        "Nucleic acid extraction",
        "Source of additional reagents used.",
    ),
    (
        "MIQE-14",
        "Nucleic acid extraction",
        "Details of DNase or RNase treatment.",
    ),
    (
        "MIQE-15",
        "Nucleic acid extraction",
        "Contamination assessment (DNA or RNA).",
    ),
    (
        "MIQE-16",
        "Nucleic acid extraction",
        "Nucleic-acid quantification; instrument and method; purity "
        "(A260/A280); yield.",
    ),
    (
        "MIQE-17",
        "Nucleic acid extraction",
        "RNA integrity: method/instrument; RIN/RQI or Cq of "
        "3'/5' transcripts; electrophoresis traces; inhibition "
        "testing (Cq dilutions, spike-in or other).",
    ),
    (
        "MIQE-18",
        "Reverse transcription",
        "Complete reaction conditions; amount of RNA and reaction "
        "volume; priming oligonucleotide (if using gene-specific) and "
        "concentration; reverse transcriptase and concentration; "
        "temperature and time; manufacturer of reagents and catalog "
        "numbers; Cq with and without RT.",
    ),
    (
        "MIQE-19",
        "qPCR target information",
        "Gene symbol; sequence accession number; location of amplicon; "
        "amplicon length.",
    ),
    (
        "MIQE-20",
        "qPCR target information",
        "In silico specificity screen (BLAST etc.); pseudogenes, "
        "retropseudogenes or other homologs.",
    ),
    (
        "MIQE-21",
        "qPCR target information",
        "Sequence alignment; secondary structure analysis of amplicon; "
        "location of each primer by exon or intron (if applicable); "
        "what splice variants are targeted.",
    ),
    (
        "MIQE-22",
        "qPCR oligonucleotides",
        "Primer sequences.",
    ),
    (
        "MIQE-23",
        "qPCR oligonucleotides",
        "RTPrimerDB Identification Number.",
    ),
    (
        "MIQE-24",
        "qPCR oligonucleotides",
        "Probe sequences (donate probe sequences to public databases).",
    ),
    (
        "MIQE-25",
        "qPCR oligonucleotides",
        "Location and identity of any modifications.",
    ),
    (
        "MIQE-26",
        "qPCR oligonucleotides",
        "Manufacturer of oligonucleotides; purification method.",
    ),
    (
        "MIQE-27",
        "qPCR protocol",
        "Complete reaction conditions; reaction volume and amount of "
        "cDNA/DNA; primer, probe, Mg2+ and dNTP concentrations; "
        "polymerase identity and concentration; buffer/kit identity "
        "and manufacturer; exact chemical constitution of the buffer; "
        "additives (SYBR Green I, DMSO, etc.).",
    ),
    (
        "MIQE-28",
        "qPCR protocol",
        "Manufacturer of plates/tubes and catalog number.",
    ),
    (
        "MIQE-29",
        "qPCR protocol",
        "Complete thermocycling parameters.",
    ),
    (
        "MIQE-30",
        "qPCR protocol",
        "Reaction setup (manual/robotic).",
    ),
    (
        "MIQE-31",
        "qPCR protocol",
        "Manufacturer of qPCR instrument.",
    ),
    (
        "MIQE-32",
        "qPCR validation",
        "Evidence of optimisation (gradients).",
    ),
    (
        "MIQE-33",
        "qPCR validation",
        "Specificity (gel, sequence, melt, or digest).",
    ),
    (
        "MIQE-34",
        "qPCR validation",
        "For SYBR Green I, Cq of the NTC.",
    ),
    (
        "MIQE-35",
        "qPCR validation",
        "Standard curves with slope and y-intercept.",
    ),
    (
        "MIQE-36",
        "qPCR validation",
        "PCR efficiency calculated from slope.",
    ),
    (
        "MIQE-37",
        "qPCR validation",
        "Confidence interval for PCR efficiency or standard error.",
    ),
    (
        "MIQE-38",
        "qPCR validation",
        "r2 of standard curve.",
    ),
    (
        "MIQE-39",
        "qPCR validation",
        "Linear dynamic range.",
    ),
    (
        "MIQE-40",
        "qPCR validation",
        "Cq variation at lower limit.",
    ),
    (
        "MIQE-41",
        "qPCR validation",
        "Confidence intervals throughout range.",
    ),
    (
        "MIQE-42",
        "qPCR validation",
        "Evidence for limit of detection.",
    ),
    (
        "MIQE-43",
        "qPCR validation",
        "If multiplex, efficiency and LOD of each assay.",
    ),
    (
        "MIQE-44",
        "Data analysis",
        "qPCR analysis program (source, version).",
    ),
    (
        "MIQE-45",
        "Data analysis",
        "Method of Cq determination.",
    ),
    (
        "MIQE-46",
        "Data analysis",
        "Outlier identification and disposition.",
    ),
    (
        "MIQE-47",
        "Data analysis",
        "Results of NTCs.",
    ),
    (
        "MIQE-48",
        "Data analysis",
        "Justification of number and choice of reference genes.",
    ),
    (
        "MIQE-49",
        "Data analysis",
        "Description of normalisation method.",
    ),
    (
        "MIQE-50",
        "Data analysis",
        "Number and concordance of biological replicates.",
    ),
    (
        "MIQE-51",
        "Data analysis",
        "Number and stage (RT or qPCR) of technical replicates.",
    ),
    (
        "MIQE-52",
        "Data analysis",
        "Repeatability (intra-assay variation).",
    ),
    (
        "MIQE-53",
        "Data analysis",
        "Reproducibility (inter-assay variation, %CV).",
    ),
    (
        "MIQE-54",
        "Data analysis",
        "Power analysis.",
    ),
    (
        "MIQE-55",
        "Data analysis",
        "Statistical methods for results significance.",
    ),
    (
        "MIQE-56",
        "Data analysis",
        "Software (source, version).",
    ),
    (
        "MIQE-57",
        "Data analysis",
        "Cq or raw data submission using RDML.",
    ),
)


# --------------------------------------------------------------------------- #
# Auto-classifier                                                             #
# --------------------------------------------------------------------------- #


# Keyword groups: each item_id may map to one or more sets of keywords.
# Presence of any keyword in any group flags the item as "present".
_ARRIVE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "ARRIVE-1a": ("group", "control", "experimental unit", "randomis", "randomiz"),
    "ARRIVE-2a": ("sample size", "n =", "n=", "per group", "power analysis"),
    "ARRIVE-3a": ("inclusion", "exclusion", "excluded", "drop out", "dropout"),
    "ARRIVE-4a": ("randomis", "randomiz", "random allocation", "block design"),
    "ARRIVE-5a": ("blind", "masked", "single-blind", "double-blind"),
    "ARRIVE-6a": ("primary outcome", "secondary outcome", "endpoint", "outcome measure"),
    "ARRIVE-7a": (
        "t-test",
        "anova",
        "regression",
        "mixed model",
        "bonferroni",
        "fdr",
        "statistical software",
        "scipy",
        "statsmodels",
    ),
    "ARRIVE-8a": (
        "c57bl/6",
        "balb/c",
        "mouse",
        "mice",
        "rat",
        "strain",
        "sex",
        "male",
        "female",
        "wild-type",
        "wild type",
        "knockout",
    ),
    "ARRIVE-9a": (
        "humane endpoint",
        "analges",
        "buprenorphine",
        "anesthe",
        "anaesthe",
        "isoflurane",
        "protocol",
    ),
    "ARRIVE-10a": (
        "mean",
        "median",
        "95% ci",
        "confidence interval",
        "effect size",
        "cohen",
    ),
}


_CONSORT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "CONSORT-1a": ("randomised trial", "randomized trial", "rct"),
    "CONSORT-1b": ("structured abstract", "background:", "methods:", "results:"),
    "CONSORT-2a": ("background", "rationale", "introduction"),
    "CONSORT-2b": ("objective", "hypothesis", "aim"),
    "CONSORT-3a": ("parallel", "factorial", "allocation ratio", "crossover"),
    "CONSORT-3b": ("protocol amendment", "changes to methods", "amendment"),
    "CONSORT-4a": ("eligibility", "inclusion criteria", "exclusion criteria"),
    "CONSORT-4b": ("setting", "location", "site", "hospital", "clinic"),
    "CONSORT-5": ("intervention", "treatment", "administered", "dose"),
    "CONSORT-6a": ("primary outcome", "secondary outcome", "pre-specified"),
    "CONSORT-6b": ("outcome changes", "amended outcomes"),
    "CONSORT-7a": ("sample size", "power analysis", "n per arm"),
    "CONSORT-7b": ("interim analysis", "stopping rule", "stopping guideline"),
    "CONSORT-8a": ("random allocation", "allocation sequence", "computer-generated"),
    "CONSORT-8b": ("block randomisation", "block randomization", "stratified randomis"),
    "CONSORT-9": ("allocation concealment", "sealed envelope", "central allocation"),
    "CONSORT-10": ("enrolled", "investigator assigned", "randomisation list"),
    "CONSORT-11a": ("blinded", "double-blind", "masked", "single-blind"),
    "CONSORT-11b": ("similar appearance", "placebo identical", "matching placebo"),
    "CONSORT-12a": ("intention-to-treat", "itt", "primary analysis"),
    "CONSORT-12b": ("subgroup analysis", "adjusted analysis", "sensitivity analysis"),
    "CONSORT-13a": ("flow diagram", "consort diagram", "participants randomly"),
    "CONSORT-13b": ("lost to follow-up", "withdrew", "exclusions after"),
    "CONSORT-14a": ("recruitment period", "follow-up", "enrolment dates"),
    "CONSORT-14b": ("trial ended", "trial stopped", "completion"),
}


_STARD_KEYWORDS: dict[str, tuple[str, ...]] = {
    "STARD-1": ("diagnostic accuracy", "sensitivity", "specificity", "auc"),
    "STARD-2": ("structured abstract", "background:", "methods:"),
    "STARD-3": ("intended use", "clinical role", "index test"),
    "STARD-4": ("objective", "hypothesis", "aim"),
    "STARD-5": ("prospective", "retrospective", "study design"),
    "STARD-6": ("eligibility", "inclusion criteria"),
    "STARD-7": ("symptoms", "previous test", "registry"),
    "STARD-8": ("setting", "location", "dates", "recruitment site"),
    "STARD-9": ("consecutive", "convenience series", "random series"),
    "STARD-10a": ("index test", "test procedure"),
    "STARD-10b": ("reference standard", "gold standard"),
    "STARD-11": ("rationale for reference"),
    "STARD-12a": ("cut-off", "cutoff", "threshold", "test positivity"),
    "STARD-12b": ("reference cut-off", "reference threshold"),
    "STARD-13a": ("blinded to reference", "masked to reference"),
    "STARD-13b": ("blinded to index", "masked to index"),
    "STARD-14": ("sensitivity", "specificity", "ppv", "npv", "auc", "roc"),
    "STARD-15": ("indeterminate", "inconclusive"),
    "STARD-16": ("missing data", "imputation"),
    "STARD-17": ("variability", "subgroup"),
    "STARD-18": ("sample size", "power analysis"),
    "STARD-19": ("flow diagram", "participant flow", "stard diagram"),
    "STARD-20": ("baseline characteristics", "demographics"),
    "STARD-21a": ("severity", "disease severity"),
    "STARD-21b": ("alternative diagnoses", "differential diagnosis"),
    "STARD-22": ("time interval", "between index and reference"),
    "STARD-23": ("cross tabulation", "2x2 table", "contingency table"),
    "STARD-24": ("95% confidence interval", "95% ci", "precision"),
    "STARD-25": ("adverse event", "complication", "side effect"),
    "STARD-26": ("limitation", "bias", "generalisability", "generalizability"),
}


_MIQE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "MIQE-1": ("experimental group", "control group"),
    "MIQE-2": ("n =", "n=", "per group", "biological replicate"),
    "MIQE-3": ("core laboratory", "in-house"),
    "MIQE-5": ("sample type", "tissue", "cell line", "blood", "biopsy"),
    "MIQE-6": ("volume", "mass", "amount", "mg of tissue", "ml of"),
    "MIQE-8": ("processing", "preservation"),
    "MIQE-9": ("frozen", "cryopreserved", "snap-frozen"),
    "MIQE-10": ("fixed", "ffpe", "paraformaldehyde", "formaldehyde"),
    "MIQE-12": ("rna extraction", "dna extraction", "trizol", "qiagen", "rneasy"),
    "MIQE-14": ("dnase", "rnase", "dnase treatment"),
    "MIQE-15": ("contamination", "purity"),
    "MIQE-16": ("nanodrop", "qubit", "a260", "a280", "yield"),
    "MIQE-17": ("rin", "rqi", "bioanalyzer", "rna integrity"),
    "MIQE-18": ("reverse transcription", "superscript", "cdna synthesis"),
    "MIQE-19": ("gene symbol", "accession", "amplicon length"),
    "MIQE-20": ("blast", "in silico"),
    "MIQE-22": ("primer sequence", "forward primer", "reverse primer"),
    "MIQE-23": ("rtprimerdb",),
    "MIQE-24": ("probe sequence", "taqman probe"),
    "MIQE-26": ("oligonucleotide manufacturer", "idt", "sigma-aldrich"),
    "MIQE-27": ("qpcr reaction", "reaction volume", "magnesium"),
    "MIQE-29": ("thermocycling", "denaturation", "annealing", "extension"),
    "MIQE-31": ("qpcr instrument", "lightcycler", "step-one", "quantstudio", "applied biosystems"),
    "MIQE-32": ("optimisation", "optimization", "gradient"),
    "MIQE-33": ("specificity", "melt curve", "gel electrophoresis"),
    "MIQE-35": ("standard curve", "slope", "y-intercept"),
    "MIQE-36": ("pcr efficiency", "efficiency"),
    "MIQE-38": ("r2", "r-squared", "correlation coefficient"),
    "MIQE-39": ("dynamic range", "linear range"),
    "MIQE-42": ("limit of detection", "lod"),
    "MIQE-44": ("analysis program", "qbase", "rest", "linregpcr"),
    "MIQE-45": ("cq", "ct value", "threshold cycle"),
    "MIQE-48": ("reference gene", "housekeeping gene"),
    "MIQE-49": ("normalisation", "normalization"),
    "MIQE-50": ("biological replicate",),
    "MIQE-51": ("technical replicate",),
    "MIQE-54": ("power analysis",),
    "MIQE-55": ("statistical test", "significance"),
    "MIQE-56": ("software", "version"),
    "MIQE-57": ("rdml",),
}


def _keyword_table(kind: ChecklistKind) -> dict[str, tuple[str, ...]]:
    if kind == ChecklistKind.arrive:
        return _ARRIVE_KEYWORDS
    if kind == ChecklistKind.consort:
        return _CONSORT_KEYWORDS
    if kind == ChecklistKind.stard:
        return _STARD_KEYWORDS
    if kind == ChecklistKind.miqe:
        return _MIQE_KEYWORDS
    return {}


def _items_table(kind: ChecklistKind) -> tuple[tuple[str, str, str], ...]:
    if kind == ChecklistKind.arrive:
        return ARRIVE_2_0_ITEMS
    if kind == ChecklistKind.consort:
        return CONSORT_2010_ITEMS
    if kind == ChecklistKind.stard:
        return STARD_2015_ITEMS
    if kind == ChecklistKind.miqe:
        return MIQE_ITEMS
    return ()


def _safe_read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _read_manuscript(manuscript_path: Path | None) -> str | None:
    if manuscript_path is None:
        return None
    p = Path(manuscript_path)
    if not p.is_file():
        return None
    return _safe_read_text(p).lower()


def _read_project_yaml(project_root: Path) -> dict[str, Any]:
    for name in ("panelforge.project.yaml", "panelforge.project.yml"):
        p = project_root / name
        if p.is_file():
            try:
                import yaml  # type: ignore[import-untyped]

                loaded = yaml.safe_load(_safe_read_text(p))
                return loaded if isinstance(loaded, dict) else {}
            except ImportError:  # pragma: no cover
                return {}
            except Exception:
                return {}
    return {}


def _contract_fields_from_plan(figure_plan: Any) -> dict[str, Any]:
    """Aggregate statistical-contract field presence across all recipes in plan."""
    out: dict[str, Any] = {
        "any_min_n": False,
        "any_correction": False,
        "any_random_seed": False,
        "any_independence_paired": False,
        "any_blinding_flag": False,
    }
    if figure_plan is None:
        return out

    figures = getattr(figure_plan, "figures", None)
    if figures is None and isinstance(figure_plan, dict):
        figures = figure_plan.get("figures", [])
    if not figures:
        return out

    try:
        from ..core.contract import ensure_all_imported, get_recipe

        try:
            ensure_all_imported()
        except Exception:
            pass

        for fig in figures:
            panels = getattr(fig, "panels", None)
            if panels is None and isinstance(fig, dict):
                panels = fig.get("panels", [])
            for p in panels or ():
                recipe_name = (
                    getattr(p, "recipe_full_name", None)
                    or (p.get("recipe_full_name") if isinstance(p, dict) else None)
                    or ""
                )
                if not recipe_name:
                    continue
                try:
                    entry = get_recipe(recipe_name)
                    meta = entry.metadata
                except Exception:
                    continue
                contract = getattr(meta, "statistical_contract", None)
                if contract is None:
                    continue
                if getattr(contract, "min_n_per_group", None):
                    out["any_min_n"] = True
                if getattr(contract, "multiple_comparisons", "none") != "none":
                    out["any_correction"] = True
                if getattr(contract, "independence", "any") in ("paired", "clustered_by_subject"):
                    out["any_independence_paired"] = True
    except Exception:
        pass

    return out


def _scan_provenance_for_seeds(project_root: Path) -> bool:
    """True iff any provenance.json has a randomisation seed embedded."""
    workspace = project_root / "panelforge_workspace" / "figures"
    if not workspace.is_dir():
        return False
    import json

    for path in workspace.glob("*.provenance.json"):
        try:
            blob = json.loads(_safe_read_text(path))
        except Exception:
            continue
        if not isinstance(blob, dict):
            continue
        # Look in scorer / rendering_environment / provenance_lock.
        for key in ("scorer", "rendering_environment", "provenance_lock"):
            sub = blob.get(key)
            if isinstance(sub, dict) and (
                "random_seed" in sub
                or "seed" in sub
                or "rng_state" in sub
                or "rng_seed" in sub
            ):
                return True
    return False


def auto_classify_item(
    item_id: str,
    section: str,
    description: str,
    *,
    project_root: Path,
    manuscript_text: str | None = None,
    figure_plan: Any | None = None,
    contract_fields: dict[str, Any] | None = None,
) -> tuple[ChecklistItemStatus, str, str]:
    """Classify a single item by scanning manuscript/contract/YAML.

    Returns ``(status, evidence_text, location_hint)``.

    The classifier is conservative: keywords + contract evidence flip to
    ``present`` only when they're directly relevant; otherwise the item
    is left ``unknown`` so the author must mark it explicitly.
    """
    # Determine which checklist the item_id belongs to from its prefix.
    if item_id.startswith("ARRIVE-"):
        kind = ChecklistKind.arrive
    elif item_id.startswith("CONSORT-"):
        kind = ChecklistKind.consort
    elif item_id.startswith("STARD-"):
        kind = ChecklistKind.stard
    elif item_id.startswith("MIQE-"):
        kind = ChecklistKind.miqe
    else:
        return (ChecklistItemStatus.unknown, "", "")

    keywords = _keyword_table(kind).get(item_id, ())

    # 1. Keyword-based check on manuscript text.
    if manuscript_text and keywords:
        ms = manuscript_text  # already lowercased upstream
        for kw in keywords:
            if kw.lower() in ms:
                idx = ms.find(kw.lower())
                snippet = ms[max(0, idx - 30) : idx + 80].replace("\n", " ").strip()
                return (
                    ChecklistItemStatus.present,
                    f"manuscript matched keyword {kw!r}: ...{snippet}...",
                    "Manuscript text",
                )

    # 2. Contract-evidence checks for sample-size / blinding / correction items.
    cf = contract_fields or {}
    if item_id in ("ARRIVE-2a", "CONSORT-7a", "STARD-18", "MIQE-54") and cf.get("any_min_n"):
        return (
            ChecklistItemStatus.present,
            "statistical_contract.min_n_per_group set in figure plan",
            "Recipe registry — statistical_contract",
        )
    if item_id in ("ARRIVE-7a", "CONSORT-12a") and cf.get("any_correction"):
        return (
            ChecklistItemStatus.present,
            "statistical_contract.multiple_comparisons populated",
            "Recipe registry — statistical_contract",
        )

    # 3. Randomisation seed check via provenance sidecars.
    if item_id in ("ARRIVE-4a", "CONSORT-8a"):
        if _scan_provenance_for_seeds(project_root):
            return (
                ChecklistItemStatus.present,
                "random_seed found in provenance.json sidecar",
                "panelforge_workspace/figures/*.provenance.json",
            )

    # 4. YAML organism block check for ARRIVE-8a.
    if item_id == "ARRIVE-8a":
        yaml_cfg = _read_project_yaml(project_root)
        if yaml_cfg.get("organisms") or yaml_cfg.get("strains"):
            return (
                ChecklistItemStatus.present,
                "organisms/strains block declared in panelforge.project.yaml",
                "panelforge.project.yaml",
            )

    return (ChecklistItemStatus.unknown, "", "")


# --------------------------------------------------------------------------- #
# Generators                                                                  #
# --------------------------------------------------------------------------- #


def _build_checklist(
    kind: ChecklistKind,
    project_root: Path,
    manuscript_path: Path | None,
    figure_plan: Any | None,
) -> Checklist:
    root = Path(project_root)
    if not root.exists() or not root.is_dir():
        raise ChecklistError(f"project_root does not exist: {root}")

    manuscript_text = _read_manuscript(manuscript_path)
    contract_fields = _contract_fields_from_plan(figure_plan)
    items_in: tuple[tuple[str, str, str], ...] = _items_table(kind)

    classified: list[ChecklistItem] = []
    n_present = n_absent = n_na = n_unknown = 0

    for item_id, sec, desc in items_in:
        status, evidence, loc = auto_classify_item(
            item_id,
            sec,
            desc,
            project_root=root,
            manuscript_text=manuscript_text,
            figure_plan=figure_plan,
            contract_fields=contract_fields,
        )
        classified.append(
            ChecklistItem(
                item_id=item_id,
                section=sec,
                description=desc,
                status=status,
                evidence=evidence,
                location_hint=loc,
            )
        )
        if status == ChecklistItemStatus.present:
            n_present += 1
        elif status == ChecklistItemStatus.absent:
            n_absent += 1
        elif status == ChecklistItemStatus.not_applicable:
            n_na += 1
        else:
            n_unknown += 1

    return Checklist(
        kind=kind,
        items=tuple(classified),
        n_present=n_present,
        n_absent=n_absent,
        n_not_applicable=n_na,
        n_unknown=n_unknown,
        pass_threshold=0.85,
    )


def generate_arrive_checklist(
    project_root: Path,
    *,
    manuscript_path: Path | None = None,
    figure_plan: Any | None = None,
) -> Checklist:
    """Build the ARRIVE 2.0 checklist with auto-classified status."""
    return _build_checklist(
        ChecklistKind.arrive, project_root, manuscript_path, figure_plan
    )


def generate_consort_checklist(
    project_root: Path,
    *,
    manuscript_path: Path | None = None,
    figure_plan: Any | None = None,
) -> Checklist:
    """Build the CONSORT 2010 checklist with auto-classified status."""
    return _build_checklist(
        ChecklistKind.consort, project_root, manuscript_path, figure_plan
    )


def generate_stard_checklist(
    project_root: Path,
    *,
    manuscript_path: Path | None = None,
    figure_plan: Any | None = None,
) -> Checklist:
    """Build the STARD 2015 checklist with auto-classified status."""
    return _build_checklist(
        ChecklistKind.stard, project_root, manuscript_path, figure_plan
    )


def generate_miqe_checklist(
    project_root: Path,
    *,
    manuscript_path: Path | None = None,
    figure_plan: Any | None = None,
) -> Checklist:
    """Build the MIQE checklist with auto-classified status."""
    return _build_checklist(
        ChecklistKind.miqe, project_root, manuscript_path, figure_plan
    )


# --------------------------------------------------------------------------- #
# Renderers                                                                   #
# --------------------------------------------------------------------------- #


_LATEX_STATUS_SYMBOL: dict[ChecklistItemStatus, str] = {
    ChecklistItemStatus.present: r"\textcolor{green!60!black}{\checkmark}",
    ChecklistItemStatus.absent: r"\textcolor{red!70!black}{$\times$}",
    ChecklistItemStatus.not_applicable: r"\textcolor{gray}{--}",
    ChecklistItemStatus.unknown: r"\textcolor{orange}{?}",
}

_MD_STATUS_SYMBOL: dict[ChecklistItemStatus, str] = {
    ChecklistItemStatus.present: "[x]",
    ChecklistItemStatus.absent: "[ ]",
    ChecklistItemStatus.not_applicable: "[-]",
    ChecklistItemStatus.unknown: "[?]",
}


def _latex_escape(text: str) -> str:
    if not text:
        return ""
    repl = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(repl.get(c, c) for c in text)


def render_checklist_latex(checklist: Checklist) -> str:
    """Render a checklist as a LaTeX ``longtable`` with status colours.

    The output requires ``\\usepackage{longtable}`` and
    ``\\usepackage{xcolor}`` in the preamble.
    """
    lines: list[str] = []
    title = checklist.kind.value
    lines.append(
        rf"% {title} reporting checklist — {checklist.n_present} present, "
        rf"{checklist.n_absent} absent, {checklist.n_not_applicable} N/A, "
        rf"{checklist.n_unknown} unknown."
    )
    lines.append(r"\begin{longtable}{l p{3.5cm} p{8.0cm} c}")
    lines.append(
        rf"\caption{{{_latex_escape(title)} reporting checklist.}} \\"
    )
    lines.append(r"\toprule")
    lines.append(r"Item & Section & Description & Status \\")
    lines.append(r"\midrule")
    lines.append(r"\endfirsthead")
    lines.append(r"\toprule")
    lines.append(r"Item & Section & Description & Status \\")
    lines.append(r"\midrule")
    lines.append(r"\endhead")
    lines.append(r"\bottomrule")
    lines.append(r"\endfoot")

    for item in checklist.items:
        symbol = _LATEX_STATUS_SYMBOL.get(item.status, "?")
        lines.append(
            " & ".join(
                [
                    _latex_escape(item.item_id),
                    _latex_escape(item.section),
                    _latex_escape(item.description),
                    symbol,
                ]
            )
            + r" \\"
        )

    lines.append(r"\end{longtable}")
    return "\n".join(lines) + "\n"


def render_checklist_markdown(checklist: Checklist) -> str:
    """Render a checklist as a Markdown table with status checkboxes."""
    lines: list[str] = []
    title = checklist.kind.value
    lines.append(f"# {title} reporting checklist")
    lines.append("")
    lines.append(
        f"Auto-detected: **{checklist.n_present} present**, "
        f"**{checklist.n_absent} absent**, "
        f"**{checklist.n_not_applicable} N/A**, "
        f"**{checklist.n_unknown} unknown**. "
        f"Pass threshold: {checklist.pass_threshold:.0%}."
    )
    lines.append("")
    lines.append("| Item | Section | Description | Status | Evidence |")
    lines.append("|---|---|---|:---:|---|")
    for item in checklist.items:
        sym = _MD_STATUS_SYMBOL.get(item.status, "[?]")
        desc = item.description.replace("|", r"\|").replace("\n", " ")
        evidence = (item.evidence or "").replace("|", r"\|").replace("\n", " ")
        lines.append(
            f"| {item.item_id} | {item.section} | {desc} | {sym} | {evidence} |"
        )

    return "\n".join(lines) + "\n"
