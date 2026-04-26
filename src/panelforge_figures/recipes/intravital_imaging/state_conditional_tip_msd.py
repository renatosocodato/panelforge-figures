"""State-conditional tip MSD — log-log MSD(τ) restricted to same-
state epochs, per state, with optional α-fit.

Closes the loop with the alpha `msd_curve_by_state` recipe but
where τ is restricted to consecutive same-state epochs (so the
diffusion regime is purely state-specific). Activated tips
super-diffuse (α > 1), homeostatic tips sub-diffuse (α < 1).

Timecourse-hierarchical-CI family: >=1 filled CI band + >=1 mean
line. Satisfied by per-state MSD curves with bootstrap CI ribbons.
"""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC
from ._shared import DecodedStateSeries, TipTrack, _demo_state_palette


class StateConditionalMSDInput(RecipeContract):
    tracks: list[TipTrack] = Field(..., min_length=1)
    decoded: list[DecodedStateSeries] = Field(..., min_length=1)
    states: list[str] = Field(..., min_length=1)
    tau_max_frames: int = 30
    fit_alpha: bool = True
    min_epoch_frames: int = 8
    decoder_label: str = "HMM"
    title: str = "State-conditional tip MSD"


def _demo() -> StateConditionalMSDInput:
    rng = np.random.default_rng(2761)
    states = ["homeostatic", "surveillant", "activated"]
    # Per-state diffusion: alpha = 0.6 (sub) / 1.0 (Brownian) / 1.5 (super).
    alpha_by_state = {"homeostatic": 0.6, "surveillant": 1.0,
                      "activated": 1.5}
    sigma_by_state = {"homeostatic": 0.4, "surveillant": 1.0,
                      "activated": 2.2}
    tracks = []
    decoded_list = []
    for k in range(8):
        n_t = 200
        # Pick state path with long sticky epochs.
        seq = []
        s = states[rng.integers(0, 3)]
        for _ in range(n_t):
            if rng.random() < 0.02:
                s = states[rng.integers(0, 3)]
            seq.append(s)
        # Generate XY: anomalous-walk increments per state.
        x = np.zeros(n_t)
        y = np.zeros(n_t)
        for t in range(1, n_t):
            sigma = sigma_by_state[seq[t]]
            alpha = alpha_by_state[seq[t]]
            # Anomalous step: scale step by t^((alpha-1)/2) (rough).
            step_scale = sigma * (1 + 0.05 * t) ** ((alpha - 1) / 2)
            x[t] = x[t-1] + rng.normal(0, step_scale)
            y[t] = y[t-1] + rng.normal(0, step_scale)
        tracks.append(TipTrack(
            tip_id=f"T{k:02d}",
            x_um=x.tolist(),
            y_um=y.tolist(),
            t_s=list(range(n_t)),
            parent_cell_id=f"C{k:02d}",
        ))
        decoded_list.append(DecodedStateSeries(
            cell_id=f"C{k:02d}",
            t_s=list(range(n_t)),
            state=seq,
            decoder="HMM",
        ))
    return StateConditionalMSDInput(
        tracks=tracks,
        decoded=decoded_list,
        states=states,
    )


_META = RecipeMetadata(
    name="state_conditional_tip_msd",
    modality="intravital_imaging",
    family=RecipeFamily.timecourse_hierarchical_ci,
    answers_question=(
        "Per decoded state, what is the tip MSD(tau) computed over "
        "same-state epochs, and what is the diffusion exponent alpha?"
    ),
    required_fields=("tracks", "decoded", "states"),
    optional_fields=(
        "tau_max_frames", "fit_alpha", "min_epoch_frames",
        "decoder_label", "title",
    ),
    file_format_hints=("yaml", "json"),
    alternatives_in_modality=("msd_curve_by_state",),
)


@register_recipe(
    metadata=_META,
    contract=StateConditionalMSDInput,
    demo_contract=_demo,
)
def render(contract: StateConditionalMSDInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.8, 4.2))
    AESTHETIC.apply_to_ax(ax)

    palette = _demo_state_palette(contract.states)
    decoded_by_cell = {d.cell_id: d for d in contract.decoded}
    tau_grid = np.arange(1, contract.tau_max_frames + 1)
    rng = np.random.default_rng(13)

    bits = []
    for state in contract.states:
        # Collect (tau, sd^2) points from same-state epochs across all
        # tracks.
        per_tau_sd2: dict[int, list[float]] = {tau: [] for tau in tau_grid}
        for track in contract.tracks:
            d = decoded_by_cell.get(track.parent_cell_id or "")
            if d is None:
                continue
            x = np.asarray(track.x_um, float)
            y = np.asarray(track.y_um, float)
            seq = d.state
            n = min(len(x), len(seq))
            # Find runs of `state` ≥ min_epoch_frames.
            i = 0
            while i < n:
                if seq[i] != state:
                    i += 1
                    continue
                j = i
                while j < n and seq[j] == state:
                    j += 1
                if j - i < contract.min_epoch_frames:
                    i = j
                    continue
                xe = x[i:j]
                ye = y[i:j]
                for tau in tau_grid:
                    if tau >= len(xe):
                        break
                    dx = xe[tau:] - xe[:-tau]
                    dy = ye[tau:] - ye[:-tau]
                    sd2 = (dx ** 2 + dy ** 2)
                    per_tau_sd2[int(tau)].extend(sd2.tolist())
                i = j

        msd = np.array([
            float(np.mean(per_tau_sd2[int(tau)]))
            if per_tau_sd2[int(tau)] else np.nan
            for tau in tau_grid
        ])
        # Bootstrap CI per τ.
        ci_lo = np.full_like(msd, np.nan)
        ci_hi = np.full_like(msd, np.nan)
        for ti, tau in enumerate(tau_grid):
            vals = per_tau_sd2[int(tau)]
            if len(vals) < 4:
                continue
            varr = np.asarray(vals)
            boots = []
            for _ in range(80):
                idx = rng.integers(0, varr.size, size=varr.size)
                boots.append(float(np.mean(varr[idx])))
            ci_lo[ti] = float(np.quantile(boots, 0.025))
            ci_hi[ti] = float(np.quantile(boots, 0.975))

        colour = palette.get(state, "#888888")
        valid = np.isfinite(msd) & (msd > 0)
        if valid.sum() < 3:
            continue
        ax.plot(tau_grid[valid], msd[valid],
                color=colour, lw=1.2, zorder=4, label=state)
        ax.fill_between(tau_grid[valid], ci_lo[valid], ci_hi[valid],
                        color=colour, alpha=0.18, linewidth=0,
                        zorder=2)

        # α fit on log-log (least-squares slope of log MSD vs log τ).
        if contract.fit_alpha and valid.sum() >= 5:
            log_tau = np.log(tau_grid[valid])
            log_msd = np.log(msd[valid])
            slope, _ = np.polyfit(log_tau, log_msd, 1)
            bits.append(f"{state}: alpha = {smart_fmt(float(slope))}")

    # Reference: alpha = 1 (Brownian).
    if tau_grid.size and contract.fit_alpha:
        # Anchor through first finite point.
        tau_ref = tau_grid.astype(float)
        ref = (tau_ref * 1.0)
        # Scale so the reference passes near the median of all curves
        # at tau = 1.
        ax.plot(tau_ref, ref, color="#888888", lw=0.6, ls="--",
                zorder=3, label="alpha = 1 (Brownian)")

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("lag tau (frames)")
    ax.set_ylabel("MSD (um^2)")
    ax.grid(which="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    ax.legend(fontsize=6.6, frameon=False, loc="upper left",
              handlelength=1.4)

    ax.set_title(
        f"{contract.title}  ·  {contract.decoder_label}  ·  "
        + "   ".join(bits),
        fontsize=8.2, pad=4,
    )
    return ax
