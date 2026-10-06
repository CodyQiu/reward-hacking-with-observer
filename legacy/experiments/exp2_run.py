"""Exp 2 end to end: both monitor conditions x N seeds, then the four figures.

    python experiments/exp2_run.py                 # the full run (2 x 5 x 500k)
    python experiments/exp2_run.py --quick         # a short smoke run
    python experiments/exp2_run.py --plots-only    # rebuild figures from results/

Run tests/test_env.py first: it reproduces the reference table by exact DP and
Monte Carlo, and none of the numbers below mean anything if it fails.
"""

import argparse
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.dp_reference import REFERENCE
from src.plots import CONDITION_LABEL, load_results, make_all_figures
from src.report import CheckLog
from src.train import train_one

CONDITIONS = ("suspicion", "flat")
# Metrics to compare against the spec's reference table, and the tolerance for
# "PPO landed near the memoryless optimum" rather than exactly on it.
COMPARE = [
    ("true_return", "true_return", 1.5),
    ("farm_steps", "farm_steps", 1.5),
    ("p_detected", "p_detected", 0.10),
    ("ep_len", "ep_len", 1.5),
    ("goal_rate", "goal_rate", 0.10),
]


def final_window(data, monitor, metric, n_last=5):
    """Mean over the last ``n_last`` evaluations, across seeds."""
    return float(data[monitor][metric][:, -n_last:].mean())


def final_window_per_seed(data, monitor, metric, n_last=5):
    return data[monitor][metric][:, -n_last:].mean(axis=1)


def run_phase2(args):
    """Optional section 10: the permanent correction, and its rise/drop/recover curve."""
    from src.permanent_correction import train_with_permanent_correction
    from src.plots import fig_permanent_correction

    log = CheckLog("EXPERIMENT 2, PHASE 2 -- the permanent correction")
    log.note(
        f"correction becomes permanent after {args.n_permanent} cumulative detections; "
        f"{args.seeds} seeds x {args.timesteps:,} steps per condition"
    )

    swaps = {}
    for monitor in CONDITIONS:
        finals, swap_steps = [], []
        for seed in range(args.seeds):
            counter, final, _ = train_with_permanent_correction(
                monitor=monitor,
                seed=seed,
                n_permanent=args.n_permanent,
                total_timesteps=args.timesteps,
                results_dir=args.results_dir,
            )
            finals.append(final)
            swap_steps.append(counter.swap_step)
        swaps[monitor] = swap_steps
        true_after = float(np.mean([f["true_return"] for f in finals]))
        log.check(
            f"{monitor}: after the permanent correction the agent relearns the real task",
            true_after > 0.0,
            f"final true return {true_after:+.3f} (honest optimum +2.0), "
            f"goal rate {np.mean([f['goal_rate'] for f in finals]):.3f}, "
            f"farm steps {np.mean([f['farm_steps'] for f in finals]):.2f}",
        )
        log.check(
            f"{monitor}: the permanent correction actually fired in every seed",
            all(s is not None for s in swap_steps),
            f"swap env steps: {swap_steps}",
        )

    if all(s is not None for s in swaps["suspicion"] + swaps["flat"]):
        susp, flat = float(np.mean(swaps["suspicion"])), float(np.mean(swaps["flat"]))
        log.check(
            "the suspicion monitor accumulates detections faster, so it corrects earlier",
            susp < flat,
            f"mean swap at env step {susp:,.0f} (suspicion) vs {flat:,.0f} (flat)",
        )

    for monitor in CONDITIONS:
        log.figure(
            fig_permanent_correction(
                args.results_dir, monitor, n_permanent=args.n_permanent,
                filename=f"exp2_permanent_correction_{monitor}_n{args.n_permanent}.png",
            )
        )
    return log.summary()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--timesteps", type=int, default=500_000)
    ap.add_argument("--eval-every", type=int, default=10_000)
    ap.add_argument("--eval-episodes", type=int, default=300)
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--results-dir", default="results")
    ap.add_argument("--quick", action="store_true", help="short smoke run")
    ap.add_argument("--plots-only", action="store_true")
    ap.add_argument(
        "--phase2", action="store_true",
        help="optional section 10: the permanent training-level correction",
    )
    ap.add_argument("--n-permanent", type=int, default=50)
    args = ap.parse_args()

    if args.phase2:
        return run_phase2(args)

    if args.quick:
        args.timesteps, args.eval_every, args.eval_episodes, args.seeds = (
            60_000, 20_000, 150, 2,
        )

    log = CheckLog("EXPERIMENT 2 -- monitor shape vs damage to the true objective")
    log.note(
        f"{len(CONDITIONS)} conditions x {args.seeds} seeds x {args.timesteps:,} steps, "
        f"eval every {args.eval_every:,} on {args.eval_episodes} fresh episodes, gamma=1.0"
    )

    if not args.plots_only:
        t0 = time.time()
        for monitor in CONDITIONS:
            for seed in range(args.seeds):
                train_one(
                    monitor,
                    seed,
                    total_timesteps=args.timesteps,
                    eval_every=args.eval_every,
                    n_eval_episodes=args.eval_episodes,
                    results_dir=args.results_dir,
                    verbose=False,
                )
                print(f"  trained {monitor} seed {seed}  ({time.time() - t0:.0f}s elapsed)")
        log.note(f"training wall clock: {time.time() - t0:.0f}s")

    data = load_results(args.results_dir)
    n_seeds = len(data[CONDITIONS[0]]["seeds"])

    # ------------------------------------------------------------------ #
    # trained policy vs the reference table
    # ------------------------------------------------------------------ #
    print("\n  Trained PPO vs the section-8 reference (mean of last 5 evals, all seeds)")
    print(f"  {'':22s} {'PPO':>9s} {'reference':>10s} {'delta':>8s}")
    for monitor in CONDITIONS:
        print(f"  --- {CONDITION_LABEL[monitor]} ---")
        for metric, ref_key, tol in COMPARE:
            got = final_window(data, monitor, metric)
            want = REFERENCE[monitor][ref_key]
            log.check(
                f"{monitor}: {metric} near the memoryless optimum",
                abs(got - want) <= tol,
                f"PPO {got:.3f} vs reference {want:.3f} (tolerance +-{tol})",
            )
            print(f"  {metric:22s} {got:9.3f} {want:10.3f} {got - want:+8.3f}")

    # ------------------------------------------------------------------ #
    # the headline: the gap between the two monitors
    # ------------------------------------------------------------------ #
    per_seed = {m: final_window_per_seed(data, m, "true_return") for m in CONDITIONS}
    gap = float(per_seed["suspicion"].mean() - per_seed["flat"].mean())
    gap_sd = float(np.sqrt(per_seed["suspicion"].var(ddof=1) / n_seeds
                           + per_seed["flat"].var(ddof=1) / n_seeds))
    ref_gap = REFERENCE["suspicion"]["true_return"] - REFERENCE["flat"]["true_return"]

    log.check(
        "the suspicion monitor limits true-reward damage better than the flat control",
        gap > 0,
        f"mean true return {per_seed['suspicion'].mean():+.3f} (suspicion) vs "
        f"{per_seed['flat'].mean():+.3f} (flat)",
    )
    log.check(
        "the gap reproduces the reference (~5.7 units of true return)",
        abs(gap - ref_gap) <= 1.5,
        f"measured gap {gap:+.3f} +- {gap_sd:.3f} across {n_seeds} seeds, "
        f"reference {ref_gap:+.3f}",
    )
    damage_susp = REFERENCE["honest_optimum_return"] - per_seed["suspicion"].mean()
    damage_flat = REFERENCE["honest_optimum_return"] - per_seed["flat"].mean()
    log.check(
        "the suspicion monitor limits damage roughly twice as well",
        1.5 <= damage_flat / damage_susp <= 2.5,
        f"damage below the honest optimum: {damage_susp:.2f} (suspicion) vs "
        f"{damage_flat:.2f} (flat) = {damage_flat / damage_susp:.2f}x",
    )

    # ------------------------------------------------------------------ #
    # the guard against leakage, and the negative result about goal rate
    # ------------------------------------------------------------------ #
    for monitor in CONDITIONS:
        got = final_window(data, monitor, "true_return")
        log.check(
            f"{monitor}: PPO is not meaningfully BETTER than the memoryless optimum",
            got <= REFERENCE[monitor]["true_return"] + 1.5,
            f"true return {got:.3f} vs memoryless ceiling "
            f"{REFERENCE[monitor]['true_return']:.3f} -- beating it would mean the "
            "clock or the suspicion level has leaked into the observation",
        )
    for monitor in CONDITIONS:
        log.check(
            f"{monitor}: goal-reach rate stays high while true return collapses",
            final_window(data, monitor, "goal_rate") > 0.85,
            f"goal rate {final_window(data, monitor, 'goal_rate'):.3f} while true "
            f"return is {final_window(data, monitor, 'true_return'):+.2f} -- task "
            "success is blind to the reward hacking",
        )

    log.finding(
        f"final mean true return: {per_seed['suspicion'].mean():+.2f} (suspicion) vs "
        f"{per_seed['flat'].mean():+.2f} (flat); gap {gap:+.2f} +- {gap_sd:.2f} over "
        f"{n_seeds} seeds. Honest optimum is +2.00."
    )

    _, paths = make_all_figures(args.results_dir)
    for p in paths:
        log.figure(p)
    return log.summary()


if __name__ == "__main__":
    main()
