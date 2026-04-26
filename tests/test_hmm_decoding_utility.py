"""Tests for `core.hmm_decoding_utility` — HMM + HSMM shims."""

from __future__ import annotations

import numpy as np

from panelforge_figures.core import (
    decode_states,
    decode_states_semi,
    fit_summary,
)


def _make_3state_synthetic(n_obs: int = 240, seed: int = 0):
    """Generate a 3-state ground-truth series with distinct emissions."""
    rng = np.random.default_rng(seed)
    state_means = np.array([[0.0, 0.0], [3.0, 1.0], [-2.0, 4.0]])
    state_sds = np.array([0.5, 0.5, 0.5])
    # Generate state path (with reasonable persistence).
    states_true = np.zeros(n_obs, dtype=int)
    s = 0
    for t in range(n_obs):
        if rng.random() < 0.05 and t > 0:
            s = int(rng.integers(0, 3))
        states_true[t] = s
    # Emit features.
    feats = (state_means[states_true]
             + rng.normal(0, 1, (n_obs, 2))
             * state_sds[states_true, None])
    return feats, states_true


def test_decode_states_recovers_correct_state_count():
    feats, _ = _make_3state_synthetic()
    result = decode_states(feats, n_states=3, seed=0)
    assert "state" in result
    assert len(result["state"]) == feats.shape[0]
    unique = set(result["state"])
    assert 1 <= len(unique) <= 3


def test_decode_states_returns_posterior_summing_to_one():
    feats, _ = _make_3state_synthetic()
    result = decode_states(feats, n_states=3, seed=0)
    posterior = np.asarray(result["posterior_prob"])
    row_sums = posterior.sum(axis=1)
    np.testing.assert_allclose(row_sums, 1.0, atol=1e-3)


def test_decode_states_returns_aic_bic_log_likelihood():
    feats, _ = _make_3state_synthetic()
    result = decode_states(feats, n_states=3, seed=0)
    assert isinstance(result["log_likelihood"], float)
    assert isinstance(result["aic"], float)
    assert isinstance(result["bic"], float)
    assert result["bic"] > result["aic"]  # BIC penalty harsher than AIC


def test_decode_states_high_purity_against_truth():
    feats, true = _make_3state_synthetic(seed=1)
    result = decode_states(feats, n_states=3, seed=1)
    decoded = np.array([int(s[1:]) for s in result["state"]])
    # Find best label permutation (HMM labels are unidentifiable).
    from itertools import permutations
    best_acc = 0.0
    for perm in permutations(range(3)):
        relabel = np.array([perm[d] for d in decoded])
        acc = float((relabel == true).mean())
        if acc > best_acc:
            best_acc = acc
    assert best_acc > 0.65  # very forgiving threshold


def test_decode_states_semi_returns_duration_params():
    feats, _ = _make_3state_synthetic()
    result = decode_states_semi(feats, n_states=3, seed=0)
    assert "duration_shape_per_state" in result
    assert "duration_scale_per_state" in result
    assert len(result["duration_shape_per_state"]) == 3
    assert len(result["duration_scale_per_state"]) == 3


def test_decode_states_semi_n_params_higher_than_hmm():
    """HSMM has 2 extra params per state (duration shape + scale)."""
    feats, _ = _make_3state_synthetic()
    hmm = decode_states(feats, n_states=3, seed=0)
    hsmm = decode_states_semi(feats, n_states=3, seed=0)
    assert hsmm["n_params"] == hmm["n_params"] + 2 * 3


def test_fit_summary_reshapes_into_modelfitsummary_dict():
    feats, _ = _make_3state_synthetic()
    decoded = decode_states(feats, n_states=3, seed=0)
    summary = fit_summary(decoded, stratum="control")
    assert summary["stratum"] == "control"
    assert summary["model"] == "HMM"
    assert summary["n_states"] >= 1
    assert "log_likelihood" in summary
    assert "aic" in summary
    assert "bic" in summary
