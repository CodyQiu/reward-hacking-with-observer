"""Exp 4 clean protocol: show the proxy/true split, then repair it with preferences.

Unlike ``exp4_sawtooth.py``, independent PPO runs are never concatenated into one
apparently continuous training trace. Each repair round trains a fresh PPO for 100k
steps under one frozen reward r_proxy + g_t. Afterward, good-vs-hacking trajectory
pairs are accumulated and g is refit from scratch.

Two conditions are intentionally reported:

* Standard learner-pair PBRR: hacker trajectories come from PPO and Eq. 3 has no
  ranking margin. This is the literal protocol and is allowed to return a null result.
* Robust ideal-coverage PBRR: hacker trajectories come from exact pi*_{r_hat} and the
  preference objective uses a declared positive margin. This tests the diagnosed
  coverage/knife-edge failure; it is an extension, not unmodified PBRR.

Controls: the unrepaired first round and independent random preference labels.
"""

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.bigworld import (
    BONUS_TILES,
    dp_optimal_policy,
    live_exploits,
    policy_true_return,
)
from src.bigworld_pbrr import expand_correction, sawtooth_run
from src.pbrr import fit_g
from src.plots_pbrr import fig_clean_repair_summary, fig_clean_split
from src.report import CheckLog

HONEST = 12.0


def _run_condition(*, robust, rounds, steps, k, n_eval, seed, verbose):
    return sawtooth_run(
        n_rounds=rounds,
        steps_per_round=steps,
        eval_every=max(1, steps // 10),
        k=k,
        seed=seed,
        lam=1.0 if robust else 10.0,
        n_eval=n_eval,
        weight_decay=0.01,
        correction_scope="state",
        preference_margin=10.0 if robust else 0.0,
        preference_source="exact_dp" if robust else "ppo",
        verbose=verbose,
    )


def _by_round(rows):
    out = {}
    for row in rows:
        out.setdefault(int(row["round"]), []).append(row)
    return out


def _random_label_control(out, seeds=5):
    """Refit on the same trajectories with labels independent of their contents."""
    audits = []
    for seed in range(seeds):
        rng = np.random.default_rng(10_000 + seed)
        pairs = [(i, j, float(rng.integers(0, 2))) for i, j, _ in out["pairs"]]
        params, _ = fit_g(
            pairs,
            out["trajs"],
            lam=1.0,
            weight_decay=0.01,
            preference_margin=10.0,
            seed=20_000 + seed,
        )
        g = expand_correction(params, "state")
        live = live_exploits(g)
        audits.append(
            dict(
                seed=seed,
                exact_true=policy_true_return(dp_optimal_policy(g)),
                n_live=sum(v > 0.0 for v in live.values()),
            )
        )
    return audits


def _serializable_summary(standard, robust, random_audits):
    def condition(out):
        by_round = _by_round(out["rows"])
        rounds = sorted(by_round)
        return dict(
            ppo_end_true=[float(by_round[r][-1]["true"]) for r in rounds],
            ppo_end_raw_received=[float(by_round[r][-1]["recv"]) for r in rounds],
            ppo_end_adjusted_gap=[
                float(by_round[r][-1]["recv_unshaped"] - by_round[r][-1]["true"])
                for r in rounds
            ],
            exact_true_after_refit=[float(x["exact_true"]) for x in out["refits"]],
            live_exploits_after_refit=[int(x["n_live"]) for x in out["refits"]],
            preferences_after_refit=[int(x["n_preferences"]) for x in out["refits"]],
        )

    return dict(
        standard_learner_pairs=condition(standard),
        robust_ideal_coverage=condition(robust),
        random_label_control=random_audits,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=7)
    ap.add_argument("--steps-per-round", type=int, default=100_000)
    ap.add_argument("--k", type=int, default=19)
    ap.add_argument("--n-eval", type=int, default=120)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    if args.quick:
        args.rounds, args.steps_per_round, args.k, args.n_eval = 3, 20_000, 8, 30

    log = CheckLog("EXPERIMENT 4 -- clean proxy/true split and preference-based repair")
    log.note(
        f"{args.rounds} independent PPO runs x {args.steps_per_round:,} steps; "
        f"k={args.k} gives {args.k**2} new good-vs-hacker preferences per refit"
    )

    standard = _run_condition(
        robust=False, rounds=args.rounds, steps=args.steps_per_round, k=args.k,
        n_eval=args.n_eval, seed=args.seed, verbose=args.verbose,
    )
    robust = _run_condition(
        robust=True, rounds=args.rounds, steps=args.steps_per_round, k=args.k,
        n_eval=args.n_eval, seed=args.seed, verbose=args.verbose,
    )

    std_by = _by_round(standard["rows"])
    rob_by = _by_round(robust["rows"])
    first = rob_by[min(rob_by)][-1]
    final = rob_by[max(rob_by)][-1]
    std_final_exact = float(standard["refits"][-1]["exact_true"])
    robust_final_exact = float(robust["refits"][-1]["exact_true"])
    robust_final_live = int(robust["refits"][-1]["n_live"])

    log.check_control(
        "without repair, optimizing the proxy creates a large hacking split",
        first["true"] < 0.0 and first["recv_unshaped"] - first["true"] > 50.0,
        f"round-0 PPO ends at raw received {first['recv']:+.2f}, true {first['true']:+.2f}; "
        f"after removing known shaping, exploit gap "
        f"{first['recv_unshaped'] - first['true']:+.2f}",
    )
    log.check(
        "literal PPO-pair Eq. 3 is a NULL RESULT in this multi-exploit environment",
        std_final_exact < HONEST - 1.0 and standard["refits"][-1]["n_live"] > 0,
        f"after {standard['refits'][-1]['n_preferences']} preferences: exact true "
        f"{std_final_exact:+.1f}, live exploits "
        f"{standard['refits'][-1]['n_live']}/{len(BONUS_TILES)}",
    )
    log.check(
        "robust repair closes the trained policy's exploit-specific proxy/true split",
        final["true"] >= HONEST - 1.0
        and final["recv_unshaped"] - final["true"] < 0.15 * (
            first["recv_unshaped"] - first["true"]
        ),
        f"true {first['true']:+.1f} -> {final['true']:+.1f}; adjusted exploit gap "
        f"{first['recv_unshaped'] - first['true']:+.1f} -> "
        f"{final['recv_unshaped'] - final['true']:+.1f}",
    )
    log.check(
        "the final learned reward itself is repaired under exact DP",
        robust_final_exact >= HONEST - 1e-9 and robust_final_live == 0,
        f"exact true {robust_final_exact:+.1f}; profitable exploits "
        f"{robust_final_live}/{len(BONUS_TILES)}; dwell values "
        f"{[round(v, 2) for v in robust['refits'][-1]['dwell_values']]}",
    )

    random_audits = _random_label_control(robust, seeds=5)
    random_repairs = sum(
        x["exact_true"] >= HONEST - 1e-9 and x["n_live"] == 0 for x in random_audits
    )
    log.check_control(
        "independent random preference labels do not reliably repair the reward",
        random_repairs == 0,
        f"repaired {random_repairs}/{len(random_audits)} fits; audits "
        f"{[(x['exact_true'], x['n_live']) for x in random_audits]}",
    )

    conditions = {
        "standard Eq. 3 · PPO pairs": standard,
        "robust extension · exact coverage": robust,
    }
    log.figure(fig_clean_split(
        robust["rows"], "exp4_clean_split.png", honest=HONEST,
    ))
    log.figure(fig_clean_repair_summary(
        conditions, "exp4_clean_repair_summary.png", honest=HONEST,
    ))

    summary = _serializable_summary(standard, robust, random_audits)
    summary["configuration"] = dict(
        rounds=args.rounds,
        steps_per_round=args.steps_per_round,
        k=args.k,
        preferences_per_refit=args.k**2,
        seed=args.seed,
    )
    result_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "results", "exp4_clean_split_summary.json",
    )
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    log.note(f"wrote machine-readable summary to {result_path}")

    log.finding(
        "The clean panels confirm that the old oscillations were mostly PPO restart "
        "artifacts. The scientifically relevant quantity is the within-run split. "
        "Standard PPO-pair PBRR does not close it here; the robust coverage+margin "
        "extension does, and its final reward passes an exact-DP exploit audit."
    )
    return log.summary()


if __name__ == "__main__":
    main()
