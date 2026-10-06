"""Exp 3 -- PBRR: repairing the proxy with a *learned* transition-dependent g.

Exp 2 corrected reward hacking with an oracle: when the monitor fired, the reward
became r_true. No overseer can do that -- r_true is exactly what it lacks. This
experiment replaces the oracle with Preference-Based Reward Repair
(Hatgis-Kessell, Bhamidipaty & Brunskill, arXiv:2510.13036v2):

    r_hat(s,a,s') = r_proxy(s,a,s') + g(s,a,s')

with g fit from preferences over trajectory pairs drawn from the reference policy
and from the policy that is optimal under the current repaired reward. Exp 2's
within-episode monitor is switched off here: PBRR *is* the correction mechanism, and
running a second one alongside it would make any repair unattributable.

Run:  python experiments/exp3_pbrr.py            (all DP phases, fast)
      python experiments/exp3_pbrr.py --quick
"""

import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.dp_reference import bfs_dist, finite_horizon_dp
from src.pbrr import (
    N_ACTIONS,
    N_TRANSITIONS,
    ideal_g,
    transition_index,
)
from src.pbrr_loop import (
    dp_optimal_policy,
    make_eps_greedy_reference,
    make_optimal_reference,
    make_random_reference,
    pbrr_run,
    policy_true_return,
    reference_true_return,
    repaired_reward_fn,
)
from src.pbrr_minimal import MINIMAL_MDPS, run_minimal_pbrr
from src.plots_pbrr import fig_g_grid, fig_minimal_mdps, fig_pbrr_curves
from src.report import CheckLog
from src.reward_distance import epic_distance
from src.waypoint_env import FREE_CELLS, GOAL, HORIZON, START, WAYPOINT, r_proxy, r_true

HONEST_OPTIMUM = 2.0
SECOND_TILE = (4, 0)          # verified equally attractive: d(S,t)+d(t,G) == 8


def two_tile_reward_fn(g, bonus=2.0, tiles=(WAYPOINT, SECOND_TILE)):
    """Proxy with a SECOND bonus tile, plus a g that never saw it.

    Phase 7 is DP-only, so the extra tile lives in the reward function rather than in
    the environment -- which also means Exp 2's env stays byte-for-byte unchanged.
    """
    g = np.asarray(g, dtype=float)

    def fn(pos, action):
        r = r_true(pos, action)
        if pos in tiles:
            r += bonus
        return r + g[transition_index(pos, action)]

    return fn


def per_cell_min_g(g):
    """min over actions of g at each cell -- the strongest penalty the cell carries."""
    return {
        cell: float(min(g[transition_index(cell, a)] for a in range(N_ACTIONS)))
        for cell in FREE_CELLS
    }


def localisation(g):
    """Fraction of g's total magnitude sitting on transitions out of the waypoint."""
    total = float(np.abs(g).sum())
    if total < 1e-12:
        return 0.0
    on_wp = float(sum(abs(g[transition_index(WAYPOINT, a)]) for a in range(N_ACTIONS)))
    return on_wp / total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iterations", type=int, default=8)
    ap.add_argument("--k", type=int, default=19)
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument(
        "--ppo", action="store_true",
        help="phase 5: confirm with a real learner (SBX PPO) rather than exact DP",
    )
    ap.add_argument("--ppo-steps", type=int, default=60_000)
    ap.add_argument(
        "--ppo-eval-every", type=int, default=2_000,
        help="dense by default: the agent discovers the exploit inside ~10k steps, so a "
             "coarse schedule collapses the whole divergence into one segment",
    )
    args = ap.parse_args()
    if args.quick:
        args.iterations, args.k, args.seeds = 4, 8, 2

    log = CheckLog("EXPERIMENT 3 -- PBRR: a learned correction g to the proxy reward")
    log.note(
        f"{args.iterations} PBRR iterations, k={args.k} ({args.k**2} preferences/iteration), "
        f"{args.seeds} seeds; pi*_r_hat solved exactly by finite-horizon DP; gamma=1, H={HORIZON}"
    )

    rng = np.random.default_rng(0)
    ref_return = reference_true_return(make_eps_greedy_reference(0.3), rng, 4000)
    log.note(
        f"pi_ref = eps-greedy shortest path (eps=0.3), true return {ref_return:+.3f}; "
        f"honest optimum {HONEST_OPTIMUM:+.1f}; uncorrected proxy optimum "
        f"{policy_true_return(dp_optimal_policy(np.zeros(N_TRANSITIONS))):+.1f}"
    )

    # ---------------------------------------------------------------- #
    # 1-2. the headline run and the loss ablation
    # ---------------------------------------------------------------- #
    conditions = {
        "PBRR, Eq 3 ($L^+$ and $L^-$)": dict(),
        "drop $L^+$ (keep $L^-$)": dict(reg_terms=("-",)),
        "drop $L^-$ (keep $L^+$)": dict(reg_terms=("+",)),
        "Eq 1 only (= RRM baseline)": dict(use_regularization=False),
        "CONTROL: random labels": dict(randomize_labels=True),
    }
    results, series = {}, {}
    for label, kw in conditions.items():
        runs = [
            pbrr_run(
                make_eps_greedy_reference(0.3), n_iterations=args.iterations,
                k=args.k, seed=s, **kw,
            )
            for s in range(args.seeds)
        ]
        arr = np.array([[h["true_return"] for h in r["history"]] for r in runs])
        x = np.array([h["n_preferences"] for h in runs[0]["history"]])
        results[label] = runs
        series[label] = (x, arr)
        repaired = int((arr.max(axis=1) > HONEST_OPTIMUM - 1e-6).sum())
        log.note(
            f"{label}: repaired in {repaired}/{args.seeds} seeds; "
            f"final true return (median over seeds) {np.median(arr[:, -1]):+.3f}, "
            f"best per seed {arr.max(axis=1).mean():+.3f}"
        )

    eq3 = series["PBRR, Eq 3 ($L^+$ and $L^-$)"][1]
    log.check(
        "PBRR (Eq 3) repairs the proxy: the induced policy reaches the honest optimum",
        eq3.max(axis=1).mean() > HONEST_OPTIMUM - 1e-6,
        f"best true return {eq3.max(axis=1).mean():+.4f} vs honest optimum "
        f"{HONEST_OPTIMUM:+.1f}, from an uncorrected -30.0",
    )
    log.check(
        "PBRR beats the reference policy, as Theorem 4.3 requires",
        eq3[:, -1].mean() > ref_return,
        f"final {eq3[:, -1].mean():+.3f} vs pi_ref {ref_return:+.3f}",
    )
    eq1 = series["Eq 1 only (= RRM baseline)"][1]
    log.check(
        "Eq 1 alone does NOT repair it (the paper's §5.4 ablation, reproduced)",
        eq1.max(axis=1).mean() < HONEST_OPTIMUM - 1.0,
        f"best true return {eq1.max(axis=1).mean():+.3f}; the plain cross-entropy "
        "objective leaves the reward worse than uncorrected",
    )
    drop_minus = series["drop $L^-$ (keep $L^+$)"][1]
    drop_plus = series["drop $L^+$ (keep $L^-$)"][1]
    log.check(
        "$L^-$ is the load-bearing term: dropping it costs far more than dropping $L^+$",
        drop_plus.mean() > drop_minus.mean(),
        f"mean-over-iterations true return {drop_plus.mean():+.3f} without $L^+$ vs "
        f"{drop_minus.mean():+.3f} without $L^-$",
    )
    ctrl = series["CONTROL: random labels"][1]
    log.check_control(
        "random preference labels do not repair the reward",
        ctrl.max(axis=1).mean() < HONEST_OPTIMUM - 1.0,
        f"best true return {ctrl.max(axis=1).mean():+.3f} -- the labels, not the "
        "regulariser, are what carry the information",
    )

    log.figure(
        fig_pbrr_curves(
            series, "exp3_pbrr_true_return.png",
            "Exp 3  ·  repairing the proxy from preferences, and what each loss term buys",
            f"thin lines are individual seeds ({args.seeds} per condition), thick lines the "
            f"median; {args.k**2} preferences per iteration. No mean/s.d. band, because the "
            "outcome is bimodal -- the induced policy is either repaired (+2.0) or not "
            "(-30.0), never in between, so an average would sit in an empty gap. The "
            "learner's reward is r_proxy + g throughout; the true reward is only ever used "
            "to label preferences. Eq 1 is the same exploration with the plain "
            "cross-entropy objective.",
            honest=HONEST_OPTIMUM, ref_return=ref_return,
        )
    )

    # ---------------------------------------------------------------- #
    # 3. what g actually learned
    # ---------------------------------------------------------------- #
    g_learned = results["PBRR, Eq 3 ($L^+$ and $L^-$)"][0]["g"]
    loc = localisation(g_learned)
    log.check(
        "the learned g concentrates on the transitions out of the waypoint",
        loc > 0.5,
        f"{loc:.1%} of |g| sits on the 5 waypoint transitions (5 of 105); "
        f"mean g there = {np.mean([g_learned[transition_index(WAYPOINT, a)] for a in range(N_ACTIONS)]):+.3f}",
    )
    log.check(
        "the correction is negative on the waypoint, i.e. it penalises the exploit",
        all(g_learned[transition_index(WAYPOINT, a)] < 0 for a in range(N_ACTIONS)),
        "every waypoint transition receives a negative correction",
    )
    log.figure(
        fig_g_grid(
            per_cell_min_g(g_learned), per_cell_min_g(ideal_g()),
            "exp3_g_grid.png",
            "Exp 3  ·  the learned correction, cell by cell (min over actions)",
            "PBRR is never told where the bug is. It localises the penalty on the "
            "waypoint from behavioural comparisons alone. Walls are grey.",
        )
    )

    # ---------------------------------------------------------------- #
    # 6. reward distance: repaired vs true
    # ---------------------------------------------------------------- #
    d_learned = epic_distance(repaired_reward_fn(g_learned), r_true)
    d_ideal = epic_distance(repaired_reward_fn(ideal_g()), r_true)
    d_proxy = epic_distance(repaired_reward_fn(np.zeros(N_TRANSITIONS)), r_true)
    pol_learned = dp_optimal_policy(g_learned)
    log.check(
        "the repaired reward induces the honest optimal policy",
        abs(policy_true_return(pol_learned) - HONEST_OPTIMUM) < 1e-9,
        f"true return of pi*_(r_proxy+g) = {policy_true_return(pol_learned):+.4f}",
    )
    log.check(
        "...while NOT being equal to the true reward (EPIC distance > 0)",
        d_learned > 1e-3,
        f"EPIC(r_proxy+g_learned, r_true) = {d_learned:.4f}; for reference the analytic "
        f"ideal gives {d_ideal:.4f} (it equals r_true exactly) and the uncorrected proxy "
        f"gives {d_proxy:.4f}",
    )
    log.finding(
        f"the repaired reward sits EPIC distance {d_learned:.3f} from the true reward yet "
        f"induces exactly the honest optimal policy -- reward repair does not require "
        f"recovering r_true, which is the whole point of correcting a proxy you cannot see "
        f"the truth behind."
    )

    # ---------------------------------------------------------------- #
    # 4. the C_1 > 0 fallback, on the paper's own minimal MDPs
    # ---------------------------------------------------------------- #
    log.note(
        "Appendix H minimal MDPs: the C_1=0 failure mode cannot arise in the waypoint "
        "grid (once farming is penalised, the argmax of r_proxy+g *is* the honest "
        "optimum), so the fallback is tested where the paper says it matters."
    )
    rows = []
    for mdp in ("MDP1", "MDP2"):
        optimum = max(MINIMAL_MDPS[mdp]["true"])
        for c1, lam in ((0.0, 10.0), (1.0, 10.0), (1.0, 0.01)):
            out = run_minimal_pbrr(mdp, n_iterations=8, c1=c1, lam=lam)
            first = next((r["iteration"] for r in out["history"] if r["is_optimal"]), None)
            rows.append(
                dict(mdp=mdp, c1=c1, lam=lam, optimum=optimum,
                     final=out["history"][-1]["induced_true_return"], first_optimal=first)
            )
    by_key = {(r["mdp"], r["c1"], r["lam"]): r for r in rows}
    log.check(
        "MDP 1: PBRR is optimal after a single preference (Theorem H.1)",
        by_key[("MDP1", 0.0, 10.0)]["first_optimal"] == 1,
        f"first optimal at iteration {by_key[('MDP1', 0.0, 10.0)]['first_optimal']}",
    )
    log.check(
        "MDP 2: with C_1 = 0 PBRR stalls above pi_ref but below the optimum",
        by_key[("MDP2", 0.0, 10.0)]["first_optimal"] is None
        and by_key[("MDP2", 0.0, 10.0)]["final"] > MINIMAL_MDPS["MDP2"]["true"][2],
        f"final {by_key[('MDP2', 0.0, 10.0)]['final']:+.0f} vs optimum "
        f"{max(MINIMAL_MDPS['MDP2']['true']):+.0f} (pi_ref = +3)",
    )
    log.check(
        "MDP 2: the fallback fixes it ONLY once lambda has decayed",
        by_key[("MDP2", 1.0, 10.0)]["first_optimal"] is None
        and by_key[("MDP2", 1.0, 0.01)]["first_optimal"] is not None,
        f"C_1=1, lambda=10 -> {by_key[('MDP2', 1.0, 10.0)]['final']:+.0f} (stalls); "
        f"C_1=1, lambda=0.01 -> optimal at iteration "
        f"{by_key[('MDP2', 1.0, 0.01)]['first_optimal']}",
    )
    log.finding(
        "the maximum-divergence fallback is specified in Algorithm 1 but disabled "
        "(C_1 = 0) in every experiment the paper runs, because Pi_t is intractable in its "
        "domains. On the paper's own MDP 2 it is necessary but not sufficient: it surfaces "
        "the informative comparison, yet L+ protects the wrongly-ranked transition until "
        "lambda decays, so the fallback and Assumption 4.5's lambda -> 0 are jointly needed."
    )
    log.figure(
        fig_minimal_mdps(
            rows, "exp3_minimal_mdps.png",
            "Exp 3  ·  the max-divergence fallback on the paper's own minimal MDPs",
            "Appendix H, Figure 7. MDP 1 is repaired by one preference either way. MDP 2 is "
            "where C_1 = 0 provably stalls, and it needs both the fallback and a decayed "
            "lambda to be repaired.",
        )
    )

    # ---------------------------------------------------------------- #
    # controls: the reference policy brackets
    # ---------------------------------------------------------------- #
    for name, ref_fn in (
        ("pi_ref = exact honest optimum", make_optimal_reference()),
        ("pi_ref = uniform random", make_random_reference()),
    ):
        arr = np.array(
            [
                [
                    h["true_return"]
                    for h in pbrr_run(
                        ref_fn, n_iterations=args.iterations, k=args.k, seed=s
                    )["history"]
                ]
                for s in range(min(3, args.seeds))
            ]
        )
        log.check_control(
            f"{name}: best true return {arr.max(axis=1).mean():+.3f}",
            True,
            "reported, not asserted -- these bracket the achievable range implied by "
            "Theorem 4.3",
        )

    # ---------------------------------------------------------------- #
    # 7. generalisation to a second, unseen bonus tile
    # ---------------------------------------------------------------- #
    d_goal, d_tile = bfs_dist(GOAL), bfs_dist(SECOND_TILE)
    log.check(
        f"the unseen tile {SECOND_TILE} is exactly as attractive as the waypoint",
        d_tile[START] + d_goal[SECOND_TILE] == d_goal[START] == 8,
        f"d(START,tile)={d_tile[START]}, d(tile,GOAL)={d_goal[SECOND_TILE]}, "
        f"d(START,GOAL)={d_goal[START]}",
    )
    V2, pol2 = finite_horizon_dp(two_tile_reward_fn(g_learned))
    states2 = []
    pos = START
    for t in range(HORIZON):
        from src.waypoint_env import CELL_INDEX, move

        a = int(pol2[t, CELL_INDEX[pos]])
        states2.append(pos)
        pos = move(pos, a)
        if pos == GOAL:
            break
    farm_new = sum(1 for p in states2 if p == SECOND_TILE)
    farm_old = sum(1 for p in states2 if p == WAYPOINT)
    log.check(
        "a g fit on one exploit does NOT generalise to an identical unseen exploit",
        farm_new > 1,
        f"with a second bonus tile at {SECOND_TILE} that appeared in no preference pair, "
        f"the repaired-reward optimum farms it for {farm_new} steps "
        f"(and the patched waypoint for {farm_old})",
    )
    log.finding(
        f"reward repair is exploit-specific here: the learned g localises on the waypoint, "
        f"so an identical bonus bug one tile away is farmed freely ({farm_new} steps). A "
        f"correction learned from behaviour patches the instance it was shown, not the class "
        f"-- which is the whack-a-mole cost of repairing proxies rather than fixing them."
    )

    # ---------------------------------------------------------------- #
    # 5. confirm with a real learner, not just exact DP
    # ---------------------------------------------------------------- #
    if args.ppo:
        from src.plots_pbrr import fig_training_divergence
        from src.train import train_one

        log.note(
            "phase 5: SBX PPO trained on the uncorrected proxy vs on r_proxy + g_learned, "
            "logging BOTH the received (training) return and the true return every "
            "10k steps. The monitor is off (h_max = h_flat = 0) so PBRR is the only "
            "correction in play. This is the Exp-2-style divergence curve: the point is "
            "whether the two returns split apart during training."
        )
        panels, ppo_rows = [], {}
        for tag, corr in (
            ("trained on the uncorrected proxy", None),
            ("trained on the repaired reward  $r_{proxy} + g$", g_learned),
        ):
            env_kwargs = dict(h_max=0.0, h_flat=0.0)
            if corr is not None:
                env_kwargs["correction"] = corr
            recv, true, steps = [], [], None
            for seed in range(3):
                rows, _ = train_one(
                    "flat", seed, total_timesteps=args.ppo_steps,
                    eval_every=args.ppo_eval_every, n_eval_episodes=300,
                    # a subdirectory: train_one names files {monitor}_seed{k}.csv, which
                    # would otherwise clobber Exp 2's results/flat_seed{k}.csv
                    results_dir=os.path.join("results", "exp3_ppo",
                                             "repaired" if corr is not None else "uncorrected"),
                    env_kwargs=env_kwargs, verbose=False,
                )
                steps = np.array([r["timesteps"] for r in rows])
                recv.append([r["proxy_return"] for r in rows])
                true.append([r["true_return"] for r in rows])
            recv, true = np.array(recv), np.array(true)
            panels.append((tag, steps, recv, true))
            ppo_rows[tag] = (float(recv[:, -1].mean()), float(true[:, -1].mean()))
            log.note(
                f"  {tag}: received {recv[:, -1].mean():+.2f}, true {true[:, -1].mean():+.2f}"
            )

        unc_recv, unc_true = ppo_rows["trained on the uncorrected proxy"]
        rep_recv, rep_true = ppo_rows["trained on the repaired reward  $r_{proxy} + g$"]
        log.check(
            "a trained PPO agent confirms the repair, not just the exact DP solution",
            rep_true > unc_true + 5.0,
            f"true return {rep_true:+.2f} on the repaired reward vs {unc_true:+.2f} "
            "on the uncorrected proxy",
        )
        log.check(
            "the uncorrected proxy reproduces Exp 2's divergence: received return rises "
            "while true return collapses",
            unc_recv > 10.0 and unc_true < -20.0,
            f"received {unc_recv:+.2f} vs true {unc_true:+.2f} -- a gap of "
            f"{unc_recv - unc_true:.1f} reward units opens up during training",
        )
        log.check(
            "the repair CLOSES that gap: the two returns track each other instead",
            abs(rep_recv - rep_true) < 0.25 * abs(unc_recv - unc_true),
            f"gap {abs(rep_recv - rep_true):.2f} on the repaired reward vs "
            f"{abs(unc_recv - unc_true):.1f} on the uncorrected proxy",
        )
        log.finding(
            f"the divergence your TA is after: training on the uncorrected proxy splits the "
            f"two returns by {unc_recv - unc_true:.1f} units (received {unc_recv:+.1f}, true "
            f"{unc_true:+.1f}); training on r_proxy + g_learned leaves them "
            f"{abs(rep_recv - rep_true):.2f} apart, both near the honest optimum. The "
            f"repaired reward is still not equal to r_true (EPIC {d_learned:.3f}) -- it just "
            f"no longer rewards the exploit."
        )
        log.figure(
            fig_training_divergence(
                panels, "exp3_training_divergence.png",
                "Exp 3  ·  does the proxy/true split still appear, and does the repair close it?",
                "mean of 3 PPO seeds, band = ±1 s.d., 300 fresh episodes per evaluation. "
                "Both quantities are in reward units so they share one axis. Left: the "
                "uncorrected proxy, where the received return climbs as the agent learns to "
                "farm while the true objective collapses. Right: the same learner on "
                "r_proxy + g, where the split does not open.",
            )
        )

    return log.summary()


if __name__ == "__main__":
    main()
