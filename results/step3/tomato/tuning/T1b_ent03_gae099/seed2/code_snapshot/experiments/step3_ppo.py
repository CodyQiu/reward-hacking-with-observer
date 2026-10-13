"""Step 3: train / tune SBX PPO against the PBRR overseer on one task of the suite.

Every invocation is one tuning *run*: an env, a run id, a configuration (defaults
= Step 1's PPO config + the env's Phase A, plus --set overrides) and one or more
seeds, each trained in its own process into
results/step3/<env>/tuning/<run_id>/seed<s>/ (never overwritten). When all seeds
finish, one row is appended to results/step3/<env>/tuning/runs.csv with the
configuration, the hypothesis being tested and S1-S5 per seed.

    .venv/bin/python experiments/step3_ppo.py --env taxi --run-id T0_step1_config --seeds 0 1 2 \
        --hypothesis "Step 1's PPO config works unchanged"
    .venv/bin/python experiments/step3_ppo.py --env taxi --run-id T1_ent02 --seeds 0 \
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

from src.step3.metrics import CRITERIA, failure_label
from src.step3.train import RESULTS, resolve_config, train_run


def parse_sets(items):
    """['ppo.ent_coef=0.02', 'episodes=192'] -> nested override dict."""
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--seeds", nargs="+", type=int, default=[0])
    ap.add_argument("--set", nargs="*", default=[])
    ap.add_argument("--hypothesis", default="")
    ap.add_argument("--worker-seed", type=int, default=None, help=argparse.SUPPRESS)
    args = ap.parse_args()
    overrides = parse_sets(args.set)
    tuning = os.path.join(RESULTS, args.env, "tuning")
    run_root = os.path.join(tuning, args.run_id)

    if args.worker_seed is not None:                       # one seed, in this process
        cfg = resolve_config(args.env, {**overrides, "seed": args.worker_seed})
        train_run(os.path.join(run_root, f"seed{args.worker_seed}"), cfg)
        return

    if os.path.exists(run_root):
        sys.exit(f"{run_root} exists: pick a new --run-id (results are never overwritten)")
    os.makedirs(run_root)
    t0 = time.time()
    # one core per seed: no XLA / BLAS thread pools fighting over the machine
    env = {**os.environ, "XLA_FLAGS": "--xla_cpu_multi_thread_eigen=false intra_op_parallelism_threads=1",
           "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "VECLIB_MAXIMUM_THREADS": "1",
           "MKL_NUM_THREADS": "1"}
    procs = []
    for s in args.seeds:
        log = open(os.path.join(run_root, f"seed{s}.log"), "w")
        cmd = [sys.executable, os.path.abspath(__file__), "--env", args.env, "--run-id", args.run_id,
               "--worker-seed", str(s), "--set", *args.set]
        procs.append((s, subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, env=env), log))
    for s, p, log in procs:
        p.wait()
        log.close()
        print(f"  seed {s} exit {p.returncode}")

    cfg = resolve_config(args.env, overrides)
    per_seed = {}
    for s in args.seeds:
        path = os.path.join(run_root, f"seed{s}", "metrics.json")
        if os.path.exists(path):
            with open(path) as fh:
                per_seed[s] = json.load(fh)
    git = ""
    if per_seed:
        with open(os.path.join(run_root, f"seed{next(iter(per_seed))}", "config.json")) as fh:
            git = json.load(fh)["git"]
    row = {"run_id": args.run_id, "finished": time.strftime("%Y-%m-%d %H:%M"), "git": git,
           "seeds": " ".join(map(str, args.seeds)), "episodes": cfg["episodes"],
           "overrides": json.dumps(overrides, sort_keys=True), "hypothesis": args.hypothesis,
           "wall_min": round((time.time() - t0) / 60, 1),
           "n_hide": sum(m["final"]["hides"] for m in per_seed.values())}
    summaries = []
    for s, m in per_seed.items():
        f = m["final"]
        summaries.append(f"s{s}: win {f['window_0_3']:.3f} off {f['offwindow_rel']:.2f} corr "
                         f"{f['corrections_per_ep']:.2f} winF {f['window_final']:.2f} proxy "
                         f"{f['proxy_0_3']:.1f} | " + " ".join(f"{c}={'Y' if f[c] else 'n'}" for c in CRITERIA)
                         + f" | {failure_label(f, m['checkpoints'])}")
    row["per_seed"] = " ;; ".join(summaries)
    fields = ["run_id", "finished", "git", "seeds", "episodes", "overrides", "hypothesis", "wall_min",
              "n_hide", "per_seed"]
    runs_csv = os.path.join(tuning, "runs.csv")
    exists = os.path.exists(runs_csv)
    with open(runs_csv, "a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        if not exists:
            w.writeheader()
        w.writerow(row)
    print(json.dumps(row, indent=1))


if __name__ == "__main__":
    main()
