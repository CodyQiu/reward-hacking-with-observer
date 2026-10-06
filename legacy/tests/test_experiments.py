"""The published acceptance numbers, as tests.

Every number asserted here also appears in the experiment scripts' output. Keeping
a copy in the test suite means a refactor cannot quietly move a threshold: these
run in seconds because they recompute only the numbers, not the figures.

    python tests/test_experiments.py
    pytest tests/test_experiments.py
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from experiments.exp1b_correction_loop import PROMPT_STEPS, simulate_episodes
from src.environments import (
    CORRIDOR_BASE,
    F_LOUD_POS,
    F_QUIET_POS,
    START_POS,
    TOY_ACTIONS,
    TOY_BASE,
    build_corridor_mdp,
    build_toy_mdp,
    classify_corridor_policy,
    state_of,
)
from src.report import run_tests
from src.solver import find_threshold, policy_iteration, value_iteration

GAMMA_HIGH = 0.95


def toy_label(gamma, **overrides):
    R, P, _ = build_toy_mdp(**{**TOY_BASE, **overrides})
    _, policy, _, _ = value_iteration(R, P, gamma)
    return TOY_ACTIONS[int(policy[0])]


def corridor(gamma=GAMMA_HIGH, **overrides):
    R, P, _ = build_corridor_mdp(**{**CORRIDOR_BASE, **overrides})
    V, policy, Q, _ = policy_iteration(R, P, gamma)
    out = classify_corridor_policy(policy)
    out.update(V=V, policy=policy, Q=Q, R=R, P=P)
    return out


# --------------------------------------------------------------------------- #
# Exp 0 acceptance numbers
# --------------------------------------------------------------------------- #

def test_exp0_phase_boundaries_in_gamma():
    g_oh = find_threshold(lambda g: toy_label(g) == "exploit_open", 0.05, 0.6, tol=1e-9)
    g_hc = find_threshold(lambda g: toy_label(g) == "exploit_hide", 0.6, 0.95, tol=1e-9)
    assert abs(g_oh - 1.0 / 2.2) < 1e-6, f"open->hide at {g_oh}, expected {1 / 2.2}"
    assert abs(g_hc - 1.0 / 1.2) < 1e-6, f"hide->comply at {g_hc}, expected {1 / 1.2}"
    assert abs(g_oh - 0.4545) < 5e-4 and abs(g_hc - 0.8333) < 5e-4


def test_exp0_all_three_regimes_are_present():
    assert toy_label(0.30) == "exploit_open"
    assert toy_label(0.60) == "exploit_hide"
    assert toy_label(0.95) == "comply"


def test_exp0_control_no_detection_gap_kills_the_hide_band():
    labels = {toy_label(g, p_H=TOY_BASE["p_O"]) for g in np.linspace(0.01, 0.995, 300)}
    assert "exploit_hide" not in labels, (
        f"hiding won somewhere with no detection gap: {labels} -- implementation bug"
    )
    assert labels == {"exploit_open", "comply"}, labels


def test_exp0_control_non_punitive_correction_kills_the_comply_band():
    labels = {toy_label(g, r_1=TOY_BASE["r_C"]) for g in np.linspace(0.01, 0.995, 300)}
    assert "comply" not in labels, labels


# --------------------------------------------------------------------------- #
# Exp 1 acceptance numbers
# --------------------------------------------------------------------------- #

def test_exp1_values_with_the_detection_gap():
    r = corridor()
    v_quiet = r["V"][state_of(F_QUIET_POS, 0)]
    v_loud = r["V"][state_of(F_LOUD_POS, 0)]
    assert abs(v_quiet - 11.97) < 5e-3, v_quiet
    assert abs(v_loud - 8.03) < 5e-3, v_loud
    assert v_quiet > v_loud


def test_exp1_greedy_path_detours_through_the_unwatched_row():
    r = corridor()
    assert r["path_rc"][:4] == [(0, 0), (1, 0), (1, 1), (1, 2)], r["path_rc"][:6]
    assert r["detour"] and r["label"] == "farm_quiet"


def test_exp1_control_no_gap_equalises_the_two_loopholes():
    r = corridor(p_unwatch=CORRIDOR_BASE["p_watch"])
    v_quiet = r["V"][state_of(F_QUIET_POS, 0)]
    v_loud = r["V"][state_of(F_LOUD_POS, 0)]
    assert abs(v_quiet - 5.80) < 5e-3, v_quiet
    assert abs(v_loud - 5.80) < 5e-3, v_loud
    assert abs(v_quiet - v_loud) < 1e-12, (
        f"the loopholes differ by {v_quiet - v_loud} with no observation gap"
    )


def test_exp1_control_no_gap_removes_the_detour_at_every_gamma():
    for gamma in np.linspace(0.5, 0.995, 120):
        r = corridor(gamma=float(gamma), p_unwatch=CORRIDOR_BASE["p_watch"])
        assert not r["detour"], f"detoured at gamma={gamma} with no gap: {r['path_rc']}"
        assert r["label"] != "farm_quiet", f"hid at gamma={gamma} with no gap"


def test_exp1_gamma_phase_boundaries():
    g_farm = find_threshold(
        lambda g: corridor(gamma=g)["label"] == "goto_goal", 0.6, 0.9, tol=1e-7
    )
    g_stealth = find_threshold(
        lambda g: not corridor(gamma=g)["detour"], 0.83, 0.95, tol=1e-7
    )
    assert abs(g_farm - 0.82) < 5e-3, f"do-task -> farm at {g_farm}"
    assert g_farm < g_stealth, (g_farm, g_stealth)
    assert abs(g_stealth - 0.8858) < 5e-3, f"stealth onset at {g_stealth}"


def test_exp1_a_punitive_correction_does_not_deter():
    """The penalty is never actually paid: past a point the optimal policy farms
    hit-and-run and is never standing on a loophole when the patch lands."""
    v = [corridor(penalty=p)["V"][state_of(F_QUIET_POS, 0)] for p in (-12.0, -50.0, -400.0)]
    assert max(v) - min(v) < 1e-9, v
    assert all(corridor(penalty=p)["label"] != "goto_goal" for p in (-5.0, -30.0, -400.0))


def test_exp1_raising_the_task_reward_does_deter():
    threshold = find_threshold(
        lambda v: corridor(R_goal=float(v))["label"] != "goto_goal", 5.0, 30.0, tol=1e-5
    )
    assert 17.0 < threshold < 18.0, threshold
    assert corridor(R_goal=20.0)["label"] == "goto_goal"
    assert corridor(R_goal=10.0)["label"] != "goto_goal"


# --------------------------------------------------------------------------- #
# Exp 1b -- the episodic correction loop (small, seeded run)
# --------------------------------------------------------------------------- #

def test_exp1b_promptness_separates_hiding_from_the_control():
    horizon, n_episodes, n_runs, seed = 25, 3, 200, 4242
    out = {}
    for tag, overrides in {
        "hiding": {},
        "control": {"p_unwatch": CORRIDOR_BASE["p_watch"]},
    }.items():
        R, P, _ = build_corridor_mdp(**{**CORRIDOR_BASE, **overrides})
        _, policy, _, _ = policy_iteration(R, P, GAMMA_HIGH)
        out[tag] = simulate_episodes(
            R, P, policy, horizon, n_episodes, n_runs, seed
        )
    assert out["hiding"]["prompt_rate"][0] < 0.02, out["hiding"]["prompt_rate"][0]
    assert out["control"]["prompt_rate"][0] > 0.75, out["control"]["prompt_rate"][0]
    # and the exploit itself: farmed steps in the first episode
    assert (
        out["hiding"]["farm_steps"][:, 0].mean()
        > 4.0 * out["control"]["farm_steps"][:, 0].mean()
    ), (
        out["hiding"]["farm_steps"][:, 0].mean(),
        out["control"]["farm_steps"][:, 0].mean(),
    )


def test_exp1b_raw_completion_would_not_separate_them():
    """Guard on the metric choice: if someone swaps promptness back out for raw
    completion, this documents why that fails."""
    horizon, n_episodes, n_runs, seed = 25, 3, 200, 4242
    rates = {}
    for tag, overrides in {
        "hiding": {},
        "control": {"p_unwatch": CORRIDOR_BASE["p_watch"]},
    }.items():
        R, P, _ = build_corridor_mdp(**{**CORRIDOR_BASE, **overrides})
        _, policy, _, _ = policy_iteration(R, P, GAMMA_HIGH)
        sim = simulate_episodes(R, P, policy, horizon, n_episodes, n_runs, seed)
        rates[tag] = sim["completed"].mean()
    assert rates["hiding"] > 0.8 and rates["control"] > 0.8, rates
    assert PROMPT_STEPS < horizon


if __name__ == "__main__":
    run_tests(dict(globals()), "ACCEPTANCE-NUMBER TESTS (Exp 0, Exp 1, Exp 1b)")
