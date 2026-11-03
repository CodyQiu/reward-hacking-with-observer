"""Step 4 validation: the PBRR variants (L- on the dispreferred trajectory, no L+,
g >= 0) and the exact tabular fit.

Run as ``.venv/bin/python tests/test_step4.py`` (or under pytest).
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.audit_grid import BASE
from src.pbrr_core import (GConfig, Traj, _reg_coef, build_design, fit_correction,
                           fit_correction_tabular, loss_numpy)
from src.pbrr_grid import transition_features
from src.report import run_tests

SWAP = GConfig(no_agree="max1", l_minus_on="dispreferred")


def _mdp1_pairs():
    proxy = np.array([10.0, 6.0, 7.0, 9.0])
    true = np.array([2.0, 4.0, 3.0, 8.0])

    def t(a):
        c = np.zeros(4)
        c[a] = 1
        return Traj(c, proxy[a], true[a], 1)
    return proxy, [(t(0), t(2), 1.0)]


def _random_pairs(seed=0, n_tr=12):
    rng = np.random.default_rng(seed)
    trajs = [Traj(rng.integers(0, 4, n_tr).astype(float), float(rng.normal() * 5),
                  float(rng.normal()), n_tr) for _ in range(8)]
    return [(trajs[i], trajs[j], float(rng.random() < 0.5)) for i in range(4) for j in range(4, 8)]


def test_defaults_reproduce_the_paper_regulariser():
    d = build_design(_random_pairs())
    assert np.array_equal(d.reg_for(GConfig()), d.reg)
    assert np.array_equal(d.reg, d.reg_plus + d.reg_pref)
    g = np.random.default_rng(1).normal(size=len(d.present))
    assert loss_numpy(g, d, GConfig()) == loss_numpy(g, d, GConfig(l_minus_on="preferred", l_plus=True))


def test_swap_moves_l_minus_onto_the_dispreferred_trajectory():
    t1, t2 = Traj(np.array([1.0, 0.0]), 5.0, 0.0, 1), Traj(np.array([0.0, 1.0]), 1.0, 0.0, 1)
    d = build_design([(t1, t2, 1.0)])                 # D-: proxy prefers tau1, label tau2
    assert np.allclose(d.reg_for(GConfig()), [0.0, 1.0])
    assert np.allclose(d.reg_for(SWAP), [1.0, 0.0])
    agree = build_design([(t1, t2, 0.0)])             # D+: L+ on both, dropped by l_plus=False
    assert np.allclose(agree.reg_for(SWAP), [1.0, 1.0])
    assert np.allclose(agree.reg_for(SWAP.with_(l_plus=False)), [0.0, 0.0])
    assert _reg_coef(d, SWAP) == 10.0                 # lambda rule unchanged (max1)


def test_swap_raises_the_preferred_transition_on_the_papers_minimal_mdp():
    proxy, pairs = _mdp1_pairs()
    g, _ = fit_correction_tabular(pairs, 4, SWAP)
    assert abs(g[0]) < 0.5 and g[2] > 3.0             # s1 left alone, s3 raised above s1
    assert proxy[2] + g[2] > proxy[0] + g[0]
    g0, _ = fit_correction_tabular(pairs, 4, GConfig(no_agree="max1"))
    assert abs(g0[2]) < 0.5 and g0[0] < -3.0          # the paper: s3 left alone, s1 lowered


def test_softplus_floor_keeps_g_nonnegative_on_every_grid_transition():
    X = transition_features(BASE)
    rng = np.random.default_rng(0)
    n = X.shape[0]

    def t(proxy, true):
        c = np.zeros(n)
        c[rng.integers(0, n, 30)] = 1.0
        return Traj(c, proxy, true, 30)
    pairs = [(t(500.0, -10.0), t(10.0, 10.0), 1.0) for _ in range(6)]
    cfg = SWAP.with_(g_floor="softplus", n_layers=3, width=64, epochs=50, lr=1e-3)
    g, info = fit_correction(pairs, X, cfg, seed=0)
    assert g.shape == (n,) and g.min() >= 0.0
    assert abs(info["loss"] - info["loss_eq3_check"]) < 1e-3 * max(1.0, abs(info["loss"]))


def test_tabular_fit_is_a_constrained_stationary_point():
    pairs = _random_pairs(seed=3)
    for cfg in (GConfig(no_agree="max1"), SWAP, SWAP.with_(g_floor="softplus", l_plus=False)):
        g, info = fit_correction_tabular(pairs, 12, cfg, ridge=1e-2)
        d = build_design(pairs)
        x = g[d.present]
        z = d.dproxy + d.A @ x
        w = _reg_coef(d, cfg) * d.reg_for(cfg) + 1e-2
        grad = d.A.T @ (1 / (1 + np.exp(-z)) - d.y) / d.n_pairs + 2 * w * x
        free = x > 1e-8 if cfg.g_floor != "none" else np.ones_like(x, bool)
        assert np.abs(grad[free]).max() < 1e-5, (cfg, np.abs(grad[free]).max())
        assert (grad[~free] >= -1e-5).all()           # KKT: at the bound the gradient may only point up (descent is blocked)
        assert np.all(g[np.setdiff1d(np.arange(12), d.present)] == 0)


def test_step3_rows_fit_reproduces_the_step2_fit_for_every_variant():
    from tests.test_step3 import GRID, SMALL_G, _grid_pairs
    from src.step3.pbrr import fit_correction_rows

    po, pn = _grid_pairs(np.random.default_rng(0))
    for kw in ({"l_minus_on": "dispreferred"}, {"l_minus_on": "dispreferred", "l_plus": False},
               {"use_regularization": False}):
        cfg = SMALL_G.with_(**kw)
        g_old, info_old = fit_correction(po, transition_features(BASE), cfg, seed=3)
        _, info = fit_correction_rows(pn, GRID, cfg, seed=3)
        s, a, _ = GRID.decode(np.unique(np.concatenate([t.keys for t, _, _ in pn] + [t.keys for _, t, _ in pn])))
        # without any regulariser float32 summation-order differences grow through Adam
        # (max |dg| 0.005 on |g| ~ 1.2, loss equal to 2e-5): same objective, not bit-identical
        tol = 1e-3 if cfg.use_regularization else 1e-2
        assert np.allclose(info["g_rows"], g_old[s * 5 + a], rtol=tol, atol=tol), kw
        assert abs(info["loss"] - info_old["loss"]) < 1e-3 * max(1.0, abs(info_old["loss"])), kw


if __name__ == "__main__":
    run_tests(globals(), "Step 4 -- PBRR variants and the tabular fit")
