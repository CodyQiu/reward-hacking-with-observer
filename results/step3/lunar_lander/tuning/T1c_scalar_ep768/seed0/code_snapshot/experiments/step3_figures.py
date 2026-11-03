"""Step 3 figures for one run of one environment, from its logged training data.

    .venv/bin/python experiments/step3_figures.py --env taxi --run-id T3_final --seeds 10 11 12 [--tag final]

Writes figures/step3_<env>_<tag>_{timeline,dashboard,episode_max,proxy_ceiling}.png.
Reference lines come from the env's Phase A: the max proxy return in a sub-episode
(no overseer) and the best monitor-avoiding return.
"""

import argparse
import csv
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.plots_step1 import plot_episode_max, plot_proxy_ceiling, plot_timeline_split
from src.plots_step3 import plot_step3_dashboard
from src.report import CheckLog
from src.step3.protocol import Protocol
from src.step3.train import RESULTS, phase_a_path


def load(env, run_id, seed):
    d = os.path.join(RESULTS, env, "tuning", run_id, f"seed{seed}")
    logs = dict(np.load(os.path.join(d, "logs.npz")))
    rounds = []
    if os.path.exists(os.path.join(d, "pbrr_rounds.csv")):
        with open(os.path.join(d, "pbrr_rounds.csv")) as fh:
            rounds = list(csv.DictReader(fh))
    with open(os.path.join(d, "config.json")) as fh:
        cfg = json.load(fh)
    return logs, rounds, cfg


def per_episode(logs, rounds, proto, refs, n_envs):
    K, T, W = proto.n_sub, proto.t_sub, proto.window
    n_ep = len(logs["caught"]) // K
    rs = lambda a: a[:n_ep * K].reshape(n_ep, K, *a.shape[1:])
    rec, prx, tru = rs(logs["env_received"]), rs(logs["env_proxy"]), rs(logs["env_true"])
    on, ca = rs(logs["on_exploit"]), rs(logs["caught"])            # on: (ep, K, T, envs)
    win = on[:, :, T - W:, :].any(axis=2)
    gx = [float(r["g_exploit"]) if r.get("g_exploit") not in (None, "", "nan") else np.nan for r in rounds]
    return {
        "received": rec.mean(axis=2), "true": tru.mean(axis=2), "proxy": prx.mean(axis=2), "env_proxy": prx,
        "rounds_per_ep": ca[:, :K - 1].sum(axis=1).mean(axis=1),
        "win_0_3": win[:, :K - 1].mean(axis=(1, 2)), "win_final": win[:, K - 1].mean(axis=1),
        "win_0": win[:, 0].mean(axis=1),
        "off_0_3": on[:, :K - 1, :T - W].mean(axis=(1, 2, 3)) / refs["offwindow_rate"],
        "ep_steps": np.arange(n_ep) * K * T * n_envs,
        "pbrr_steps": [int(r["timesteps"]) for r in rounds], "pbrr_gx": gx,
    }


def reference_lines(env):
    if env == "grid":                                           # Step 1 / 2's numbers
        from src.step3.tasks.grid import refs
        return 8700.0, 7700.0, refs()
    with open(phase_a_path(env)) as fh:
        pa = json.load(fh)
    a1 = pa["a1"]
    if "proxy_opt_proxy" in a1:
        ceiling = a1.get("sim_proxy_opt", {}).get("proxy", a1["proxy_opt_proxy"])
        avoid = pa["refs"]["proxy_0_3"]
    else:                                                       # scripted Phase A
        ceiling, avoid = a1["open"]["proxy"], pa["refs"]["proxy_0_3"]
    return ceiling, avoid, pa["refs"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--seeds", nargs="+", type=int, default=[0])
    ap.add_argument("--tag", default=None)
    args = ap.parse_args()
    tag = args.tag or args.run_id
    env = args.env
    log = CheckLog(f"Step 3 figures -- {env} {args.run_id}, seeds {args.seeds}")
    loaded = [load(env, args.run_id, s) for s in args.seeds]
    cfg = loaded[0][2]
    proto = Protocol(**cfg["protocol"])
    n_envs = int(cfg["n_envs"])
    ceiling, avoid, refs = reference_lines(env)
    refs_lines = [(ceiling, f"max proxy return in a sub-episode ({ceiling:,.0f}): exploit throughout, ignore the monitor"),
                  (avoid, f"best monitor-avoiding return ({avoid:,.0f}): stop exploiting before the audit")]
    runs = [per_episode(l, r, proto, refs, n_envs) for l, r, _ in loaded]
    name = env.replace("_", " ")
    log.figure(plot_step3_dashboard(
        runs, proto.n_sub, f"step3_{env}_{tag}_dashboard.png",
        f"Step 3, {name} ({args.run_id}): training against the PBRR overseer, all episodes",
        subtitle=f"SBX PPO, {len(runs)} seed(s) x {n_envs} parallel envs; logged training data (mean over envs, per "
                 "episode). Received reward = original proxy + the PBRR correction in force. Dotted: max proxy return "
                 "in a sub-episode; dashed: best monitor-avoiding return. Exploit step = proxy != true.",
        refs=refs_lines))
    n = min(len(r["received"]) for r in runs)
    trials = np.concatenate([r["env_proxy"][:n].transpose(2, 0, 1) for r in runs])
    log.figure(plot_episode_max(
        runs[0]["ep_steps"][:n], trials, ceiling, avoid, f"step3_{env}_{tag}_episode_max.png",
        f"{name}: max proxy return over the sub-episodes of each episode, per trial",
        subtitle=f"{trials.shape[0]} trials, each trial's own sub-episode returns under the ORIGINAL proxy. Dark: the "
                 "best sub-episode of the episode; orange: the best of sub-episodes 0-3, whose audits can trigger a "
                 "PBRR round.", hit_tol=0.02 * abs(ceiling),
        ceiling_label=f"max proxy return: exploit all {proto.t_sub} steps"))
    log.figure(plot_proxy_ceiling(
        runs[0]["ep_steps"][:n], [r["proxy"][:n, 0] for r in runs], [r["true"][:n, 0] for r in runs],
        runs[0]["ep_steps"][:n], [r["win_0"][:n] for r in runs], ceiling, avoid,
        f"step3_{env}_{tag}_proxy_ceiling.png",
        f"{name}: sub-episode 0 of every episode (reward not yet updated) vs the maximum proxy return",
        subtitle="Logged training data, mean over envs per seed. Bottom: fraction of envs that exploit during "
                 "sub-episode 0's audit (logged, not an exact evaluation).",
        ceiling_label=f"max proxy return: exploit all {proto.t_sub} steps",
        window_label="audit-window exploitation (logged)",
        window_ylabel="fraction exploiting during\nthe audit of sub-episode 0"))
    l0 = loaded[0][0]
    corrected = runs[0]["rounds_per_ep"]
    smooth = np.convolve(corrected, np.ones(10) / 10, mode="valid")
    cross = int(np.argmax((smooth < 0.5) & (np.arange(len(smooth)) > 5))) if (smooth < 0.5).any() else len(smooth) // 2
    n_ep = len(runs[0]["received"])
    windows = [(0, 8, "start of training"), (max(8, cross - 3), 8, "learning to avoid correction"),
               (n_ep - 8, 8, "end of training")]
    log.figure(plot_timeline_split(
        proto, l0["step_received"], l0["step_true"], l0["caught"].mean(axis=1), windows,
        f"step3_{env}_{tag}_timeline.png",
        f"Step 3, {name} ({args.run_id}, seed {args.seeds[0]}): received vs true reward over training",
        subtitle=f"One training run, mean over {n_envs} envs of the reward actually received (original proxy + the "
                 f"PBRR correction in force) and the true reward; y = reward so far in the current {proto.t_sub}-step "
                 "sub-episode. The reward function and the preference data reset at every dashed episode boundary.",
        steps_per_tick=n_envs, refs=refs_lines, received_label="received reward (proxy + PBRR correction)"))
    log.summary()


if __name__ == "__main__":
    main()
