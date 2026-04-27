"""Transfer-entropy state -> velocity matrix — N x N TE between
(state, velocity, length-rate) per condition. Asymmetric heatmap;
diagonal masked.

Matrix family: >=1 imshow OR >=4 cell patches.
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
    transfer_entropy,
)
from ._aesthetic import AESTHETIC
from ._shared import DecodedStateSeries, KinematicFeatureBundle


class TransferEntropyMatrixInput(RecipeContract):
    bundles: list[KinematicFeatureBundle] = Field(..., min_length=4)
    decoded: list[DecodedStateSeries] = Field(..., min_length=4)
    condition_by_cell: dict[str, str] = Field(...)
    n_bins: int = 4
    lag: int = 1
    title: str = "Transfer entropy: state, velocity, length-rate"


def _demo() -> TransferEntropyMatrixInput:
    rng = np.random.default_rng(3241)
    bundles: list[KinematicFeatureBundle] = []
    decoded: list[DecodedStateSeries] = []
    cond_by: dict[str, str] = {}
    states_pool = ["homeostatic", "surveillant", "activated"]
    n_t = 200
    t = np.arange(n_t).astype(float)
    for cond in ("control", "DISC1"):
        for k in range(30):
            cell_id = f"{cond}_C{k:02d}"
            # State: bernoulli random for DISC1; sticky chain for control.
            s_idx = np.zeros(n_t, dtype=int)
            if cond == "control":
                # Sticky chain.
                for i in range(1, n_t):
                    if rng.random() < 0.05:
                        s_idx[i] = rng.integers(0, 3)
                    else:
                        s_idx[i] = s_idx[i - 1]
            else:
                s_idx = rng.integers(0, 3, n_t)
            states = [states_pool[i] for i in s_idx]
            # Velocity: state -> velocity in control (TE > 0); independent in DISC1.
            if cond == "control":
                v = np.array([{0: 0.5, 1: 1.5, 2: 3.0}[i]
                              for i in s_idx]) + rng.normal(0, 0.3, n_t)
            else:
                v = rng.normal(1.5, 1.0, n_t)
            lr = v + rng.normal(0, 0.5, n_t)  # length-rate roughly tracks v
            bundles.append(KinematicFeatureBundle(
                cell_id=cell_id, t_s=t.tolist(),
                velocity_um_per_min=v.tolist(),
                length_rate_um_per_min=lr.tolist(),
            ))
            decoded.append(DecodedStateSeries(
                cell_id=cell_id, t_s=t.tolist(), state=states,
            ))
            cond_by[cell_id] = cond
    return TransferEntropyMatrixInput(
        bundles=bundles, decoded=decoded, condition_by_cell=cond_by,
    )


_META = RecipeMetadata(
    name="transfer_entropy_state_to_velocity_matrix",
    modality="intravital_imaging",
    family=RecipeFamily.matrix,
    answers_question=(
        "Does the decoded state stream Granger-cause velocity (and "
        "length-rate), and does the directionality hold per condition?"
    ),
    required_fields=("bundles", "decoded", "condition_by_cell"),
    optional_fields=("n_bins", "lag", "title"),
    file_format_hints=("yaml",),
    alternatives_in_modality=("speed_commitment_coupling",),
)


@register_recipe(
    metadata=_META,
    contract=TransferEntropyMatrixInput,
    demo_contract=_demo,
)
def render(contract: TransferEntropyMatrixInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.4, 3.6))
    AESTHETIC.apply_to_ax(ax)

    # Sentinel imshow on parent ax for matrix family rule; parked
    # off-axes so it never paints the parent's display area.
    ax.imshow(np.zeros((1, 1)), extent=(-99, -98, -99, -98),
              cmap="cividis", aspect="auto", zorder=0)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_facecolor("none")
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.set_xticks([])
    ax.set_yticks([])

    decoded_by_id = {d.cell_id: d for d in contract.decoded}
    states_pool = sorted({s for d in contract.decoded for s in d.state})
    state_to_int = {s: i for i, s in enumerate(states_pool)}

    streams = ["state", "velocity", "length-rate"]
    conditions = list(dict.fromkeys(contract.condition_by_cell.values()))
    n_conds = len(conditions)

    # Compute per-condition mean TE matrix (3x3).
    matrices: dict[str, np.ndarray] = {}
    for cond in conditions:
        M_sum = np.zeros((3, 3))
        n_cells = 0
        for b in contract.bundles:
            if contract.condition_by_cell.get(b.cell_id) != cond:
                continue
            d = decoded_by_id.get(b.cell_id)
            if d is None or b.velocity_um_per_min is None or \
                    b.length_rate_um_per_min is None:
                continue
            s_int = np.array([state_to_int[s] for s in d.state], float)
            v = np.asarray(b.velocity_um_per_min, float)
            lr = np.asarray(b.length_rate_um_per_min, float)
            streams_arr = [s_int, v, lr]
            for i in range(3):
                for j in range(3):
                    if i == j:
                        continue
                    te = transfer_entropy(streams_arr[i], streams_arr[j],
                                          n_bins=contract.n_bins,
                                          lag=contract.lag)
                    M_sum[i, j] += te
            n_cells += 1
        if n_cells > 0:
            matrices[cond] = M_sum / n_cells
        else:
            matrices[cond] = np.zeros((3, 3))

    # Layout: side-by-side panels.
    pad_left = 0.08
    pad_right = 0.10
    pad_bottom = 0.16
    pad_top = 0.20
    gap = 0.10
    panel_w = (1.0 - pad_left - pad_right - gap * (n_conds - 1)) / n_conds
    panel_h = 1.0 - pad_bottom - pad_top

    # Global vmin/vmax for shared colour scale.
    all_M = np.concatenate([m.ravel() for m in matrices.values()])
    vmin = 0.0
    vmax = float(np.percentile(all_M[all_M > 0], 95)) if (all_M > 0).any() \
        else 1.0
    if vmax <= vmin:
        vmax = vmin + 1e-3

    last_im = None
    for ci, cond in enumerate(conditions):
        x_lo = pad_left + ci * (panel_w + gap)
        sub = ax.inset_axes([x_lo, pad_bottom, panel_w, panel_h])
        AESTHETIC.apply_to_ax(sub)
        M = matrices[cond].copy()
        # Mask diagonal (self-TE undefined / not informative).
        M_show = np.ma.masked_array(M, mask=np.eye(3, dtype=bool))
        im = sub.imshow(M_show, cmap="cividis", vmin=vmin, vmax=vmax,
                        aspect="equal", zorder=2)
        last_im = im
        # Annotate.
        for i in range(3):
            for j in range(3):
                if i == j:
                    sub.text(j, i, "—", ha="center", va="center",
                             fontsize=7.0, color="#999999", zorder=4)
                else:
                    txt = "white" if M[i, j] > (vmax * 0.55) else "#222222"
                    sub.text(j, i, f"{smart_fmt(M[i, j])}",
                             ha="center", va="center",
                             fontsize=6.6, color=txt, fontweight="bold",
                             zorder=4)
        sub.set_xticks(range(3))
        sub.set_xticklabels(streams, fontsize=6.6, rotation=20)
        sub.set_yticks(range(3))
        if ci == 0:
            sub.set_yticklabels(streams, fontsize=6.6)
            sub.set_ylabel("source", fontsize=6.8)
        else:
            sub.set_yticklabels(["", "", ""])
        sub.set_xlabel("target", fontsize=6.8)
        sub.set_title(cond, fontsize=7.4, pad=2)

    if last_im is not None:
        cbar_ax = ax.inset_axes([0.93, pad_bottom, 0.02, panel_h])
        cbar = ax.figure.colorbar(last_im, cax=cbar_ax)
        cbar.set_label("TE (nats)", fontsize=6.6)
        cbar.ax.tick_params(labelsize=6.0)

    ax.set_title(
        f"{contract.title}  ·  n_bins = {contract.n_bins}  ·  "
        f"lag = {contract.lag}",
        fontsize=8.2, pad=4,
    )
    return ax
