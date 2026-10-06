"""The paper's own minimal MDPs (Appendix H, Figure 7) as validation anchors.

Two horizon-1 MDPs with one start state and four actions leading to terminal
states s1..s4. Rewards are defined over the next state. They differ *only* in the
ground-truth reward:

                 proxy   truth (MDP 1)   truth (MDP 2)
        s1        +10          +2              +2
        s2         +6          +4              +8
        s3         +7          +3              +3
        s4         +9          +8              +4

pi_ref visits s3 in both.

These are worth implementing for two reasons.

**They validate L-.** In MDP 1 the paper proves (Theorem H.1) that PBRR recovers an
optimal policy after O(1) preferences, whereas uniform exploration needs O(|S|). If
our L- is wired up correctly, MDP 1 must be solved in a single iteration. That is a
much sharper test of the asymmetric ridge than anything the gridworld provides.

**They exhibit the C_1 = 0 failure that our gridworld cannot.** In MDP 2 PBRR with
C_1 = 0 decrements s1, moves to s4, and then finds that the proxy already ranks
s4 above s3 -- the pair lands in D+, L+ pins g, and the loop stops at truth +4 while
the optimum s2 (+8) was never visited by either policy. In the waypoint gridworld
this cannot happen: once farming is penalised, the policy that maximises
r_proxy + g *is* the honest optimum, so there is no third unexplored option to get
stuck away from. MDP 2 is therefore where the maximum-divergence fallback has
something to fix.

Pi_t (the non-dominated policy set) is taken here as *all* policies, which is a
conservative relaxation of the paper's confidence-set definition (Eq 15). At four
actions the relaxation costs nothing and keeps the fallback's behaviour transparent:
the max-divergence pair is whichever pair of transitions the accumulated data has
constrained least, which is exactly the unexplored s2.
"""

import numpy as np

from .pbrr import Trajectory, fit_g
from .pbrr_loop import feature_covariance, max_divergence_pair

__all__ = ["MINIMAL_MDPS", "minimal_trajectories", "run_minimal_pbrr"]

N_A = 4
REF_ACTION = 2  # pi_ref visits s3

MINIMAL_MDPS = {
    "MDP1": {
        "proxy": [10.0, 6.0, 7.0, 9.0],
        "true": [2.0, 4.0, 3.0, 8.0],
        "note": "PBRR with C_1=0 succeeds: Theorem H.1's O(1) case.",
    },
    "MDP2": {
        "proxy": [10.0, 6.0, 7.0, 9.0],
        "true": [2.0, 8.0, 3.0, 4.0],
        "note": "PBRR with C_1=0 stalls at s4 (+4); the optimum s2 (+8) is never seen.",
    },
}


def minimal_trajectories(spec):
    """One single-transition Trajectory per action."""
    return [
        Trajectory(
            states=[0], actions=[a], proxy_return=spec["proxy"][a],
            true_return=spec["true"][a], g_idx=[a], n_transitions=N_A,
        )
        for a in range(N_A)
    ]


def _label(traj_a, traj_b):
    """Noiseless preference from the ground truth (Assumption 4.6)."""
    if traj_a.true_return > traj_b.true_return:
        return 0.0
    if traj_a.true_return < traj_b.true_return:
        return 1.0
    return 0.5


def run_minimal_pbrr(
    name, n_iterations=5, c1=0.0, lam=10.0, use_regularization=True, verbose=False
):
    """PBRR on a minimal MDP. Returns the per-iteration history."""
    spec = MINIMAL_MDPS[name]
    trajs_by_action = minimal_trajectories(spec)
    optimal_action = int(np.argmax(spec["true"]))

    trajs, pairs, history = [], [], []
    observed_diffs = []          # feeds V_t of Eq 7
    g = np.zeros(N_A)

    for it in range(n_iterations):
        a_star = int(np.argmax(np.asarray(spec["proxy"]) + g))
        a_ref = REF_ACTION

        used_fallback = False
        if c1 > 0.0:
            # lines 6-11: is the default (pi*, pi_ref) pair divergent enough?
            (bi, bj), best_val = max_divergence_pair(trajs_by_action, observed_diffs)
            Vinv = np.linalg.pinv(
                feature_covariance(observed_diffs, N_A)
            )
            d = trajs_by_action[a_star].counts - trajs_by_action[a_ref].counts
            default_val = float(d @ Vinv @ d)
            if c1 * default_val <= best_val:
                used_fallback = True
                a_star, a_ref = bi, bj

        i, j = len(trajs), len(trajs) + 1
        trajs.append(trajs_by_action[a_star])
        trajs.append(trajs_by_action[a_ref])
        pairs.append((i, j, _label(trajs[i], trajs[j])))
        observed_diffs.append(trajs[i].counts - trajs[j].counts)

        g, info = fit_g(pairs, trajs, lam=lam, use_regularization=use_regularization)
        induced = int(np.argmax(np.asarray(spec["proxy"]) + g))
        history.append(
            {
                "iteration": it + 1,
                "n_preferences": len(pairs),
                "compared": (a_star, a_ref),
                "induced_action": induced,
                "induced_true_return": spec["true"][induced],
                "is_optimal": induced == optimal_action,
                "used_fallback": used_fallback,
                "n_agree": info.get("n_agree", 0),
                "g": g.copy(),
            }
        )
        if verbose:
            print(
                f"    iter {it + 1}: compared s{a_star + 1} vs s{a_ref + 1} -> "
                f"induces s{induced + 1} (true {spec['true'][induced]:+.0f}"
                f"{', OPTIMAL' if induced == optimal_action else ''})"
                f"  |D+|={info.get('n_agree', 0)}"
                + ("  [fallback]" if used_fallback else "")
            )
    return {"name": name, "optimal_action": optimal_action, "history": history, "g": g}
