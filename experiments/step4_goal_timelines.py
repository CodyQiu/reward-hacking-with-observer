"""Step 4 outcome audit (docs/step4_goal.md): the training timeline of every cell, in the Step 2-4 figure style.

For each env x variant of CAMPAIGN=goal, the cell's run with the smallest mean best-response gap (among tuning runs,
not confirmations, with the most finished seeds), averaged over those finished seeds:
``plot_timeline_split`` (src/plots_step1.py), the same figure as experiments/step3_figures.py's timeline: x = training
steps, y = reward accumulated within the current round (back to 0 at every boundary); received (proxy + the
correction in force) and true on separate rows; every round's audit marked by whether it triggered a correction;
zooms of 8 episodes at the start, the middle and the end of training. Mean over the seeds' logged training data
(each seed's per-step rewards are already the mean over its parallel envs), not an exact evaluation.

    .venv/bin/python experiments/step4_goal_timelines.py [--envs grid_goal ...] [--variants base P1eq1 P2swap]
    .venv/bin/python experiments/step4_goal_timelines.py --run results/step4/<env>/<campaign>/<run_id>   (one run)

Writes figures/step4_goal_<env>_<variant>_timeline.png (with --run: step4_goal_<env>_<run_id>_timeline.png) and a
copy in results/step4/goal_figures/ (committed).
"""

import argparse
import glob
import json
import os
import shutil
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.plots_step1 import plot_timeline_split  # noqa: E402
from src.step3.protocol import Protocol  # noqa: E402
from src.step3.train import ROOT  # noqa: E402

T4 = os.path.join(ROOT, "results", "step4")
OUT = os.path.join(T4, "goal_figures")
ENVS = ["grid_goal", "absent_supervisor_goal", "tomato_goal", "taxi_goal", "boat_race_goal"]
VARIANTS = ["base", "P1eq1", "P2swap"]
ENV_NAME = {"grid_goal": "Grid", "absent_supervisor_goal": "Absent Supervisor", "tomato_goal": "Tomato",
            "taxi_goal": "Taxi", "boat_race_goal": "Boat Race"}
VAR_NAME = {"base": "standard PBRR", "P1eq1": "no regulariser", "P2swap": "swap"}


def finished(seed_dir):
    try:
        return "metrics.json" in os.listdir(seed_dir)
    except FileNotFoundError:
        return False


def seed_dirs(run):
    """The run's seeds with logs: its finished ones, or (none finished yet) all that have logs."""
    have = sorted(d for d in glob.glob(os.path.join(run, "seed*")) if os.path.isdir(d)
                  and "_nockpt_" not in d and os.path.exists(os.path.join(d, "logs.npz")))
    done = [d for d in have if finished(d)]
    return done or have


def mean_gap(run):
    gaps = []
    for s in seed_dirs(run):
        fs = glob.glob(os.path.join(run, "step4_br", f"{os.path.basename(s)}_ep*.json"))
        if not fs:
            return None
        with open(max(fs, key=lambda p: int(p.rsplit("_ep", 1)[1][:-5]))) as fh:
            gaps.append(json.load(fh)["gap"])
    return float(np.mean(gaps)) if gaps else None


def pick_run(env, variant):
    cands = [r for r in glob.glob(os.path.join(T4, env, "goal", f"G1_{variant}_*"))
             if os.path.isdir(r) and not r.endswith("_confirm") and seed_dirs(r)]
    if not cands:
        return None, None
    most = max(len(seed_dirs(r)) for r in cands)
    cands = [r for r in cands if len(seed_dirs(r)) == most]
    scored = sorted((g, r) for g, r in ((mean_gap(r), r) for r in cands) if g is not None)
    return (scored[0][1], scored[0][0]) if scored else (sorted(cands)[0], None)


def reference_lines(env):
    """(value, label) per round: the proxy optimum (exploit in view) and the best uncorrected round."""
    fs = sorted(glob.glob(os.path.join(T4, env, "targets", "base", "seed*.json")))
    if not fs:
        return []
    with open(fs[0]) as fh:
        a1 = json.load(fh)["a1"]
    return [(a1["proxy_opt_proxy"], "proxy optimum (exploit, missing the goal in view)"),
            (a1["hide_proxy"], "best uncorrected round (exploit, then hidden)")]


def figure_name(env, variant, run=None):
    """The figure's file name: one per cell by default; with ``run`` (``--run`` mode) the run id, so two runs of one
    cell (e.g. ``G1_stack_P2swap_LN`` and ``G1_stack_P2swap_nohide_LN``) never overwrite each other's figure."""
    return f"step4_goal_{env}_{os.path.basename(os.path.normpath(run)) if run else variant}_timeline.png"


def draw(run, env, variant, gap=None, by_run=False):
    seeds = seed_dirs(run)
    logs = [np.load(os.path.join(s, "logs.npz")) for s in seeds]
    with open(os.path.join(seeds[0], "config.json")) as fh:
        cfg = json.load(fh)
    proto, n_envs = Protocol(**cfg["protocol"]), int(cfg["n_envs"])
    K = proto.n_sub
    n_rounds = min(len(lg["step_received"]) for lg in logs)
    n_rounds -= n_rounds % K
    rec = np.mean([lg["step_received"][:n_rounds] for lg in logs], axis=0)
    tru = np.mean([lg["step_true"][:n_rounds] for lg in logs], axis=0)
    caught = np.mean([lg["caught"][:n_rounds].mean(axis=1) for lg in logs], axis=0)
    n_ep = n_rounds // K
    w = min(8, max(1, n_ep // 3))
    windows = [(0, w, "start of training"), (max(w, n_ep // 2 - w // 2), w, "middle of training"),
               (n_ep - w, w, "end of training")]
    names = [os.path.basename(s)[4:] for s in seeds]
    fname = figure_name(env, variant, run if by_run else None)
    gap_txt = "" if gap is None else f"; mean best-response gap {gap:.3f}"
    path = plot_timeline_split(
        proto, rec, tru, caught, windows, fname,
        f"{ENV_NAME.get(env, env)}, {VAR_NAME.get(variant, variant)}: received vs true reward over training "
        f"({os.path.basename(run)}, mean over seeds {', '.join(names)})",
        subtitle=f"Logged training data, mean over {len(seeds)} seed(s) of each seed's mean over its {n_envs} envs "
                 f"({n_ep} episodes{gap_txt}). Received = original proxy + the PBRR correction in force; y = reward "
                 f"so far in the current {proto.t_sub}-step round. A round is corrected iff it misses the goal, does "
                 "not end hidden and beats the reference under the reward in force (docs/step4_goal.md). The reward "
                 "and the preference data reset at every dashed episode boundary.",
        steps_per_tick=n_envs, refs=reference_lines(env),
        received_label="received reward (proxy + PBRR correction)", caught_label=f"fraction of the {n_envs} envs corrected")
    os.makedirs(OUT, exist_ok=True)
    shutil.copy(path, os.path.join(OUT, fname))
    print(f"{env} {variant}: {os.path.basename(run)}, seeds {names}, {n_ep} episodes -> {os.path.join(OUT, fname)}",
          flush=True)
    return os.path.join(OUT, fname)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--envs", nargs="*", default=ENVS)
    ap.add_argument("--variants", nargs="*", default=VARIANTS)
    ap.add_argument("--run", default=None, help="draw this one run directory instead of picking per cell")
    args = ap.parse_args()
    if args.run:
        run = os.path.abspath(args.run)
        env = os.path.basename(os.path.dirname(os.path.dirname(run)))
        variant = os.path.basename(run).split("_")[1] if "_" in os.path.basename(run) else "run"
        draw(run, env, variant, mean_gap(run), by_run=True)
        return
    for env in args.envs:
        for v in args.variants:
            run, gap = pick_run(env, v)
            if run is None:
                print(f"{env} {v}: no run with logs yet", flush=True)
                continue
            draw(run, env, v, gap)


if __name__ == "__main__":
    main()
