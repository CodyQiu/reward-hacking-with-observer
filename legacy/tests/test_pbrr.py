"""Exp 3 (PBRR) validation tests.

    python tests/test_pbrr.py
    pytest tests/test_pbrr.py
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.dp_reference import bfs_dist, finite_horizon_dp, extract_path
from src.pbrr import (
    N_TRANSITIONS,
    PUSH2ZERO,
    Trajectory,
    _reg_targets,
    build_design,
    design_loss_and_grad,
    fit_g,
    g_return,
    ideal_g,
    loss_and_grad,
    make_trajectory,
    partition_pairs,
    transition_index,
    TRANSITION_TRIPLES,
)
from src.pbrr_loop import (
    dp_optimal_policy,
    make_eps_greedy_reference,
    pbrr_run,
    policy_true_return,
    repaired_reward_fn,
    rollout_stochastic_policy,
    sample_pairs,
)
from src.pbrr_minimal import MINIMAL_MDPS, run_minimal_pbrr
from src.report import run_tests
from src.waypoint_env import GOAL, START, WAYPOINT, WaypointFarmEnv, r_proxy, r_true


def _toy_pairs(seed=0, k=6):
    """A small, genuinely mixed preference set (some agree, some disagree, some tie)."""
    rng = np.random.default_rng(seed)
    trajs = []
    a = [rollout_stochastic_policy(make_eps_greedy_reference(0.2), rng) for _ in range(k)]
    b = [rollout_stochastic_policy(make_eps_greedy_reference(0.9), rng) for _ in range(k)]
    pairs = sample_pairs(a, b, trajs, rng)
    return pairs, trajs


# --------------------------------------------------------------------------- #
# the analytic anchor
# --------------------------------------------------------------------------- #

def test_ideal_correction_recovers_the_true_reward_exactly():
    g = ideal_g()
    worst = max(
        abs(r_proxy(p, a, False) + g[transition_index(p, a)] - r_true(p, a))
        for p, a, _ in TRANSITION_TRIPLES
    )
    assert worst == 0.0, worst
    assert int((g != 0).sum()) == 5, "only the 5 transitions out of the waypoint"


def test_dp_on_the_ideal_correction_gives_the_honest_optimum():
    V, policy = finite_horizon_dp(repaired_reward_fn(ideal_g()))
    path, _ = extract_path(policy)
    assert abs(V[0, 0] - 2.0) < 1e-9, V[0, 0]
    assert len(path) - 1 == 8, len(path) - 1
    assert abs(policy_true_return(policy) - 2.0) < 1e-9


def test_uncorrected_proxy_farms():
    """The null: with g = 0 the proxy optimum is to farm, badly."""
    policy = dp_optimal_policy(np.zeros(N_TRANSITIONS))
    true_ret = policy_true_return(policy)
    assert true_ret < -20.0, f"expected heavy true-reward damage, got {true_ret}"


# --------------------------------------------------------------------------- #
# bookkeeping
# --------------------------------------------------------------------------- #

def test_g_return_matches_the_per_step_sum():
    pairs, trajs = _toy_pairs()
    rng = np.random.default_rng(1)
    g = rng.standard_normal(N_TRANSITIONS)
    for traj in trajs[:8]:
        by_step = sum(g[transition_index(p, a)] for p, a in zip(traj.states, traj.actions))
        assert abs(g_return(g, traj) - by_step) < 1e-12
        assert abs(float(traj.counts @ g) - by_step) < 1e-12


def test_proxy_return_is_consistent_with_the_env():
    """A Trajectory's proxy return must equal what the env would accumulate."""
    rng = np.random.default_rng(3)
    env = WaypointFarmEnv(monitor="flat", h_flat=0.0, seed=0)
    env.reset(seed=0)
    states, actions, total = [], [], 0.0
    for _ in range(12):
        a = int(rng.integers(0, 5))
        states.append(env.pos)
        actions.append(a)
        _, reward, term, trunc, _ = env.step(a)
        total += reward
        if term or trunc:
            break
    traj = make_trajectory(states, actions)
    assert abs(traj.proxy_return - total) < 1e-9, (traj.proxy_return, total)


# --------------------------------------------------------------------------- #
# the D+/D- partition and the two ridge terms
# --------------------------------------------------------------------------- #

def test_partition_matches_the_sign_condition():
    pairs, trajs = _toy_pairs()
    agree, disagree = partition_pairs(pairs, trajs)
    assert len(agree) + len(disagree) == len(pairs)
    for k in agree:
        i, j, mu = pairs[k]
        assert mu != 0.5
        assert np.sign(trajs[j].proxy_return - trajs[i].proxy_return) == np.sign(mu - 0.5)
    for k in disagree:
        i, j, mu = pairs[k]
        if mu == 0.5:
            continue
        assert np.sign(trajs[j].proxy_return - trajs[i].proxy_return) != np.sign(mu - 0.5)


def test_ties_never_land_in_the_agree_set():
    t = [
        Trajectory([START], [0], 5.0, 1.0, g_idx=[0], n_transitions=3),
        Trajectory([START], [1], 1.0, 1.0, g_idx=[1], n_transitions=3),
    ]
    agree, disagree = partition_pairs([(0, 1, 0.5)], t)
    assert agree == [] and disagree == [0]


def test_L_minus_penalises_only_the_preferred_trajectory():
    """The asymmetry is the whole mechanism: on a misranked pair only the preferred
    trajectory's g is pushed to zero, which forces 'lower the bad'."""
    t = [
        Trajectory([START], [0], 10.0, 1.0, g_idx=[0], n_transitions=3),  # proxy loves it
        Trajectory([START], [1], 1.0, 9.0, g_idx=[1], n_transitions=3),   # truth loves it
    ]
    pairs = [(0, 1, 1.0)]                       # mu=1 -> tau_2 preferred
    agree, disagree = partition_pairs(pairs, t)
    assert agree == [] and disagree == [0], "proxy prefers tau_1, human prefers tau_2"
    targets = _reg_targets(pairs, agree, disagree, "pref_only")
    assert targets == [(1, "-")], f"only the preferred trajectory, got {targets}"


def test_L_plus_penalises_both_trajectories_of_an_agreeing_pair():
    t = [
        Trajectory([START], [0], 10.0, 9.0, g_idx=[0], n_transitions=3),
        Trajectory([START], [1], 1.0, 1.0, g_idx=[1], n_transitions=3),
    ]
    pairs = [(0, 1, 0.0)]                       # mu=0 -> tau_1 preferred; proxy agrees
    agree, disagree = partition_pairs(pairs, t)
    assert agree == [0] and disagree == []
    targets = _reg_targets(pairs, agree, disagree, "pref_only")
    assert sorted(targets) == [(0, "+"), (1, "+")], targets


def test_lambda_schedule_is_ten_over_d_plus_and_decays():
    pairs, trajs = _toy_pairs()
    design = build_design(pairs, trajs)
    _, _, parts = design_loss_and_grad(np.zeros(N_TRANSITIONS), design)
    assert abs(parts["lam_eff"] - PUSH2ZERO / max(1, design.n_agree)) < 1e-12
    # more agreeing pairs -> weaker regulariser
    small = build_design(pairs[:8], trajs)
    if small.n_agree < design.n_agree and small.n_agree > 0:
        _, _, p_small = design_loss_and_grad(np.zeros(N_TRANSITIONS), small)
        assert p_small["lam_eff"] > parts["lam_eff"]


# --------------------------------------------------------------------------- #
# the objective: two implementations, and calculus
# --------------------------------------------------------------------------- #

def test_vectorised_objective_matches_the_reference_implementation():
    pairs, trajs = _toy_pairs()
    rng = np.random.default_rng(5)
    g = 0.5 * rng.standard_normal(N_TRANSITIONS)
    for variant in ("code", "paper"):
        for use_reg in (True, False):
            design = build_design(pairs, trajs, variant=variant)
            l_vec, g_vec, _ = design_loss_and_grad(g, design, use_regularization=use_reg)
            l_ref, g_ref = loss_and_grad(
                g, pairs, trajs, use_regularization=use_reg, variant=variant
            )
            assert abs(l_vec - l_ref) < 1e-10, (variant, use_reg, l_vec, l_ref)
            assert np.abs(g_vec - g_ref).max() < 1e-10, (variant, use_reg)


def test_gradient_matches_finite_differences():
    pairs, trajs = _toy_pairs()
    rng = np.random.default_rng(7)
    g = 0.3 * rng.standard_normal(N_TRANSITIONS)
    for variant in ("code", "paper"):
        design = build_design(pairs, trajs, variant=variant)
        _, grad, _ = design_loss_and_grad(g, design)
        h = 1e-6
        for k in rng.choice(N_TRANSITIONS, 10, replace=False):
            e = np.zeros(N_TRANSITIONS)
            e[k] = h
            lp, _, _ = design_loss_and_grad(g + e, design)
            lm, _, _ = design_loss_and_grad(g - e, design)
            assert abs((lp - lm) / (2 * h) - grad[k]) < 1e-6, (variant, k)


def test_fit_converges_and_is_init_independent():
    """Convex objective: different starting points must reach the same optimum."""
    pairs, trajs = _toy_pairs()
    g1, i1 = fit_g(pairs, trajs, seed=0)
    g2, i2 = fit_g(pairs, trajs, seed=1, init=0.5 * np.ones(N_TRANSITIONS))
    assert i1["grad_norm"] < 1e-3, i1
    assert i2["grad_norm"] < 1e-3, i2
    assert abs(i1["loss"] - i2["loss"]) < 1e-4, (i1["loss"], i2["loss"])


# --------------------------------------------------------------------------- #
# the paper's own minimal MDPs (Appendix H, Figure 7)
# --------------------------------------------------------------------------- #

def test_minimal_mdp1_is_repaired_by_a_single_preference():
    """Theorem H.1: PBRR recovers an optimal policy after O(1) preferences.

    This is the sharpest available check that L- is wired up correctly -- it only
    holds if the update decrements the dispreferred transition while leaving the
    preferred one alone.
    """
    for lam in (10.0, 1.0, 0.1):
        out = run_minimal_pbrr("MDP1", n_iterations=4, c1=0.0, lam=lam)
        assert out["history"][0]["is_optimal"], f"lam={lam}: not optimal after 1 preference"


def test_minimal_mdp2_stalls_without_the_fallback():
    """The paper's stated C_1 = 0 failure: PBRR beats pi_ref but is not optimal."""
    out = run_minimal_pbrr("MDP2", n_iterations=8, c1=0.0, lam=10.0)
    assert not any(r["is_optimal"] for r in out["history"])
    final = out["history"][-1]["induced_true_return"]
    ref_true = MINIMAL_MDPS["MDP2"]["true"][2]      # pi_ref visits s3
    assert final > ref_true, "Theorem 4.3: must still beat the reference policy"
    assert final < max(MINIMAL_MDPS["MDP2"]["true"]), "but must not be optimal"


def test_minimal_mdp2_needs_both_the_fallback_and_a_decayed_lambda():
    """The fallback surfaces the right comparison, but L+ has to be weak enough to
    act on it -- which is why Assumption 4.5 requires lambda -> 0."""
    stuck = run_minimal_pbrr("MDP2", n_iterations=8, c1=1.0, lam=10.0)
    assert not any(r["is_optimal"] for r in stuck["history"])
    fixed = run_minimal_pbrr("MDP2", n_iterations=8, c1=1.0, lam=0.01)
    assert any(r["is_optimal"] for r in fixed["history"])
    # and the fallback is load-bearing: same lambda without it still fails
    no_fb = run_minimal_pbrr("MDP2", n_iterations=8, c1=0.0, lam=0.01)
    assert not any(r["is_optimal"] for r in no_fb["history"])


# --------------------------------------------------------------------------- #
# end to end, and the control the whole experiment rests on
# --------------------------------------------------------------------------- #

def test_pbrr_repairs_the_waypoint_proxy():
    out = pbrr_run(make_eps_greedy_reference(0.3), n_iterations=4, k=12, seed=0)
    finals = [h["true_return"] for h in out["history"]]
    assert max(finals) > 1.99, f"PBRR never reached the honest optimum: {finals}"


def test_eq1_alone_does_not_repair_it():
    """The paper's §5.4 / Appendix G.3 ablation, in our environment."""
    out = pbrr_run(
        make_eps_greedy_reference(0.3), n_iterations=4, k=12, seed=0,
        use_regularization=False,
    )
    finals = [h["true_return"] for h in out["history"]]
    assert max(finals) < 1.99, f"Eq 1 should NOT reach the optimum, got {finals}"


def test_random_labels_control():
    """With the preference labels destroyed, PBRR must not repair anything. This is
    what shows the labels rather than the regulariser are doing the work.

    Labels are drawn independently of the trajectories. Permuting the real labels is
    NOT sufficient: within an iteration nearly every pair carries the same label, so
    a permutation is close to a no-op and the "control" still repairs the reward --
    which it did, before this was fixed.
    """
    for seed in (0, 1, 2):
        out = pbrr_run(
            make_eps_greedy_reference(0.3), n_iterations=4, k=12, seed=seed,
            randomize_labels=True,
        )
        finals = [h["true_return"] for h in out["history"]]
        assert max(finals) < 1.99, f"random labels repaired the reward (seed {seed}): {finals}"


def test_env_correction_hook_defaults_to_exp2_behaviour():
    env = WaypointFarmEnv(monitor="suspicion", seed=0)
    assert env.correction is None, "Exp 2 semantics must be the default"
    # with a correction supplied the bonus stays live and g is added on top
    g = ideal_g()
    env2 = WaypointFarmEnv(monitor="flat", h_flat=0.0, seed=0, correction=g)
    env2.reset(seed=0)
    env2.pos = WAYPOINT
    _, reward, _, _, info = env2.step(4)
    assert abs(reward - info["true_reward"]) < 1e-12, (
        "r_proxy + ideal g must equal the true reward, so standing on the waypoint "
        f"costs -1; got {reward}"
    )


def test_second_bonus_tile_is_equally_attractive():
    """Geometry for the generalisation phase: the unseen tile must sit on a shortest
    path too, or a failure to farm it would be about distance, not about g."""
    d_goal = bfs_dist(GOAL)
    for tile in ((4, 0), (0, 4)):
        d_tile = bfs_dist(tile)
        assert d_tile[START] + d_goal[tile] == d_goal[START] == 8, tile
        assert d_tile[START] == bfs_dist(WAYPOINT)[START] == 4, tile


if __name__ == "__main__":
    run_tests(dict(globals()), "EXP 3 (PBRR) VALIDATION TESTS")
