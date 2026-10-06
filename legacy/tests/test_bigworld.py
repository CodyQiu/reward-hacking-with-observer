"""Exp 4 structural and convergence checks.

Run directly with::

    .venv/bin/python tests/test_bigworld.py
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.bigworld import (
    CELL_INDEX,
    N_ACTIONS,
    N_FREE,
    N_TRANSITIONS,
    START,
    dp_optimal_policy,
    live_exploits,
    policy_true_return,
)
from src.bigworld_pbrr import bigworld_pbrr_dp, expand_correction, make_trajectory
from src.pbrr import build_design, design_loss_and_grad
from src.report import run_tests


def test_state_correction_is_shared_across_all_actions():
    params = np.arange(N_FREE, dtype=float)
    full = expand_correction(params, "state")
    assert full.shape == (N_TRANSITIONS,)
    i = CELL_INDEX[START]
    assert np.all(full[i * N_ACTIONS : (i + 1) * N_ACTIONS] == params[i])


def test_state_trajectory_uses_one_parameter_per_visited_state():
    traj = make_trajectory([START, START], [4, 3], correction_scope="state")
    assert traj.n_transitions == N_FREE
    assert np.array_equal(traj.g_idx, [CELL_INDEX[START], CELL_INDEX[START]])


def test_margin_objective_gradient_matches_finite_differences():
    a = make_trajectory([START, START], [4, 4], correction_scope="state")
    b = make_trajectory([START], [3], correction_scope="state")
    design = build_design([(0, 1, 1.0)], [a, b])
    g = np.linspace(-0.2, 0.2, N_FREE)
    _, grad, _ = design_loss_and_grad(g, design, preference_margin=10.0)
    eps = 1e-6
    for j in np.flatnonzero(design.A[0])[:2]:
        d = np.zeros_like(g)
        d[j] = eps
        lp, _, _ = design_loss_and_grad(g + d, design, preference_margin=10.0)
        lm, _, _ = design_loss_and_grad(g - d, design, preference_margin=10.0)
        assert abs(grad[j] - (lp - lm) / (2 * eps)) < 1e-5


def test_structured_margin_pbrr_converges_and_stays_repaired():
    out = bigworld_pbrr_dp(
        n_iterations=15,
        k=19,
        seed=0,
        lam=1.0,
        weight_decay=0.01,
        correction_scope="state",
        preference_margin=10.0,
    )
    tail = [h["true_return"] for h in out["history"][-5:]]
    assert tail == [12.0] * 5, tail
    assert policy_true_return(dp_optimal_policy(out["g"])) == 12.0
    assert all(v <= 0.0 for v in live_exploits(out["g"]).values())


def test_structured_margin_pbrr_repairs_all_five_checked_seeds():
    for seed in range(5):
        out = bigworld_pbrr_dp(
            n_iterations=15,
            k=19,
            seed=seed,
            lam=1.0,
            weight_decay=0.01,
            correction_scope="state",
            preference_margin=10.0,
        )
        assert policy_true_return(dp_optimal_policy(out["g"])) == 12.0, seed
        assert all(v <= 0.0 for v in live_exploits(out["g"]).values()), seed


if __name__ == "__main__":
    run_tests(dict(globals()), "EXP 4 BIG-WORLD VALIDATION TESTS")
