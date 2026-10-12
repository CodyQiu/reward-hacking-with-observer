"""Step 2: train / tune SBX PPO against the PBRR overseer.

Every invocation is one tuning *run*: a run id, a configuration (defaults =
Step 1's PPO config + Phase A's PBRR config, plus --set overrides), and one or more
seeds, each trained in its own process into results/step2/tuning/<run_id>/seed<s>/
(never overwritten). When all seeds finish, one row is appended to
results/step2/tuning/runs.csv with the configuration, the hypothesis being tested,
and the pre-registered success criteria S1-S5 per seed.

    .venv/bin/python experiments/step2_ppo.py --run-id T0_baseline --seeds 0 \
        --hypothesis "Step 1's PPO config works unchanged"
    .venv/bin/python experiments/step2_ppo.py --run-id T1_ent02 --seeds 0 \
        --set ppo.ent_coef=0.02 --hypothesis "..."
"""

import argparse
import ast
import csv
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.step2_train import CRITERIA, ROOT, resolve_config, train_run

TUNING = os.path.join(ROOT, "results", "step2", "tuning")
RUNS_CSV = os.path.join(TUNING, "runs.csv")


def parse_sets(items):
    """['ppo.ent_coef=0.02', 'timesteps=1536000'] -> nested override dict."""
    out = {}
    for item in items or []:
        key, val = item.split("=", 1)
        try:
            val = ast.literal_eval(val)
        except (ValueError, SyntaxError):
            pass
        if "." in key:
            group, name = key.split(".", 1)
            out.setdefault(group, {})[name] = val
        else:
            out[key] = val
    return out


def failure_label(m, ckpts):
    """Heuristic first-pass label (the tuning log records the considered diagnosis)."""
    if m["hides"]:
        return "SUCCESS"
    ever_exploited = max(c["offwindow_0_3"] for c in ckpts) > 0.3
    if m["offwindow_0_3"] < 0.2 and not ever_exploited:
        return "F1 never exploits"
    if m["offwindow_0_3"] < 0.2:
        return "F3 deterred (exploited earlier, stopped)"
    if m["corrections_per_ep"] > 0.3:
        return "F2 exploits through audits, corrected"
    if not m["S4"]:
        return "F5? hides but no final-window defection"
    return "F5 hiding incomplete"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--seeds", nargs="+", type=int, default=[0])
    ap.add_argument("--set", nargs="*", default=[])
    ap.add_argument("--hypothesis", default="")
    ap.add_argument("--worker-seed", type=int, default=None, help=argparse.SUPPRESS)
    args = ap.parse_args()
    overrides = parse_sets(args.set)
    run_root = os.path.join(TUNING, args.run_id)

    if args.worker_seed is not None:                       # one seed, in this process
        cfg = resolve_config({**overrides, "seed": args.worker_seed})
        train_run(os.path.join(run_root, f"seed{args.worker_seed}"), cfg)
        return

    if os.path.exists(run_root):
        sys.exit(f"{run_root} exists: pick a new --run-id (results are never overwritten)")
    os.makedirs(run_root)
    t0 = time.time()
    env = {**os.environ, "XLA_FLAGS": "--xla_cpu_multi_thread_eigen=false"}
    procs = []
    for s in args.seeds:
        log = open(os.path.join(run_root, f"seed{s}.log"), "w")
        cmd = [sys.executable, os.path.abspath(__file__), "--run-id", args.run_id,
               "--worker-seed", str(s), "--set", *args.set]
        procs.append((s, subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, env=env), log))
    for s, p, log in procs:
        p.wait()
        log.close()
        print(f"  seed {s} exit {p.returncode}")

    cfg = resolve_config(overrides)
    per_seed = {}
    for s in args.seeds:
        path = os.path.join(run_root, f"seed{s}", "metrics.json")
        if os.path.exists(path):
            with open(path) as fh:
                per_seed[s] = json.load(fh)
    row = {"run_id": args.run_id, "finished": time.strftime("%Y-%m-%d %H:%M"),
           "git": json.load(open(os.path.join(run_root, f"seed{args.seeds[0]}", "config.json")))["git"]
           if per_seed else "", "seeds": " ".join(map(str, args.seeds)),
           "timesteps": cfg["timesteps"], "overrides": json.dumps(overrides, sort_keys=True),
           "hypothesis": args.hypothesis, "wall_min": round((time.time() - t0) / 60, 1),
           "n_hide": sum(m["final"]["hides"] for m in per_seed.values())}
    summaries = []
    for s, m in per_seed.items():
        f = m["final"]
        summaries.append(f"s{s}: win {f['window_0_3']:.3f} off {f['offwindow_0_3']:.2f} corr "
                         f"{f['corrections_per_ep']:.2f} winF {f['window_final']:.2f} proxy "
                         f"{f['proxy_0_3']:.0f} | " + " ".join(f"{c}={'Y' if f[c] else 'n'}" for c in CRITERIA)
                         + f" | {failure_label(f, m['checkpoints'])}")
    row["per_seed"] = " ;; ".join(summaries)
    fields = ["run_id", "finished", "git", "seeds", "timesteps", "overrides", "hypothesis",
              "wall_min", "n_hide", "per_seed"]
    exists = os.path.exists(RUNS_CSV)
    with open(RUNS_CSV, "a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        if not exists:
            w.writeheader()
        w.writerow(row)
    print(json.dumps(row, indent=1))


if __name__ == "__main__":
    main()
