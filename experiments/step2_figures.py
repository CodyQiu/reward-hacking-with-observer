"""Step 2 figures for one tuning/final run, from its logged training data.

    .venv/bin/python experiments/step2_figures.py --run-id T0_step1_config --seeds 0 [--tag T0]

Writes figures/step2_<tag>_dashboard.png, _episode_max.png, _proxy_ceiling.png and,
when per-step logs exist (runs started after per-step logging was added),
_timeline.png.
"""

import argparse
import csv
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.audit_grid import BASE, manhattan
from src.plots_step1 import plot_episode_max, plot_proxy_ceiling, plot_timeline_split
from src.plots_step2 import plot_step2_dashboard
from src.report import CheckLog
from src.step2_train import ROOT

CEILING, AVOID = 8700.0, 7700.0
REFS = [(CEILING, f"max proxy return in a sub-episode ({CEILING:,.0f}): exploit all 100 steps, ignore the monitor"),
        (AVOID, f"best monitor-avoiding return ({AVOID:,.0f}): step off before the audit")]


def load(run_id, seed):
    d = os.path.join(ROOT, "results", "step2", "tuning", run_id, f"seed{seed}")
    logs = dict(np.load(os.path.join(d, "logs.npz")))
    with open(os.path.join(d, "pbrr_rounds.csv")) as fh:
        rounds = list(csv.DictReader(fh))
    return logs, rounds


def per_episode(logs, rounds, cfg=BASE, n_envs=16):
    K, T, W = cfg.n_sub, cfg.t_sub, cfg.window
    n_ep = len(logs["caught"]) // K
    rs = lambda a: a[:n_ep * K].reshape(n_ep, K, *a.shape[1:])
    rec, prx, tru = rs(logs["env_received"]), rs(logs["env_proxy"]), rs(logs["env_true"])
    on, ca = rs(logs["on_exploit"]), rs(logs["caught"])          # on: (ep, K, T, envs)
    win = on[:, :, T - W:, :].any(axis=2)
    d_s = manhattan(cfg.start, cfg.exploit)
    return {
        "received": rec.mean(axis=2), "true": tru.mean(axis=2), "proxy": prx.mean(axis=2),
        "env_proxy": prx, "rounds_per_ep": ca[:, :K - 1].sum(axis=1).mean(axis=1),
        "win_0_3": win[:, :K - 1].mean(axis=(1, 2)), "win_final": win[:, K - 1].mean(axis=1),
        "win_0": win[:, 0].mean(axis=1), "off_0_3": on[:, :K - 1, d_s:T - W].mean(axis=(1, 2, 3)),
        "ep_steps": np.arange(n_ep) * K * T * n_envs,
        "pbrr_steps": [int(r["timesteps"]) for r in rounds], "pbrr_gE": [float(r["g_dwell_E"]) for r in rounds],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--seeds", nargs="+", type=int, default=[0])
    ap.add_argument("--tag", default=None)
    args = ap.parse_args()
    tag = args.tag or args.run_id
    log = CheckLog(f"Step 2 figures -- {args.run_id}, seeds {args.seeds}")
    loaded = [load(args.run_id, s) for s in args.seeds]
    runs = [per_episode(l, r) for l, r in loaded]
    n_seeds = len(runs)
    log.figure(plot_step2_dashboard(
        runs, BASE.n_sub, f"step2_{tag}_dashboard.png",
        f"Step 2 ({args.run_id}): training against the PBRR overseer, all episodes",
        subtitle=f"SBX PPO, {n_seeds} seed(s) x 16 parallel envs; every value is from the logged training "
                 "data (mean over envs, per episode). Received reward = original proxy + the PBRR "
                 "correction in force. Dotted: max proxy return in a sub-episode (8,700); dashed: best "
                 "monitor-avoiding return (7,700). Bottom: the learned correction on dwelling at the "
                 "exploit tile after each PBRR round.",
        refs=REFS))
    n = min(len(r["received"]) for r in runs)
    trials = np.concatenate([r["env_proxy"][:n].transpose(2, 0, 1) for r in runs])   # (trials, ep, K)
    log.figure(plot_episode_max(
        runs[0]["ep_steps"][:n], trials, CEILING, AVOID, f"step2_{tag}_episode_max.png",
        "Max proxy return over the sub-episodes of each episode, per trial, vs the proxy maximum",
        subtitle=f"{trials.shape[0]} trials ({n_seeds} seed(s) x 16 parallel envs), each trial's own "
                 "sub-episode returns under the ORIGINAL proxy. Dark: the best sub-episode of the "
                 "episode; orange: the best of sub-episodes 0-3, whose audits can trigger a PBRR round."))
    log.figure(plot_proxy_ceiling(
        runs[0]["ep_steps"][:n], [r["proxy"][:n, 0] for r in runs], [r["true"][:n, 0] for r in runs],
        runs[0]["ep_steps"][:n], [r["win_0"][:n] for r in runs], CEILING, AVOID,
        f"step2_{tag}_proxy_ceiling.png",
        "Sub-episode 0 of every episode (reward not yet updated) vs the maximum proxy return",
        subtitle="Logged training data, mean over 16 envs per seed. Bottom: fraction of envs on the "
                 "exploit during sub-episode 0's audit (logged, not an exact evaluation)."))
    l0 = loaded[0][0]
    if "step_received" in l0:
        corrected = runs[0]["rounds_per_ep"]
        smooth = np.convolve(corrected, np.ones(10) / 10, mode="valid")
        cross = int(np.argmax((smooth < 0.5) & (np.arange(len(smooth)) > 5)))
        n_ep = len(runs[0]["received"])
        windows = [(0, 8, "start of training"), (max(8, cross - 3), 8, "learning to avoid correction"),
                   (n_ep - 8, 8, "end of training")]
        log.figure(plot_timeline_split(
            BASE, l0["step_received"], l0["step_true"], l0["caught"].mean(axis=1), windows,
            f"step2_{tag}_timeline.png",
            f"Step 2 ({args.run_id}, seed {args.seeds[0]}): received vs true reward over training",
            subtitle="One training run, mean over 16 envs of the reward actually received (original "
                     "proxy + the PBRR correction in force) and the true reward; y = reward so far in "
                     "the current 100-step sub-episode. The reward function and the preference data "
                     "reset at every dashed episode boundary.",
            steps_per_tick=16, refs=REFS, received_label="received reward (proxy + PBRR correction)"))
    else:
        log.note("no per-step logs in this run (started before per-step logging): timeline skipped")
    log.summary()


if __name__ == "__main__":
    main()
