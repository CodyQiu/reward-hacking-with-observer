"""Exact dynamic programming for small tabular MDPs.

Every environment in this repo hands the solver two plain arrays:

    R : (S, A)      expected immediate reward for taking action a in state s
    P : (S, A, S)   P[s, a, s'] transition kernel, rows summing to 1

Nothing in this module knows about overseers, corrections or gridworlds. That is
deliberate (CLAUDE.md 6, "Solver conventions"): a new experiment is a new
``build_*`` function, never a change here.

Two exact solvers are provided and they are meant to be used against each other:

* ``value_iteration``  -- the reference method; contraction to a fixed tolerance.
* ``policy_iteration`` -- exact policy evaluation by linear solve. Converges in a
  handful of iterations regardless of how close gamma is to 1, which makes it the
  workhorse for the dense parameter sweeps. It is still exact DP; ``check_agreement``
  is used at sampled sweep points to confirm it matches value iteration.
"""

import numpy as np

__all__ = [
    "check_mdp",
    "q_from_v",
    "value_iteration",
    "policy_evaluation",
    "policy_iteration",
    "bellman_residual",
    "finite_horizon",
    "check_agreement",
    "find_threshold",
]


def check_mdp(R, P, gamma, allow_undiscounted=False):
    """Validate the tabular MDP triple; raise on anything malformed.

    ``allow_undiscounted`` admits gamma == 1, which is well defined only for a
    finite horizon (``finite_horizon`` passes it; the infinite-horizon solvers do not).
    """
    R = np.asarray(R, dtype=float)
    P = np.asarray(P, dtype=float)
    if R.ndim != 2:
        raise ValueError(f"R must be (S, A); got shape {R.shape}")
    n_s, n_a = R.shape
    if P.shape != (n_s, n_a, n_s):
        raise ValueError(f"P must be (S, A, S) = {(n_s, n_a, n_s)}; got {P.shape}")
    upper_ok = gamma <= 1.0 if allow_undiscounted else gamma < 1.0
    if not (0.0 <= gamma and upper_ok):
        raise ValueError(f"gamma must lie in [0, 1{']' if allow_undiscounted else ')'}; got {gamma}")
    if np.any(P < -1e-12):
        raise ValueError("P has negative entries")
    row_sums = P.sum(axis=2)
    if not np.allclose(row_sums, 1.0, atol=1e-9):
        bad = np.argwhere(np.abs(row_sums - 1.0) > 1e-9)
        raise ValueError(f"P rows must sum to 1; first offender (s, a) = {tuple(bad[0])}")
    return R, P


def q_from_v(V, R, P, gamma):
    """One-step lookahead: Q[s, a] = R[s, a] + gamma * sum_s' P[s, a, s'] V[s']."""
    return R + gamma * (P @ V)


def value_iteration(R, P, gamma, tol=1e-13, max_iter=500_000, validate=True):
    """Solve for V* by contraction. Returns (V, policy, Q, info).

    ``tol`` is on the sup-norm change between sweeps. The returned ``info`` dict
    carries the iteration count, the final sweep delta and the Bellman residual,
    so callers can assert on convergence quality rather than trusting it.
    """
    if validate:
        R, P = check_mdp(R, P, gamma)
    V = np.zeros(R.shape[0])
    delta = np.inf
    for n_iter in range(1, max_iter + 1):
        Q = q_from_v(V, R, P, gamma)
        V_new = Q.max(axis=1)
        delta = float(np.max(np.abs(V_new - V)))
        V = V_new
        if delta < tol:
            break
    else:
        raise RuntimeError(
            f"value_iteration did not converge in {max_iter} sweeps "
            f"(gamma={gamma}, final delta={delta:.3e})"
        )
    Q = q_from_v(V, R, P, gamma)
    policy = Q.argmax(axis=1)
    info = {
        "n_iter": n_iter,
        "delta": delta,
        "residual": bellman_residual(V, R, P, gamma),
        # Contraction bound on ||V - V*||_inf given the last sweep delta.
        "value_error_bound": delta * gamma / (1.0 - gamma),
    }
    return V, policy, Q, info


def policy_evaluation(policy, R, P, gamma):
    """Exact V^pi via the linear system (I - gamma P_pi) V = r_pi."""
    n_s = R.shape[0]
    rows = np.arange(n_s)
    r_pi = R[rows, policy]
    P_pi = P[rows, policy]
    return np.linalg.solve(np.eye(n_s) - gamma * P_pi, r_pi)


def policy_iteration(R, P, gamma, max_iter=1_000, validate=True):
    """Solve for V* by exact policy iteration. Returns (V, policy, Q, info)."""
    if validate:
        R, P = check_mdp(R, P, gamma)
    n_s = R.shape[0]
    policy = np.zeros(n_s, dtype=int)
    for n_iter in range(1, max_iter + 1):
        V = policy_evaluation(policy, R, P, gamma)
        Q = q_from_v(V, R, P, gamma)
        new_policy = Q.argmax(axis=1)
        # Greedy-improvement stability, not raw index equality: with ties the
        # argmax can flip between equally optimal actions and never settle.
        rows = np.arange(n_s)
        if np.allclose(Q[rows, new_policy], Q[rows, policy], atol=1e-12):
            policy = new_policy
            break
        policy = new_policy
    else:
        raise RuntimeError(f"policy_iteration did not converge in {max_iter} steps")
    V = policy_evaluation(policy, R, P, gamma)
    Q = q_from_v(V, R, P, gamma)
    policy = Q.argmax(axis=1)
    info = {"n_iter": n_iter, "residual": bellman_residual(V, R, P, gamma)}
    return V, policy, Q, info


def bellman_residual(V, R, P, gamma):
    """sup-norm of (T V - V). Zero exactly at V = V*."""
    return float(np.max(np.abs(q_from_v(V, R, P, gamma).max(axis=1) - V)))


def finite_horizon(R, P, gamma, horizon, validate=True):
    """Backward induction for a finite-horizon MDP.

    Returns (V, policy) with V of shape (horizon + 1, S) and policy of shape
    (horizon, S); V[horizon] == 0 and policy[t] is optimal with t steps elapsed.
    gamma == 1 is allowed: the horizon makes the undiscounted return finite.
    Step 1 uses it to cross-check the vectorised audit-grid DP (src/audit_dp.py).
    """
    if validate:
        R, P = check_mdp(R, P, gamma, allow_undiscounted=True)
    n_s, _ = R.shape
    V = np.zeros((horizon + 1, n_s))
    policy = np.zeros((horizon, n_s), dtype=int)
    for t in range(horizon - 1, -1, -1):
        Q = q_from_v(V[t + 1], R, P, gamma)
        policy[t] = Q.argmax(axis=1)
        V[t] = Q.max(axis=1)
    return V, policy


def check_agreement(R, P, gamma, atol=1e-8):
    """Cross-check the two exact solvers. Returns a diagnostics dict.

    Policies are compared through their action values rather than their indices:
    two different argmax choices are both optimal when their Q values tie, so
    index mismatch is not by itself a disagreement.
    """
    V_vi, pi_vi, Q_vi, info_vi = value_iteration(R, P, gamma)
    V_pi, pi_pi, Q_pi, info_pi = policy_iteration(R, P, gamma, validate=False)
    rows = np.arange(R.shape[0])
    return {
        "max_value_gap": float(np.max(np.abs(V_vi - V_pi))),
        "policies_identical": bool(np.array_equal(pi_vi, pi_pi)),
        "max_action_value_gap": float(
            np.max(np.abs(Q_vi[rows, pi_vi] - Q_vi[rows, pi_pi]))
        ),
        "residual_vi": info_vi["residual"],
        "residual_pi": info_pi["residual"],
        "agree": bool(
            np.max(np.abs(V_vi - V_pi)) < atol
            and np.max(np.abs(Q_vi[rows, pi_vi] - Q_vi[rows, pi_pi])) < atol
        ),
    }


def find_threshold(predicate, lo, hi, tol=1e-6, max_iter=200):
    """Bisect for the parameter value where ``predicate`` flips.

    ``predicate(x) -> bool``; requires predicate(lo) != predicate(hi). Returns the
    midpoint of the final bracket. Used to locate phase boundaries to far better
    precision than a linear scan, at a fraction of the cost.
    """
    p_lo, p_hi = bool(predicate(lo)), bool(predicate(hi))
    if p_lo == p_hi:
        raise ValueError(
            f"predicate does not flip on [{lo}, {hi}] (both sides -> {p_lo})"
        )
    for _ in range(max_iter):
        if hi - lo < tol:
            break
        mid = 0.5 * (lo + hi)
        if bool(predicate(mid)) == p_lo:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)
