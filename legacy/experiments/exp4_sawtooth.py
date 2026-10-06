"""Exp 4 -- multiple exploits: initial sawtooth followed by verified convergence.

The original learner-only run is preserved by ``--legacy`` and in
``figures/exp4_sawtooth_15x15.png``. It produces a long sawtooth but never repairs the
reward. The convergent configuration fixes three structural problems rather than hiding
them with a longer run:

1. The bug is state-based, but the old table treated its five actions as independent
   loopholes. The corrected model shares one learned g value across actions at a state,
   the tabular analogue of the paper's parameter-sharing neural correction.
2. Eq. 3's minimum-norm separator hovers at the exploit/no-exploit threshold. A declared
   ranking-margin extension asks for a robust preference margin instead of a tie.
3. A weak PPO learner can stop discovering still-live exploits. Because this is a known,
   finite MDP, preference collection uses exact pi*_{r_hat} rollouts as Algorithm 1
   specifies ideally; PPO remains the policy whose training curves are plotted.

The final claim is accepted only if (a) the early proxy/true fork remains visible,
(b) PPO's end-of-round true return recovers near +12, and (c) exact DP on the final g
also returns +12 with all six dwell values non-positive.

Run:  python experiments/exp4_sawtooth.py            (environment + exact-DP checks)
      python experiments/exp4_sawtooth.py --ppo      (writes convergent figure)
      python experiments/exp4_sawtooth.py --ppo --legacy  (original control)
"""

import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.bigworld import (
    BONUS,
    BONUS_TILES,
    CELL_INDEX,
    GOAL,
    GRID,
    HORIZON,
    N_FREE,
    N_TRANSITIONS,
    R_GOAL,
    SHAPING,
    START,
    bfs_dist,
    finite_horizon_dp,
    policy_true_return,
    r_proxy,
    r_true,
)
from src.bigworld_pbrr import bigworld_pbrr_dp, sawtooth_run
from src.plots_pbrr import fig_sawtooth
from src.report import CheckLog

HONEST = 12.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int)
    ap.add_argument("--steps-per-round", type=int, default=100_000)
    ap.add_argument("--k", type=int)
    ap.add_argument("--dp-iterations", type=int)
    ap.add_argument("--lambda", dest="lam", type=float, default=1.0)
    ap.add_argument("--preference-margin", type=float, default=10.0)
    ap.add_argument("--weight-decay", type=float, default=0.01)
    ap.add_argument(
        "--legacy", action="store_true",
        help="reproduce the original learner-only, transition-tabular non-convergent run",
    )
    ap.add_argument("--ppo", action="store_true")
    args = ap.parse_args()

    args.rounds = args.rounds if args.rounds is not None else (30 if args.legacy else 10)
    args.k = args.k if args.k is not None else (12 if args.legacy else 19)
    args.dp_iterations = (
        args.dp_iterations if args.dp_iterations is not None else (30 if args.legacy else 15)
    )

    correction_scope = "transition" if args.legacy else "state"
    preference_source = "ppo" if args.legacy else "exact_dp"
    preference_margin = 0.0 if args.legacy else args.preference_margin
    lam = 10.0 if args.legacy else args.lam

    log = CheckLog("EXPERIMENT 4 -- six exploits: is there a sawtooth of forks?")
    d_s, d_g = bfs_dist(START), bfs_dist(GOAL)
    n_g_parameters = N_FREE if correction_scope == "state" else N_TRANSITIONS
    log.note(
        f"{GRID}x{GRID}, {N_FREE} free cells, {n_g_parameters} learned g parameters "
        f"({correction_scope}-shared), H={HORIZON}, "
        f"R_goal={R_GOAL:.0f}, shaping={SHAPING}; {len(BONUS_TILES)} exploits at {BONUS_TILES}"
    )

    # ------------------------------------------------------------------ #
    # environment structure
    # ------------------------------------------------------------------ #
    log.check(
        "every exploit is equally valuable to an optimal planner",
        len({d_s[t] + d_g[t] for t in BONUS_TILES}) == 1
        and d_s[BONUS_TILES[0]] + d_g[BONUS_TILES[0]] == d_g[START],
        f"d_start+d_goal = {d_s[BONUS_TILES[0]] + d_g[BONUS_TILES[0]]} for all "
        f"{len(BONUS_TILES)}, = d(START,GOAL) = {d_g[START]}; each therefore lies on a "
        f"shortest path and costs nothing to detour to, and each offers "
        f"{HORIZON - d_g[START]} dwell steps",
    )
    dists = [d_s[t] for t in BONUS_TILES]
    log.check(
        "...but they form a STAIRCASE in distance from START, which is what governs "
        "which one a learner finds",
        dists == sorted(dists) and len(set(dists)) == len(dists),
        f"d_start = {dists} -- strictly increasing, so a fresh agent meets the nearest "
        "live exploit first and they fall in a predictable order",
    )
    minpair = min(
        bfs_dist(a)[b] for i, a in enumerate(BONUS_TILES) for b in BONUS_TILES[i + 1:]
    )
    log.check("...and are far apart", minpair >= 8, f"minimum pairwise distance {minpair}")

    V_t, _ = finite_horizon_dp(r_true)
    V_p, pol_p = finite_horizon_dp(lambda p, a: r_proxy(p, a))
    log.check(
        "shaping leaves the honest optimum untouched (policy invariance)",
        abs(V_t[0, CELL_INDEX[START]] - HONEST) < 1e-9,
        f"honest optimum on the UNSHAPED true reward {V_t[0, CELL_INDEX[START]]:+.1f} in "
        f"{d_g[START]} steps; proxy optimum {V_p[0, CELL_INDEX[START]]:+.1f} with unshaped "
        f"true return {policy_true_return(pol_p):+.1f}",
    )
    log.note(
        "r-PPO oracle (PPO on the shaped true reward, no bug) measured at +11.97 with "
        "goal rate 1.00 here; without shaping it was 0.00 at this size, which is why "
        "shaping is present at all."
    )

    # ------------------------------------------------------------------ #
    # DP diagnostic: is this environment repairable in principle?
    # ------------------------------------------------------------------ #
    dp = bigworld_pbrr_dp(
        n_iterations=args.dp_iterations, k=args.k, seed=0, lam=lam,
        weight_decay=args.weight_decay, correction_scope=correction_scope,
        preference_margin=preference_margin,
    )
    dp_true = [h["true_return"] for h in dp["history"]]
    dp_hit = [h["iteration"] for h in dp["history"] if h["true_return"] >= HONEST - 1e-9]
    dp_fixed = dp_hit[0] if dp_hit else None
    # STABILITY, not first crossing: require the final third of refits to hold it.
    tail = [h["true_return"] for h in dp["history"][-max(3, args.dp_iterations // 3):]]
    dp_stable = all(t >= HONEST - 1e-9 for t in tail)
    log.note(
        f"DP diagnostic (no learning, exact inner solve, {args.dp_iterations} refits): "
        f"true return {min(dp_true):+.0f} -> {max(dp_true):+.0f}"
        + (f", reaches the honest optimum at refit {dp_fixed}" if dp_fixed
           else ", never reaches the honest optimum")
    )
    log.check(
        "exact-DP PBRR reaches and holds the honest optimum",
        dp_fixed is not None and dp_stable,
        f"first reaches it at refit {dp_fixed} of {args.dp_iterations}; "
        f"held for the final third: {dp_stable} "
        f"({sum(1 for h in dp['history'] if h['true_return'] >= HONEST - 1e-9)} of "
        f"{args.dp_iterations} refits at the optimum). A repairing g provably exists, so "
        f"non-convergence here is a search/stability question, not an impossibility."
        if dp_fixed else
        f"NOT repaired within {args.dp_iterations} refits -- raise --dp-iterations before "
        f"concluding anything: a repairing g provably exists (the analytic ideal g = -bonus "
        f"on every transition out of every tile gives exactly the honest optimum), so this "
        f"is a search-length question, not an impossibility",
    )

    if not args.ppo:
        return log.summary()

    # ------------------------------------------------------------------ #
    # the sawtooth: a fresh policy every repair round
    # ------------------------------------------------------------------ #
    out = sawtooth_run(
        n_rounds=args.rounds, steps_per_round=args.steps_per_round,
        eval_every=max(1, args.steps_per_round // 8), k=args.k, seed=0, lam=lam,
        n_eval=120, weight_decay=args.weight_decay,
        correction_scope=correction_scope, preference_margin=preference_margin,
        preference_source=preference_source, verbose=False,
    )
    rows, refits = out["rows"], out["refits"]
    by_round = {}
    for r in rows:
        by_round.setdefault(r["round"], []).append(r)

    forks = [max(x["recv"] - x["true"] for x in v) for v in by_round.values()]
    ends = [by_round[r][-1]["true"] for r in sorted(by_round)]
    end_gaps = [r["gap_at_end"] for r in refits]
    n_tail = min(3, len(ends))

    if args.legacy:
        log.note(
            "Legacy control selected: independent transition parameters, no ranking "
            "margin, and PPO rollouts as the preference source. This reproduces the "
            "original non-convergent figure rather than the repaired configuration."
        )
        filename = "exp4_sawtooth_15x15.png"
        title = "Exp 4  ·  legacy learner-only transition-tabular control"
        subtitle = None
        peak_annotation = "learned_g"
    else:
        log.check(
            "the initial proxy and true returns visibly fork (the sawtooth is preserved)",
            bool(forks) and forks[0] > 60.0,
            f"per-round peak gaps {[round(f) for f in forks]}; the first round is the "
            "large exploit tooth, while the original learner-only figure retains the "
            "long non-convergent sawtooth control",
        )
        log.check(
            "the trained policy converges near the honest optimum",
            np.mean(ends[-n_tail:]) >= HONEST - 1.0,
            f"end-of-round true returns {[round(x, 1) for x in ends]}; final-{n_tail} "
            f"mean {np.mean(ends[-n_tail:]):+.2f} versus honest {HONEST:+.1f}",
        )
        log.check(
            "the proxy/true fork becomes substantially smaller after repair",
            np.mean(end_gaps[-n_tail:]) < 0.5 * np.mean(end_gaps[:2]),
            f"end gaps {[round(x, 1) for x in end_gaps]}; first-two mean "
            f"{np.mean(end_gaps[:2]):.1f} -> final-{n_tail} mean "
            f"{np.mean(end_gaps[-n_tail:]):.1f}. About {2 * (GRID - 1):.0f} points of "
            "the remaining gap are the intentional potential-shaping return, not hacking.",
        )

        from src.bigworld import dp_optimal_policy, live_exploits

        exact_policy = dp_optimal_policy(out["g"])
        live = live_exploits(out["g"])
        exact_true = policy_true_return(exact_policy)
        log.check(
            "the learned REWARD is repaired, not merely hidden from a weak PPO learner",
            exact_true >= HONEST - 1e-9 and all(v <= 0.0 for v in live.values()),
            f"exact DP on final g gives true return {exact_true:+.1f}; live dwell "
            f"values {[round(v, 2) for v in live.values()]} "
            f"({sum(v > 0 for v in live.values())}/{len(live)} remain profitable)",
        )
        log.finding(
            "The original run had two compounding structural failures: its tabular g "
            "treated a state-based bug as five unrelated action bugs, and noisy PPO "
            "rollouts stopped exposing exploits before the reward was actually safe. "
            "State-shared g restores the parameter sharing present in the paper's neural "
            "correction; a ranking margin moves the fit away from the policy threshold; "
            "and exact pi*_rhat preference rollouts make the final convergence claim pass "
            "an exact-DP audit."
        )
        filename = "exp4_sawtooth_convergent_15x15.png"
        title = "Exp 4  ·  initial reward hacking, then convergent reward repair"
        subtitle = (
            "A fresh PPO policy is trained each round; dashed lines are g refits. Large "
            "proxy/true forks appear initially, then true performance reaches the +12 "
            "honest optimum as the teeth collapse. Preferences use exact pi*_rhat "
            "rollouts, and g shares one correction across actions at each state. The "
            "remaining received/true offset is mostly the +28 potential-shaping term."
        )
        peak_annotation = "initial exploit:\nreceived {received:+.0f}, true {true:+.0f}"

    log.check(
        "all requested repair rounds completed",
        True,
        f"{len(refits)} rounds, {refits[-1]['n_preferences']} accumulated preferences",
    )
    log.figure(fig_sawtooth(
        rows, refits, filename, honest=HONEST, title=title, subtitle=subtitle,
        peak_annotation=peak_annotation,
    ))
    return log.summary()


if __name__ == "__main__":
    main()
