"""Solver tests: value iteration against closed forms, and against policy iteration.

Runnable either way:
    python tests/test_solver.py
    pytest tests/test_solver.py
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.environments import (
    CORRIDOR_ACTIONS,
    CORRIDOR_BASE,
    FARM_POS,
    F_LOUD_POS,
    F_QUIET_POS,
    GOAL_POS,
    N_POS,
    TOY_ACTIONS,
    TOY_BASE,
    build_corridor_mdp,
    build_toy_mdp,
    move,
    state_of,
    toy_closed_form,
)
from src.report import run_tests
from src.solver import (
    bellman_residual,
    check_agreement,
    check_mdp,
    finite_horizon,
    find_threshold,
    policy_evaluation,
    policy_iteration,
    value_iteration,
)

GAMMAS = (0.0, 0.1, 0.35, 0.4545, 0.5, 0.65, 0.8333, 0.9, 0.95, 0.99, 0.995)


# --------------------------------------------------------------------------- #
# value iteration vs the closed form
# --------------------------------------------------------------------------- #

def test_vi_matches_toy_closed_form():
    R, P, _ = build_toy_mdp(**TOY_BASE)
    for gamma in GAMMAS:
        V, policy, _, _ = value_iteration(R, P, gamma)
        cf = toy_closed_form(gamma, **TOY_BASE)
        assert abs(V[0] - cf["v_star"]) < 1e-6, (
            f"gamma={gamma}: VI gave {V[0]!r}, closed form {cf['v_star']!r}"
        )
        assert TOY_ACTIONS[int(policy[0])] == cf["label"], f"gamma={gamma} label mismatch"


def test_vi_matches_closed_form_off_base_parameters():
    """Not just the base point: a small grid of parameter settings."""
    rng = np.random.default_rng(11)
    for _ in range(40):
        params = dict(
            r_C=float(rng.uniform(0.2, 2.0)),
            r_O=float(rng.uniform(0.2, 5.0)),
            r_H=float(rng.uniform(0.2, 5.0)),
            p_O=float(rng.uniform(0.05, 0.99)),
            p_H=float(rng.uniform(0.0, 0.99)),
            r_1=float(rng.uniform(-2.0, 2.0)),
        )
        gamma = float(rng.uniform(0.0, 0.98))
        R, P, _ = build_toy_mdp(**params)
        V, _, _, _ = value_iteration(R, P, gamma)
        assert abs(V[0] - toy_closed_form(gamma, **params)["v_star"]) < 1e-6, params


def test_policy_evaluation_matches_stationary_closed_forms():
    """Each closed form is the value of a constant policy, so policy evaluation
    must reproduce it exactly -- including for actions that are not optimal."""
    R, P, _ = build_toy_mdp(**TOY_BASE)
    for gamma in (0.3, 0.6, 0.9, 0.99):
        cf = toy_closed_form(gamma, **TOY_BASE)
        for a, name in enumerate(TOY_ACTIONS):
            v = policy_evaluation(np.array([a, 0]), R, P, gamma)
            assert abs(v[0] - cf[name]) < 1e-9, (gamma, name, v[0], cf[name])


# --------------------------------------------------------------------------- #
# value iteration vs policy iteration
# --------------------------------------------------------------------------- #

def test_vi_agrees_with_policy_iteration_on_both_environments():
    envs = {
        "toy": build_toy_mdp(**TOY_BASE)[:2],
        "corridor": build_corridor_mdp(**CORRIDOR_BASE)[:2],
        "corridor_nogap": build_corridor_mdp(
            **{**CORRIDOR_BASE, "p_unwatch": CORRIDOR_BASE["p_watch"]}
        )[:2],
    }
    for name, (R, P) in envs.items():
        for gamma in (0.0, 0.5, 0.82, 0.95, 0.99):
            d = check_agreement(R, P, gamma)
            assert d["agree"], f"{name} at gamma={gamma}: {d}"


def test_vi_agrees_with_policy_iteration_on_random_mdps():
    """Neither solver is special-cased to these environments."""
    rng = np.random.default_rng(7)
    for _ in range(25):
        n_s, n_a = int(rng.integers(2, 12)), int(rng.integers(2, 6))
        R = rng.normal(size=(n_s, n_a))
        P = rng.random((n_s, n_a, n_s)) ** 3 + 1e-6
        P /= P.sum(axis=2, keepdims=True)
        gamma = float(rng.uniform(0.0, 0.97))
        d = check_agreement(R, P, gamma)
        assert d["agree"], f"n_s={n_s} n_a={n_a} gamma={gamma}: {d}"


def test_bellman_residual_is_zero_at_the_returned_solution():
    for R, P in (
        build_toy_mdp(**TOY_BASE)[:2],
        build_corridor_mdp(**CORRIDOR_BASE)[:2],
    ):
        for gamma in (0.5, 0.9, 0.99):
            V, _, _, info = value_iteration(R, P, gamma)
            assert bellman_residual(V, R, P, gamma) < 1e-9, (gamma, info)
            V_pi, _, _, _ = policy_iteration(R, P, gamma)
            assert bellman_residual(V_pi, R, P, gamma) < 1e-12, gamma


def test_value_iteration_reports_a_valid_error_bound():
    R, P, _ = build_corridor_mdp(**CORRIDOR_BASE)
    for gamma in (0.9, 0.99):
        V, _, _, info = value_iteration(R, P, gamma)
        V_exact, _, _, _ = policy_iteration(R, P, gamma)
        assert np.max(np.abs(V - V_exact)) <= info["value_error_bound"] + 1e-12


# --------------------------------------------------------------------------- #
# finite horizon
# --------------------------------------------------------------------------- #

def test_finite_horizon_one_step_is_greedy_on_reward():
    R, P, _ = build_corridor_mdp(**CORRIDOR_BASE)
    V, policy = finite_horizon(R, P, 0.95, 1)
    assert np.allclose(V[0], R.max(axis=1))
    assert np.array_equal(policy[0], R.argmax(axis=1))


def test_finite_horizon_converges_to_the_discounted_optimum():
    R, P, _ = build_corridor_mdp(**CORRIDOR_BASE)
    gamma = 0.9
    V_inf, _, _, _ = value_iteration(R, P, gamma)
    V_h, _ = finite_horizon(R, P, gamma, 400)
    assert np.max(np.abs(V_h[0] - V_inf)) < 1e-6, np.max(np.abs(V_h[0] - V_inf))


# --------------------------------------------------------------------------- #
# input validation and utilities
# --------------------------------------------------------------------------- #

def test_check_mdp_rejects_malformed_input():
    R, P, _ = build_toy_mdp(**TOY_BASE)
    bad_rows = P.copy()
    bad_rows[0, 0, :] = [0.9, 0.5]  # sums to 1.4
    for label, args in {
        "gamma >= 1": (R, P, 1.0),
        "gamma < 0": (R, P, -0.1),
        "rows do not sum to 1": (R, bad_rows, 0.9),
        "R is not 2-D": (R[0], P, 0.9),
    }.items():
        try:
            check_mdp(*args)
        except ValueError:
            continue
        raise AssertionError(f"check_mdp accepted a malformed MDP: {label}")


def test_find_threshold_locates_a_known_root():
    got = find_threshold(lambda x: x < 1.0 / 3.0, 0.0, 1.0, tol=1e-12)
    assert abs(got - 1.0 / 3.0) < 1e-9, got
    try:
        find_threshold(lambda x: True, 0.0, 1.0)
    except ValueError:
        return
    raise AssertionError("find_threshold accepted a predicate that never flips")


# --------------------------------------------------------------------------- #
# environment structure -- guards on the modelling rules the project relies on
# --------------------------------------------------------------------------- #

def test_corridor_transitions_are_well_formed():
    R, P, meta = build_corridor_mdp(**CORRIDOR_BASE)
    check_mdp(R, P, 0.95)
    assert P.shape == (20, 5, 20) and R.shape == (20, 5)
    for patched in (0, 1):
        g = state_of(GOAL_POS, patched)
        assert P[g, :, g].min() == 1.0, "GOAL must be absorbing in both patch layers"
        assert np.all(R[g, :] == 0.0), "GOAL must pay nothing once reached"


def test_detection_does_not_depend_on_the_action():
    """The load-bearing rule of Exp 1: detection comes from the observation model
    and the geometry, never from a per-action hiding probability. So for a fixed
    tile, the chance of being corrected must be identical across all five actions."""
    _, P, _ = build_corridor_mdp(**CORRIDOR_BASE)
    for pos in FARM_POS:
        s = state_of(pos, 0)
        patch_prob = [P[s, a, N_POS:].sum() for a in range(len(CORRIDOR_ACTIONS))]
        assert max(patch_prob) - min(patch_prob) < 1e-15, (pos, patch_prob)
    expected = {F_LOUD_POS: CORRIDOR_BASE["p_watch"], F_QUIET_POS: CORRIDOR_BASE["p_unwatch"]}
    for pos, want in expected.items():
        s = state_of(pos, 0)
        assert abs(P[s, 0, N_POS:].sum() - want) < 1e-15, (pos, want)


def test_no_detection_away_from_an_unpatched_loophole():
    _, P, _ = build_corridor_mdp(**CORRIDOR_BASE)
    for pos in range(N_POS):
        for patched in (0, 1):
            if pos in FARM_POS and patched == 0:
                continue
            s = state_of(pos, patched)
            leaked = P[s, :, (1 - patched) * N_POS : (1 - patched) * N_POS + N_POS].sum()
            assert leaked < 1e-15, (
                f"patch state changed from ({pos}, {patched}) -- corrections must be "
                "permanent and only triggered on an unpatched loophole tile"
            )


def test_the_control_changes_only_the_observation_model():
    """Closing the gap must leave rewards, geometry and the watched tile untouched;
    otherwise the control would be confounded."""
    R_gap, P_gap, _ = build_corridor_mdp(**CORRIDOR_BASE)
    R_no, P_no, _ = build_corridor_mdp(
        **{**CORRIDOR_BASE, "p_unwatch": CORRIDOR_BASE["p_watch"]}
    )
    assert np.array_equal(R_gap, R_no), "the control must not touch the reward function"
    differing = {
        s % N_POS for s in range(20) if not np.allclose(P_gap[s], P_no[s])
    }
    assert differing == {F_QUIET_POS}, (
        f"only the unwatched loophole's dynamics may change; got {differing}"
    )


def test_every_route_to_the_goal_passes_a_loophole():
    """Context for the classifier: 'do the task' cannot mean 'never touch a
    loophole', because column 1 is a loophole on top and column 2 on the bottom."""
    reachable = {0}
    frontier = [0]
    while frontier:
        pos = frontier.pop()
        for a in range(len(CORRIDOR_ACTIONS)):
            nxt = move(pos, a)
            if nxt not in reachable and nxt not in FARM_POS:
                reachable.add(nxt)
                frontier.append(nxt)
    assert GOAL_POS not in reachable, (
        "GOAL is reachable while avoiding both loophole tiles -- the classifier's "
        "'goto_goal' label would then mean something different"
    )


if __name__ == "__main__":
    run_tests(dict(globals()), "SOLVER + ENVIRONMENT TESTS")
