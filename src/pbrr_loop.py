"""PBRR Algorithm 1: the outer repair loop.

Each iteration:

  4. compute pi*_{r_hat_t} for the repaired reward r_proxy + g_t
  5. set (pi_1, pi_2) = (pi*_{r_hat_t}, pi_ref)
  6-11. if C_1 > 0, optionally replace that pair with the maximum-divergence pair
        from the non-dominated policy set Pi_t
  12. roll out k trajectories from each policy and form all k^2 cross pairs
  13. label them and append to the accumulated dataset D
  14. refit g from scratch on ALL of D  (Appendix E.2)

Two things this module exploits that the paper's own experiments could not:

* pi*_{r_hat_t} is computed **exactly** by finite-horizon DP rather than by
  training a policy, so the paper's footnote-3 caveat ("not guaranteed to find an
  optimal policy") does not apply.
* The non-dominated policy set Pi_t and the maximum-divergence pair are tractable
  at this size. The paper sets C_1 = 0 throughout its experiments (Assumption 4.7,
  §5) precisely because they are not tractable in its domains, so the fallback is
  specified there but never run.

Preference labels come from a Boltzmann model on the **ground-truth** return, as in
Appendix E.5. That is the only place the true reward is ever touched, and only as a
labeller -- g never sees its numeric values.
"""

import numpy as np

from .dp_reference import finite_horizon_dp, step_toward
from .pbrr import (
    N_ACTIONS,
    N_TRANSITIONS,
    Trajectory,
    count_vector,
    fit_g,
    make_trajectory,
    transition_index,
)
from .waypoint_env import (
    GOAL,
    HORIZON,
    START,
    WAYPOINT,
    move,
    r_proxy,
    r_true,
)

__all__ = [
    "repaired_reward_fn",
    "dp_optimal_policy",
    "rollout_dp_policy",
    "rollout_stochastic_policy",
    "make_eps_greedy_reference",
    "make_random_reference",
    "make_optimal_reference",
    "boltzmann_label",
    "sample_pairs",
    "policy_true_return",
    "pbrr_run",
]


# --------------------------------------------------------------------------- #
# the repaired reward, and its exact optimal policy
# --------------------------------------------------------------------------- #

def repaired_reward_fn(g, bonus=2.0):
    """reward_fn(pos, action) for r_proxy + g, ready for finite_horizon_dp.

    The transition-dependent g needs no special handling because s' = move(s,a):
    the DP already calls reward_fn(pos, action) and looks up V at move(pos, a).
    """
    g = np.asarray(g, dtype=float)

    def fn(pos, action):
        return r_proxy(pos, action, False, bonus) + g[transition_index(pos, action)]

    return fn


def dp_optimal_policy(g, horizon=HORIZON, bonus=2.0):
    """pi*_{r_hat}: exact finite-horizon optimal policy for r_proxy + g."""
    _, policy = finite_horizon_dp(repaired_reward_fn(g, bonus), horizon)
    return policy


def rollout_dp_policy(policy, horizon=HORIZON, start=START, bonus=2.0):
    """Deterministic rollout of a time-indexed DP policy. Returns a Trajectory."""
    from .waypoint_env import CELL_INDEX

    pos, states, actions = start, [], []
    for t in range(horizon):
        a = int(policy[t, CELL_INDEX[pos]])
        states.append(pos)
        actions.append(a)
        pos = move(pos, a)
        if pos == GOAL:
            break
    return make_trajectory(states, actions, bonus)


def rollout_stochastic_policy(action_fn, rng, horizon=HORIZON, start=START, bonus=2.0):
    """Roll out a policy given as action_fn(pos, rng) -> action."""
    pos, states, actions = start, [], []
    for _ in range(horizon):
        a = int(action_fn(pos, rng))
        states.append(pos)
        actions.append(a)
        pos = move(pos, a)
        if pos == GOAL:
            break
    return make_trajectory(states, actions, bonus)


# --------------------------------------------------------------------------- #
# reference policies
# --------------------------------------------------------------------------- #

def make_eps_greedy_reference(eps=0.3):
    """Shortest path to the goal, perturbed with probability eps.

    Reaches the goal and never dwells on the bonus tile, but wastes steps, so its
    true return sits below the honest optimum of +2.0. Theorem 4.3 only guarantees
    PBRR does no worse than the reference, so a deliberately suboptimal reference
    is what makes "does PBRR reach the optimum?" a real question.
    """

    def action_fn(pos, rng):
        if rng.random() < eps:
            return int(rng.integers(0, N_ACTIONS))
        return step_toward(pos, GOAL)

    return action_fn


def _eps_soft(policy, eps, horizon=HORIZON):
    """eps-soft rollout policy from a time-indexed DP table.

    The DP table is indexed by (t, cell); the rollout tracks its own step counter so
    the returned closure has the ``action_fn(pos, rng)`` signature the sampler wants.
    """
    from .waypoint_env import CELL_INDEX

    state = {"t": 0}

    def action_fn(pos, rng):
        t = min(state["t"], horizon - 1)
        state["t"] += 1
        if rng.random() < eps:
            return int(rng.integers(0, N_ACTIONS))
        return int(policy[t, CELL_INDEX[pos]])

    return action_fn


def make_random_reference():
    """Uniform random -- the paper's Appendix K.8 adversarial reference."""

    def action_fn(pos, rng):
        return int(rng.integers(0, N_ACTIONS))

    return action_fn


def make_optimal_reference():
    """The exact 8-step honest route: the easy-case upper bracket."""

    def action_fn(pos, rng):
        return step_toward(pos, GOAL)

    return action_fn


# --------------------------------------------------------------------------- #
# labelling and pair construction
# --------------------------------------------------------------------------- #

def boltzmann_label(traj_a, traj_b, rng, beta=1.0, tie_tol=1e-9):
    """Preference label from a Boltzmann model on the ground-truth return.

    Returns mu in {0, 1, 1/2}: 0 means traj_a preferred, 1 means traj_b, 1/2 means
    indifferent. Exact ties in true return are labelled as indifference rather than
    coin-flipped, because in this environment they are genuine: dwelling k steps on
    the bonus tile and dawdling k steps elsewhere both score 2-k under r_true.
    """
    diff = traj_a.true_return - traj_b.true_return
    if abs(diff) <= tie_tol:
        return 0.5
    p_a = 1.0 / (1.0 + np.exp(-np.clip(beta * diff, -500, 500)))
    return 0.0 if rng.random() < p_a else 1.0


def sample_pairs(trajs_1, trajs_2, trajs, rng, beta=1.0):
    """All k^2 cross pairs between two trajectory sets (Appendix E.5).

    ``trajs`` is the growing global trajectory list; the returned pairs index into
    it. Preferences are elicited over full trajectories, per Appendix A.
    """
    base = len(trajs)
    trajs.extend(trajs_1)
    trajs.extend(trajs_2)
    idx_1 = list(range(base, base + len(trajs_1)))
    idx_2 = list(range(base + len(trajs_1), base + len(trajs_1) + len(trajs_2)))

    pairs = []
    for i in idx_1:
        for j in idx_2:
            pairs.append((i, j, boltzmann_label(trajs[i], trajs[j], rng, beta)))
    return pairs


# --------------------------------------------------------------------------- #
# evaluation
# --------------------------------------------------------------------------- #

def policy_true_return(policy, horizon=HORIZON, start=START):
    """Exact true return of a deterministic time-indexed policy (no sampling)."""
    from .waypoint_env import CELL_INDEX

    pos, total = start, 0.0
    for t in range(horizon):
        a = int(policy[t, CELL_INDEX[pos]])
        total += r_true(pos, a)
        pos = move(pos, a)
        if pos == GOAL:
            break
    return total


def reference_true_return(action_fn, rng, n=2000, horizon=HORIZON, bonus=2.0):
    """Monte Carlo true return of a stochastic reference policy."""
    return float(
        np.mean(
            [
                rollout_stochastic_policy(action_fn, rng, horizon, bonus=bonus).true_return
                for _ in range(n)
            ]
        )
    )


# --------------------------------------------------------------------------- #
# the maximum-divergence fallback (C_1 > 0)
# --------------------------------------------------------------------------- #

def _feature_map(traj):
    """phi(tau): transition visitation counts. The reward is linear in this by
    construction (Assumption 4.1), since r(tau) = <phi(tau), r_vector>."""
    return count_vector(traj)


def feature_covariance(observed_diffs, n_transitions, kappa_lambda=1.0):
    """V_t of Eq 7: regularised covariance of the *observed* pair differences.

    Only pairs that have actually been compared enter V. That is what makes
    V^-1 large in directions the data has not constrained, and hence what makes the
    max-divergence criterion of Eq 10 point at unexplored transitions.
    """
    V = kappa_lambda * np.eye(n_transitions)
    for d in observed_diffs:
        V += np.outer(d, d)
    return V


def max_divergence_pair(candidate_trajs, observed_diffs=(), kappa_lambda=1.0):
    """arg max over candidate pairs of ||phi(t1) - phi(t2)||_{V^-1} (Eq 10).

    At this scale V is a small dense solve, which is exactly why the fallback is
    testable here and not in the paper's own domains (§5: they set C_1 = 0 because
    Pi_t is intractable there).
    """
    feats = [t.counts for t in candidate_trajs]
    n = len(feats)
    n_tr = candidate_trajs[0].n_transitions
    Vinv = np.linalg.pinv(feature_covariance(observed_diffs, n_tr, kappa_lambda))

    best, best_val = (0, min(1, n - 1)), -np.inf
    for i in range(n):
        for j in range(i + 1, n):
            d = feats[i] - feats[j]
            val = float(d @ Vinv @ d)
            if val > best_val:
                best, best_val = (i, j), val
    return best, best_val


# --------------------------------------------------------------------------- #
# Algorithm 1
# --------------------------------------------------------------------------- #

def pbrr_run(
    reference_action_fn,
    n_iterations=8,
    k=19,
    seed=0,
    lam=10.0,
    use_regularization=True,
    variant="code",
    tie_handling="pref_only",
    reg_terms=("+", "-"),
    beta=1.0,
    horizon=HORIZON,
    bonus=2.0,
    c1=0.0,
    proxy_eps=0.05,
    randomize_labels=False,
    verbose=False,
):
    """Run PBRR and return the per-iteration history.

    ``use_regularization=False`` is Eq 1 (the RRM baseline). ``c1 > 0`` enables the
    maximum-divergence fallback.

    ``randomize_labels=True`` is the control that shows the *labels* rather than the
    regulariser are doing the work: each preference is drawn uniformly from {0, 1}
    independently of the trajectories. Note that merely *permuting* the elicited
    labels is NOT a valid control here -- within an iteration almost every pair
    carries the same label (the reference beats the farmer on true return), so a
    permutation of a homogeneous list leaves the data essentially unchanged and the
    "control" still repairs the reward.
    """
    rng = np.random.default_rng(seed)
    trajs = []
    pairs = []
    g = np.zeros(N_TRANSITIONS)
    history = []

    for it in range(n_iterations):
        policy = dp_optimal_policy(g, horizon, bonus)
        proxy_traj = rollout_dp_policy(policy, horizon, bonus=bonus)

        # line 12: k trajectories from each policy. The exact DP policy is
        # deterministic, so k identical rollouts would make the k^2 preferences
        # carry only k distinct contrasts. The paper's pi*_{r_hat} is a trained
        # network and therefore stochastic, so we roll out an eps-soft version to
        # match; evaluation below still uses the exact deterministic policy.
        set_1 = [
            rollout_stochastic_policy(
                _eps_soft(policy, proxy_eps), rng, horizon, bonus=bonus
            )
            for _ in range(k)
        ]
        set_2 = [
            rollout_stochastic_policy(reference_action_fn, rng, horizon, bonus=bonus)
            for _ in range(k)
        ]

        used_fallback = False
        if c1 > 0.0:
            # lines 6-11: is the default pair divergent enough? Compare against the
            # best pair available among the candidate trajectories.
            candidates = [proxy_traj] + set_2
            (bi, bj), best_val = max_divergence_pair(candidates)
            d = _feature_map(proxy_traj) - _feature_map(set_2[0])
            V = np.eye(N_TRANSITIONS)
            default_val = float(d @ np.linalg.pinv(V) @ d)
            if c1 * default_val <= best_val:
                used_fallback = True
                set_1 = [candidates[bi] for _ in range(k)]
                set_2 = [candidates[bj] for _ in range(k)]

        new_pairs = sample_pairs(set_1, set_2, trajs, rng, beta)
        if randomize_labels:
            new_pairs = [
                (i, j, float(rng.integers(0, 2))) for (i, j, _mu) in new_pairs
            ]
        pairs.extend(new_pairs)

        # line 14: refit from scratch on ALL accumulated preferences (Appendix E.2)
        g, fit_info = fit_g(
            pairs, trajs, lam=lam, use_regularization=use_regularization,
            variant=variant, tie_handling=tie_handling, reg_terms=reg_terms,
            seed=seed + it,
        )

        new_policy = dp_optimal_policy(g, horizon, bonus)
        true_ret = policy_true_return(new_policy, horizon)
        farm_steps = sum(
            1 for p, a in zip(*_states_actions(new_policy, horizon)) if p == WAYPOINT
        )
        history.append(
            {
                "iteration": it + 1,
                "n_preferences": len(pairs),
                "true_return": true_ret,
                "farm_steps": farm_steps,
                "g": g.copy(),
                "used_fallback": used_fallback,
                **{f"fit_{key}": val for key, val in fit_info.items()},
            }
        )
        if verbose:
            print(
                f"    iter {it + 1:2d}  prefs {len(pairs):5d}  true {true_ret:+7.3f}  "
                f"farm {farm_steps:3d}  |D+| {fit_info.get('n_agree', 0):4d}  "
                f"grad {fit_info['grad_norm']:.1e}"
                + ("  [fallback]" if used_fallback else "")
            )

    return {"history": history, "g": g, "pairs": pairs, "trajs": trajs}


def _states_actions(policy, horizon=HORIZON, start=START):
    from .waypoint_env import CELL_INDEX

    pos, states, actions = start, [], []
    for t in range(horizon):
        a = int(policy[t, CELL_INDEX[pos]])
        states.append(pos)
        actions.append(a)
        pos = move(pos, a)
        if pos == GOAL:
            break
    return states, actions
