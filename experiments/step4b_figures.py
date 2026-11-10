"""Step 4b: the optimal-policy campaign's results for the mentor, one seed-averaged timeline per cell.

A cell is one (env, PBRR variant) pair of docs/step4_optimal.md. For each cell this takes the config listed in
CELLS (the one that made the cell DONE, or the best so far), every finished seed of it, and draws the Step 4
timeline (received and true reward over training, src/plots_step1.plot_timeline_split) of the MEAN over those
seeds: per step, the mean over seeds of the mean over each seed's envs. The seeds share one config and length,
so they share one time axis. It also collects each seed's best-response verdict (experiments/step4_br.py, newest
check) and the exact target (experiments/step4_targets.py) into results/step4b/overview.json.

    .venv/bin/python experiments/step4b_figures.py [--cells grid:P2swap ...] [--no-figures]

Writes figures/step4b_<env>_<variant>_timeline.png and results/step4b/overview.json.
"""

import argparse
import glob
import json
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from step3_figures import reference_lines  # noqa: E402
from src.plots_step1 import plot_timeline_split  # noqa: E402
from src.step3.protocol import Protocol  # noqa: E402
from src.step3.train import ROOT  # noqa: E402

T4 = os.path.join(ROOT, "results", "step4")
OUT = os.path.join(ROOT, "results", "step4b")
VARIANT_NAME = {"P2swap": "swap (L- on the dispreferred trajectory)", "P1eq1": "no regulariser"}
# (env, variant): ([(run id, seeds), ...], episodes to draw (None = the run's length), DONE in the campaign log)
CELLS = {
    ("grid", "P2swap"): ([("O1_P2swap_LE+NET+ENT3", [0, 1, 2]), ("O1_P2swap_LE+NET+ENT3_confirm", [20, 21, 22])],
                         None, True),
    ("grid", "P1eq1"): ([("O1_P1eq1_LN+LR+ES10", [0, 1, 2])], None, False),
    ("absent_supervisor", "P2swap"): ([("O1_P2swap_LN", [0, 1, 2]), ("O1_P2swap_LN_confirm", [20, 21, 22])],
                                      None, True),
    ("absent_supervisor", "P1eq1"): ([("O1_P1eq1_LN+RS", [0, 1, 2]), ("O1_P1eq1_LN+RS_confirm", [20, 21, 22])],
                                     None, True),
    ("tomato", "P2swap"): ([("O1_P2swap_LN+ES10+N4", [0, 1, 2])], None, False),
    ("tomato", "P1eq1"): ([("O1_P1eq1_LN", [0, 1, 2]), ("O1_P1eq1_LN_confirm", [20, 21, 22])], None, True),
    ("tomato_large", "P2swap"): ([("O1_P2swap_LE", [0, 1, 2]), ("O1_P2swap_LE_confirm", [20])], None, False),
    ("tomato_large", "P1eq1"): ([("O1_P1eq1_L", [0, 1, 2])], 6144, False),
}


def newest_br(run_dir, seed, max_ep=None):
    files = glob.glob(os.path.join(run_dir, "step4_br", f"seed{seed}_ep*.json"))
    eps = sorted((int(re.search(r"_ep(\d+)", f).group(1)), f) for f in files)
    eps = [e for e in eps if max_ep is None or e[0] <= max_ep]
    if not eps:
        return None
    with open(eps[-1][1]) as fh:
        d = json.load(fh)
    keep = ("received_by_k", "true_by_k", "window_by_k", "corrections_per_ep", "end_state")
    return {"episodes": eps[-1][0], "gap": d["gap"], "gap_se": d["gap_se"], "converged": d["gap"] <= 0.03,
            "policy": {k: d["policy"][k] for k in keep}, "best_response": {k: d["best_response"][k] for k in keep}}


def target(env, variant, seed):
    p = os.path.join(T4, env, "targets", variant, f"seed{seed}.json")
    if not os.path.exists(p):
        return None
    with open(p) as fh:
        d = json.load(fh)
    t = d["target"]
    return {"end_state": t["end_state"], "true_by_k": t["true_by_k"], "received_by_k": t["received_by_k"],
            "V0": t["V0"], "V_hide": d["V_hide"], "a1": d["a1"],
            "per_draw": [p["end_state"] for p in d.get("per_draw", [])]}


def finished(run_dir, seed, episodes):
    """Finished (at ``episodes``, for a run that has since been extended further): the best-response check
    runs only on finished seeds (step4_br.py --finished-only), so a check at that length marks it."""
    if episodes is None:
        return os.path.exists(os.path.join(run_dir, f"seed{seed}", "metrics.json"))
    return os.path.exists(os.path.join(run_dir, "step4_br", f"seed{seed}_ep{episodes}.json"))


def cell(env, variant, figures=True):
    runs, episodes, done = CELLS[(env, variant)]
    seeds, logs, cfg0 = [], [], None
    for run, ss in runs:
        rd = os.path.join(T4, env, "optimal", run)
        for s in ss:
            if not finished(rd, s, episodes):
                continue
            with open(os.path.join(rd, f"seed{s}", "config.json")) as fh:
                cfg = json.load(fh)
            if cfg0 is None:
                cfg0 = cfg
            assert cfg["n_envs"] == cfg0["n_envs"] and cfg["protocol"] == cfg0["protocol"], (run, s)
            rec = {"run": run, "seed": s, "br": newest_br(rd, s, episodes), "target": target(env, variant, s)}
            seeds.append(rec)
            if figures:
                logs.append(dict(np.load(os.path.join(rd, f"seed{s}", "logs.npz"))))
    out = {"env": env, "variant": variant, "done": done, "runs": [r for r, _ in runs], "seeds": seeds,
           "n_converged": sum(bool(r["br"] and r["br"]["converged"]) for r in seeds),
           "n_envs": cfg0["n_envs"] if cfg0 else None}
    if not figures or not logs:
        return out
    proto = Protocol(**cfg0["protocol"])
    K = proto.n_sub
    n_rounds = min(len(l["step_received"]) for l in logs)
    if episodes is not None:
        n_rounds = min(n_rounds, episodes * K)
    n_rounds -= n_rounds % K
    sp = np.mean([l["step_received"][:n_rounds] for l in logs], axis=0)
    st = np.mean([l["step_true"][:n_rounds] for l in logs], axis=0)
    caught = np.mean([l["caught"][:n_rounds].mean(axis=1) for l in logs], axis=0)
    n_ep = n_rounds // K
    a1 = next((r["target"]["a1"] for r in seeds if r["target"]), {})
    mid = 0.5 * (a1.get("honest_true", 0.0) + a1.get("proxy_opt_true", 0.0))
    after = np.convolve(st.sum(axis=1).reshape(n_ep, K)[:, 1:].mean(axis=1), np.ones(10) / 10, mode="valid")
    cross = int(np.argmax(after > mid)) + 5 if (after > mid).any() else n_ep // 2
    windows = [(0, 8, "start of training"),
               (min(max(8, cross - 3), n_ep - 16), 8, "learning to comply after the correction"),
               (n_ep - 8, 8, "end of training")]
    ceiling, avoid, _ = reference_lines(env)
    refs_lines = [(ceiling, f"max proxy return in a sub-episode ({ceiling:,.0f}): exploit throughout, ignore the monitor"),
                  (avoid, f"best monitor-avoiding return ({avoid:,.0f}): stop exploiting before the audit")]
    name = env.replace("_", " ")
    n = len(logs)
    who = "; ".join(f"{run} seeds {', '.join(str(r['seed']) for r in seeds if r['run'] == run)}"
                    for run in dict.fromkeys(r["run"] for r in seeds))
    fname = f"step4b_{env}_{variant}_timeline.png"
    out["figure"] = plot_timeline_split(
        proto, sp, st, caught, windows, fname,
        f"Step 4b, {name}, {VARIANT_NAME[variant]}: received vs true reward over training (mean of {n} seeds)",
        subtitle=f"{who}; {n_ep} episodes. Mean over the {n} seeds of each run's mean over its {cfg0['n_envs']} "
                 f"envs: the reward actually received (original proxy + the PBRR correction in force) and the true "
                 f"reward; y = reward so far in the current {proto.t_sub}-step sub-episode. Best-response check: "
                 f"{out['n_converged']} of {n} seeds within 3% of the best response to their own corrections. The "
                 "reward function and the preference data reset at every dashed episode boundary.",
        steps_per_tick=cfg0["n_envs"], refs=refs_lines, received_label="received reward (proxy + PBRR correction)",
        caught_label=f"fraction of envs caught, mean of {n} seeds")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cells", nargs="*", default=None, help="env:variant ... (default: all eight)")
    ap.add_argument("--no-figures", action="store_true")
    args = ap.parse_args()
    keys = [tuple(c.split(":")) for c in args.cells] if args.cells else list(CELLS)
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "overview.json")
    prev = {}
    if os.path.exists(path):
        with open(path) as fh:
            prev = {(c["env"], c["variant"]): c for c in json.load(fh)}
    for env, variant in keys:
        res = cell(env, variant, figures=not args.no_figures)
        if args.no_figures and (env, variant) in prev and "figure" in prev[(env, variant)]:
            res["figure"] = prev[(env, variant)]["figure"]
        prev[(env, variant)] = res
        print(f"{env} {variant}: {len(res['seeds'])} seeds, {res['n_converged']} converged"
              + (f" -> {os.path.relpath(res['figure'], ROOT)}" if res.get("figure") else ""), flush=True)
    with open(path, "w") as fh:
        json.dump([prev[k] for k in CELLS if k in prev], fh, indent=1, default=float)
    print(f"wrote {os.path.relpath(path, ROOT)}")


if __name__ == "__main__":
    main()
