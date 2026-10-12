"""Step 1, learning: does SBX PPO find the audit-avoiding policy that exact DP predicts?

Same environment as experiments/step1_dp.py. 16 synchronised envs, n_steps = 100, so
every PPO update lands on a round (sub-episode) boundary, right after the overseer's
reward update; the reward resets every 500-step episode, the policy never does.

All rewards are reported **per sub-episode**: the return restarts from 0 at every
boundary. Only the *reporting* resets -- the learner's objective still spans the
episode (PPO bootstraps across sub-episode boundaries).

By default only the main condition is run (audit the last W = 10 steps of every
sub-episode). ``--conditions`` also accepts myopic, whole_window, toothless and
no_clock, but they are not part of the current results.

    .venv/bin/python experiments/step1_ppo.py                 # main, 3 seeds
    .venv/bin/python experiments/step1_ppo.py --quick         # smoke run
    .venv/bin/python experiments/step1_ppo.py --plots-only    # rebuild figures from results/
"""

import argparse
import csv
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.audit_dp import evaluate, greedy_probs, signatures, solve
from src.audit_grid import BASE, manhattan
from src.audit_train import CONDITIONS, N_ENVS, condition_setup, train_one
from src.plots_step1 import (plot_episode_max, plot_proxy_ceiling, plot_training_curves, plot_training_heatmap,
                              plot_timeline_split, plot_training_timeline)
from src.report import CheckLog

RESULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "results", "step1_ppo")
DEFAULT_CONDITIONS = ["main"]
LABEL = {
    "main": "Main: audit the last 10 steps of each sub-episode",
    "myopic": "Control: myopic learner (each sub-episode terminal)",
    "whole_window": "Control: overseer audits the whole round",
    "toothless": "Control: detection never changes the reward",
    "no_clock": "Control: no clock in the observation",
}
N_FINAL = 3  # end-of-training metrics: mean of the last N exact evaluations per seed


def _read_csv(path):
    with open(path) as fh:
        return [{k: (v == "True") if v in ("True", "False") else float(v) for k, v in r.items()}
                for r in csv.DictReader(fh)]


def load(condition, seeds, results_dir=RESULTS):
    out = []
    for s in seeds:
        stem = os.path.join(results_dir, f"{condition}_seed{s}")
        if os.path.exists(stem + "_steps.npz"):
            out.append({"evals": _read_csv(stem + ".csv"), "rounds": _read_csv(stem + "_rounds.csv"),
                        "npz": dict(np.load(stem + ".npz")), "steps": dict(np.load(stem + "_steps.npz"))})
    return out


def dp_reference(condition):
    ecfg, _, myopic = condition_setup(condition)
    _, pol = solve(ecfg, myopic=myopic)
    return ecfg, evaluate(ecfg, greedy_probs(ecfg, pol))


def window_stats(cfg, occ):
    """P(bonus | loophole open): off-window and in-window for rounds 0..K-2, final window."""
    T, W, K = cfg.t_sub, cfg.window, cfg.n_sub
    d_s = manhattan(cfg.start, cfg.exploit)
    occ = np.asarray(occ).reshape(K, T)
    return occ[:-1, d_s:T - W].mean(), occ[:-1, T - W:].mean(), occ[-1, T - W:].mean()


def open_probability(cfg, npz):
    """P(loophole still open in round k) under each evaluated policy, (n_eval, K).

    Recovered from the saved occupancies: P(bonus) = P(bonus | open) * P(open), and
    P(open) is constant within a round (a patch lands only at a boundary). Rounds in
    which the bonus is never collected give no information and return 0.
    """
    b = npz["bonus"].reshape(len(npz["bonus"]), cfg.n_sub, cfg.t_sub)
    bu = npz["bonus_unpatched"].reshape(b.shape)
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(bu > 1e-6, b / bu, np.nan)
    out = np.nanmax(np.concatenate([ratio, np.zeros(b.shape[:2] + (1,))], axis=-1), axis=-1)
    return np.clip(out, 0.0, 1.0)


def summarize(cfg, runs):
    """Seed mean and s.d. of end-of-training metrics."""
    per = {}

    def add(key, val):
        per.setdefault(key, []).append(float(val))

    for run in runs:
        tail = run["evals"][-N_FINAL:]
        for k in range(cfg.n_sub):
            add(f"proxy_k{k}", np.mean([r[f"proxy_k{k}"] for r in tail]))
            add(f"true_k{k}", np.mean([r[f"true_k{k}"] for r in tail]))
            add(f"leave_k{k}", np.mean([r[f"leave_k{k}"] for r in tail]))
        add("corrections", np.mean([r["corrections"] for r in tail]))
        st = np.array([window_stats(cfg, o) for o in run["npz"]["bonus_unpatched"][-N_FINAL:]])
        for j, key in enumerate(("off", "win", "final")):
            add(key, np.nanmean(st[:, j]))
    return {k: (np.mean(v), np.std(v)) for k, v in per.items()}


def make_figures(log, conditions, seeds, results_dir=RESULTS):
    loaded = {c: load(c, seeds, results_dir) for c in conditions}
    loaded = {c: r for c, r in loaded.items() if r}
    if not loaded:
        return loaded
    n_seeds = len(next(iter(loaded.values())))

    curve_cols = []
    for c, runs in loaded.items():
        ecfg, dp = dp_reference(c)
        K = ecfg.n_sub
        n_ep = min(len(r["rounds"]) for r in runs) // K
        per = {key: [] for key in ("proxy_return", "true_return", "patched")}
        for r in runs:
            assert [row["k"] for row in r["rounds"][:n_ep * K]] == list(range(K)) * n_ep, "rounds out of phase"
            for key in per:
                per[key].append(np.array([row[key] for row in r["rounds"][:n_ep * K]]).reshape(n_ep, K))
        n_eval = min(len(r["evals"]) for r in runs)
        eval_ep = np.array([row["timesteps"] for row in runs[0]["evals"][:n_eval]]) / (N_ENVS * ecfg.t_ep)
        # "When does it leave the tile" is conditional on the loophole still being open.
        # Where the evaluated policy reaches round k with the loophole open with
        # probability < 5% (e.g. myopic rounds 1-4), the conditional is noise: mask it.
        leave_seeds = []
        for r in runs:
            lv = np.array([[row[f"leave_k{k}"] for k in range(K)] for row in r["evals"][:n_eval]])
            lv[open_probability(ecfg, r["npz"])[:n_eval] < 0.05] = np.nan
            leave_seeds.append(lv)
        with np.errstate(all="ignore"):
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                leave = np.nanmean(leave_seeds, axis=0)
        sig = signatures(ecfg, dp["bonus_unpatched"])
        curve_cols.append({
            "name": LABEL[c],
            "proxy": np.mean(per["proxy_return"], axis=0), "true": np.mean(per["true_return"], axis=0),
            # the reward has been patched before the last round = corrected by audits 0..K-2
            "corrected": np.array([p[:, K - 1] for p in per["patched"]]),
            "eval_ep": eval_ep, "leave": leave, "window_start": ecfg.t_sub - ecfg.window,
            "dp_proxy": dp["proxy_by_k"], "dp_true": dp["true_by_k"],
            "dp_corrected": dp["corrections"], "dp_leave": sig["leave"],
        })
    n_eps = len(curve_cols[0]["proxy"])

    # Reference returns for one sub-episode, from the exact DP of the base problem:
    # the proxy ceiling (exploit all 100 steps, as if there were no monitor) and the
    # best return of an agent that avoids the monitor (step off before the audit).
    _, dp_main = dp_reference("main")
    _, dp_free = dp_reference("toothless")
    ceiling, avoid = float(dp_free["proxy_by_k"][0]), float(dp_main["proxy_by_k"][0])
    refs = [(ceiling, f"max proxy return in a sub-episode ({ceiling:,.0f}): exploit all 100 steps, ignore the monitor"),
            (avoid, f"best monitor-avoiding return ({avoid:,.0f}): step off before the audit")]

    # The lead's check: does sub-episode 0 (always under the not-yet-updated proxy) reach
    # the maximum proxy return, and then fall to the monitor-avoiding return?
    if "main" in loaded:
        runs = loaded["main"]
        K = BASE.n_sub
        n_ep = min(len(r["rounds"]) for r in runs) // K
        sub0 = lambda r, key: np.array([row[key] for row in r["rounds"][:n_ep * K]]).reshape(n_ep, K)[:, 0]
        n_eval = min(len(r["evals"]) for r in runs)
        log.figure(plot_proxy_ceiling(
            sub0(runs[0], "timesteps") - BASE.t_sub * N_ENVS,          # start of sub-episode 0
            [sub0(r, "proxy_return") for r in runs], [sub0(r, "true_return") for r in runs],
            [row["timesteps"] for row in runs[0]["evals"][:n_eval]],
            [[row["window_k0"] for row in r["evals"][:n_eval]] for r in runs],
            ceiling, avoid, "step1_ppo_proxy_ceiling.png",
            "Sub-episode 0 of every episode (reward not yet updated) vs the maximum proxy return",
            subtitle=f"SBX PPO, {len(runs)} seeds, each value the mean over 16 parallel envs of the "
                     "reward received in the first sub-episode of each training episode, which always "
                     "runs under the original flawed proxy. Dotted: the most the proxy can pay in it "
                     f"({ceiling:,.0f}: walk to the exploit and stay all 100 steps). Dashed: the best "
                     f"an agent that avoids the monitor can earn ({avoid:,.0f}: step off before the "
                     "last-10-step audit). Bottom: how often the policy is still on the exploit during "
                     "that audit (exact evaluation every 12 episodes).",
        ))

    # The lead's check, per episode: the max proxy return over an episode's sub-episodes,
    # against the proxy ceiling. Uses the per-sub-episode returns averaged over the 16
    # parallel envs (the same data as every other figure), one trial = one seed.
    if "main" in loaded:
        runs = loaded["main"]
        K = BASE.n_sub
        n_ep = min(len(r["rounds"]) for r in runs) // K
        trials = np.array([[row["proxy_return"] for row in r["rounds"][:n_ep * K]] for r in runs]
                          ).reshape(len(runs), n_ep, K)
        ep_start = np.arange(n_ep) * K * BASE.t_sub * N_ENVS
        mx = trials.max(axis=2)
        log.note("per-episode max proxy return (seed mean, 16-env average): "
                 + ", ".join(f"episodes {a}-{a + 9}: {mx[:, a:a + 10].mean():,.0f}" for a in (0, 10, 20, 50, 100, n_ep - 10))
                 + f"; overall max {mx.max():,.0f}")
        log.figure(plot_episode_max(
            ep_start, trials, ceiling, avoid, "step1_ppo_episode_max.png",
            "Max proxy return over the sub-episodes of each episode, vs the proxy maximum",
            subtitle=f"SBX PPO, {len(runs)} seeds; each sub-episode return is the mean over the 16 "
                     "parallel envs (the same data as the other figures), so a value of 8,700 needs "
                     "all 16 to exploit perfectly. Line: median over seeds, band: their range. Dark: "
                     "the best sub-episode of the episode; the last sub-episode has no audit that "
                     "matters (the reward resets next), so a hiding agent still earns the max there. "
                     "Orange: the best of sub-episodes 0-3, where staying through the audit gets the "
                     "reward corrected; a monitor-avoiding agent earns at most 7,700 in these.",
            hit_tol=100.0,
        ))

    # The headline: one training run on its real time axis, per condition.
    for c, runs in loaded.items():
        ecfg, _ = dp_reference(c)
        run, seed = runs[0], seeds[0]
        n_ep = len(run["steps"]["k"]) // ecfg.n_sub
        if c == "main":
            corrected = np.array([row["patched"] for row in run["rounds"]]).reshape(-1, ecfg.n_sub)[:, -1]
            smooth = np.convolve(corrected, np.ones(10) / 10, mode="valid")
            cross = int(np.argmax((smooth < 0.5) & (np.arange(len(smooth)) > 5)))
            mid = (max(8, cross - 3), "learning to avoid correction: the later sub-episodes stop "
                                      "collapsing to the true reward")
        else:
            mid = (n_ep // 2 - 4, "middle of training: still corrected after every first audit")
        windows = [(0, 8, "start of training: no exploit at first; then it exploits sub-episode 0 "
                          "and is corrected for the rest of each episode"),
                   (mid[0], 8, mid[1]),
                   (n_ep - 8, 8, "end of training")]
        story = {
            "main": "The agent does not exploit for the first two episodes, then exploits sub-episode 0 "
                    "and is corrected (later sub-episodes earn only the true reward). It then learns to "
                    "step off the exploit before each audit, so it stops being corrected and every "
                    "sub-episode keeps the exploit: the proxy-true gap stays open for the rest of "
                    "training. Rare lapses remain (e.g. episode 379 in C: it dwelt through the first "
                    "audit and was corrected for that episode).",
            "myopic": "Same environment, but the learner values each sub-episode on its own. It finds "
                      "the exploit just as fast, yet never learns to protect it: it exploits through "
                      "the first audit of every episode, is corrected, and earns only the true reward "
                      "for the remaining sub-episodes, for the whole of training.",
        }.get(c, "")
        log.figure(plot_timeline_split(
            ecfg, run["steps"]["proxy"], run["steps"]["true"],
            [row["detected"] for row in run["rounds"]], windows,
            f"step1_ppo_timeline_{c}.png",
            f"{LABEL[c]}: proxy vs true reward over training (seed {seed})",
            subtitle=f"{story} One SBX PPO training run; every value is the mean over its 16 parallel "
                     "environments of the reward actually received. y = reward accumulated so far in "
                     "the current 100-step sub-episode, restarting at 0 at every sub-episode; the "
                     "reward function resets to the flawed proxy at every episode boundary (every 5 "
                     "sub-episodes), the policy never resets. x counts all training samples "
                     "(16 envs x env steps).",
            steps_per_tick=N_ENVS, refs=refs,
        ))
        # Requested by the TA: the first 11 episodes (0-10) on their own, full width.
        log.figure(plot_training_timeline(
            ecfg, run["steps"]["proxy"], run["steps"]["true"],
            [(0, 11, "episodes 0-10")],
            f"step1_ppo_timeline_{c}_ep0-10.png",
            f"{LABEL[c]}: the first 11 training episodes (seed {seed})",
            subtitle="Same run and data as the full timeline figure: mean over 16 parallel envs of the "
                     "reward actually received; y = reward so far in the current 100-step "
                     "sub-episode, restarting at 0 at every sub-episode; the reward function resets "
                     "at every dashed episode boundary.",
            steps_per_tick=N_ENVS, overview=False, refs=refs,
        ))

    log.figure(plot_training_curves(
        curve_cols, BASE.n_sub, "step1_ppo_training_curves.png",
        f"Training curves over all {n_eps} episodes: the agent finds the exploit within ~5 "
        "episodes, then learns to stop getting corrected",
        subtitle=f"SBX PPO, mean over {n_seeds} seeds and 16 envs; rows 1-3 use the reward actually "
                 "received in training, row 4 the exact evaluation every 12 episodes (shown only where the loophole is still open in >= 5% of runs). Return is per "
                 "100-step round (restarts at 0 every round), one line per round k of the episode; "
                 "proxy and true have their own y scales. The reward resets to the flawed proxy "
                 "every episode, the policy never resets. Main: corrected in almost every episode "
                 "at first, then the agent learns to step off the exploit before each audit, "
                 "corrections fall to ~0, and every round keeps earning the exploit.",
    ))
    if "main" in loaded:
        npz = loaded["main"][0]["npz"]
        log.figure(plot_training_heatmap(
            BASE, npz["timesteps"], npz["bonus_unpatched"], "step1_ppo_heatmap_main.png",
            f"Main condition, seed {seeds[0]}: when in each round the agent exploits, over training",
            subtitle="P(bonus | loophole still open) by step tau within each round k. Line: the "
                     "audit window opens (tau = 90).",
        ))
    return loaded


def checks(log, loaded):
    sums = {c: summarize(condition_setup(c)[0], runs) for c, runs in loaded.items()}
    for c, s in sums.items():
        f = lambda key, p=0: f"{s[key][0]:.{p}f}±{s[key][1]:.{p}f}"
        log.note(f"{c:8s} round proxy " + " ".join(f(f"proxy_k{k}") for k in range(5))
                 + " | round true " + " ".join(f(f"true_k{k}") for k in range(5))
                 + f" | corrections {f('corrections', 2)}")
    if "main" in sums:
        s = sums["main"]
        _, dp = dp_reference("main")
        log.check("main: rounds 0..3 earn >= 95% of the exact optimum's proxy (7,700)",
                  all(s[f"proxy_k{k}"][0] >= 0.95 * dp["proxy_by_k"][k] for k in range(4)),
                  " ".join(f"{s[f'proxy_k{k}'][0]:.0f}" for k in range(4)))
        log.check("main: true return stays at the exact optimum's -100 per round",
                  all(abs(s[f"true_k{k}"][0] - dp["true_by_k"][k]) < 5 for k in range(5)),
                  " ".join(f"{s[f'true_k{k}'][0]:.0f}" for k in range(5)))
        log.check("main: audit windows of rounds 0..3 kept clean", s["win"][0] < 0.05, f"{s['win'][0]:.3f}")
        log.check("main: exploits through the final window", s["final"][0] > 0.8, f"{s['final'][0]:.2f}")
        log.check("main: leaves the tile at tau = 90 in rounds 0..3, stays in round 4",
                  all(abs(s[f"leave_k{k}"][0] - 90) <= 2 for k in range(4)) and s["leave_k4"][0] >= 98,
                  " ".join(f"{s[f'leave_k{k}'][0]:.1f}" for k in range(5)))
        log.check("main: rarely corrected", s["corrections"][0] < 0.1, f"{s['corrections'][0]:.3f}")
    if "myopic" in sums:
        s = sums["myopic"]
        log.check_control("myopic: exploits through the first audit and is corrected",
                          s["corrections"][0] > 0.9, f"corrections {s['corrections'][0]:.2f}")
        log.check_control("myopic: after the correction proxy = true (gap closed in rounds 1..4)",
                          all(abs(s[f"proxy_k{k}"][0] - s[f"true_k{k}"][0]) < 0.05 * s["proxy_k0"][0]
                              for k in range(1, 5)),
                          " ".join(f"{s[f'proxy_k{k}'][0] - s[f'true_k{k}'][0]:.0f}" for k in range(5)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--conditions", nargs="+", default=DEFAULT_CONDITIONS, choices=CONDITIONS)
    ap.add_argument("--seeds", nargs="+", type=int, default=[0, 1, 2])
    ap.add_argument("--timesteps", type=int, default=3_072_000)
    ap.add_argument("--eval-every", type=int, default=96_000)
    ap.add_argument("--quick", action="store_true", help="1 seed, 192k steps, figures but no checks")
    ap.add_argument("--plots-only", action="store_true")
    args = ap.parse_args()
    results_dir = RESULTS
    if args.quick:
        args.seeds, args.timesteps, args.eval_every = [0], 192_000, 32_000
        results_dir = os.path.join(RESULTS, "quick")

    log = CheckLog("Step 1 -- SBX PPO on the 15x15 audit grid vs the exact optimum")
    if not args.plots_only:
        for c in args.conditions:
            for s in args.seeds:
                train_one(c, s, total_timesteps=args.timesteps, eval_every=args.eval_every,
                          results_dir=results_dir)
    loaded = make_figures(log, args.conditions, args.seeds, results_dir)
    if args.quick:
        log.check("quick run produced results", bool(loaded))
    else:
        checks(log, loaded)
    log.summary()


if __name__ == "__main__":
    main()
