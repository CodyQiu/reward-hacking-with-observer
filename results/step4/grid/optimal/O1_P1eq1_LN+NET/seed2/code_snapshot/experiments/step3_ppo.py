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

Resume / extend (same run directory; see src/step3/train.py): ``--resume`` continues every listed
seed that has no metrics.json from its last checkpoint; ``--resume --extend-to N`` also takes
finished seeds on to N episodes in total. ``--set`` may then change only ``anneal.*``. A seed that
died before its first checkpoint (no model.zip) is moved aside to seed<s>_nockpt_<time> and
restarted from scratch.
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


def _run_overrides(run_root):
    """The --set overrides a run was started with (overrides.json, written by the launcher), for a
    seed that has to restart from scratch inside an existing run."""
    path = os.path.join(run_root, "overrides.json")
    if os.path.exists(path):
        with open(path) as fh:
            return json.load(fh)
    raise SystemExit(f"{run_root}: no overrides.json (runs started before 2026-11-04): restart that seed by hand")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--seeds", nargs="+", type=int, default=[0])
    ap.add_argument("--set", nargs="*", default=[])
    ap.add_argument("--hypothesis", default="")
    ap.add_argument("--results-dir", default=None,
                    help="parent of the run directory and runs.csv (default results/step3/<env>/tuning; "
                         "Step 4: results/step4/<env>/ppo)")
    ap.add_argument("--resume", action="store_true", help="continue an existing run from its checkpoints")
    ap.add_argument("--extend-to", type=int, default=None, help="with --resume: total episodes per seed")
    ap.add_argument("--worker-seed", type=int, default=None, help=argparse.SUPPRESS)
    args = ap.parse_args()
    overrides = parse_sets(args.set)
    tuning = args.results_dir or os.path.join(RESULTS, args.env, "tuning")
    run_root = os.path.join(tuning, args.run_id)
    if args.resume and set(overrides) - {"anneal"}:
        sys.exit("--resume: --set may change only anneal.* (the rest of the config is the run's own)")

    if args.worker_seed is not None:                       # one seed, in this process
        sdir = os.path.join(run_root, f"seed{args.worker_seed}")
        if args.resume and os.path.exists(os.path.join(sdir, "model.zip")):
            with open(os.path.join(sdir, "config.json")) as fh:
                cfg = json.load(fh)
            cfg["episodes"] = args.extend_to or cfg["episodes"]
            cfg["anneal"] = {**cfg.get("anneal", {"last": 0.0, "floor": 1.0}), **overrides.get("anneal", {})}
            train_run(sdir, cfg, resume=True)
        else:
            if args.resume and os.path.exists(sdir):        # died before its first checkpoint: keep it aside
                os.replace(sdir, f"{sdir}_nockpt_{time.strftime('%Y%m%d-%H%M%S')}")
            base = {}
            if args.resume:                                 # the run's own overrides, from a sibling seed
                base = _run_overrides(run_root)
            cfg = resolve_config(args.env, {**base, **overrides, "seed": args.worker_seed,
                                            **({"episodes": args.extend_to} if args.extend_to else {})})
            train_run(sdir, cfg)
        return

    if args.resume:
        if not os.path.isdir(run_root):
            sys.exit(f"{run_root} does not exist: nothing to resume")
        todo = []
        for s in args.seeds:
            m = os.path.join(run_root, f"seed{s}", "metrics.json")
            done = os.path.exists(m)
            if done and args.extend_to:
                with open(os.path.join(run_root, f"seed{s}", "progress.json")) as fh:
                    done = json.load(fh)["episodes"] >= args.extend_to
            if not done:
                todo.append(s)
        if not todo:
            sys.exit(f"{run_root}: every listed seed is finished" + (f" at >= {args.extend_to} episodes"
                                                                       if args.extend_to else ""))
        args.seeds = todo
    elif os.path.exists(run_root):
        sys.exit(f"{run_root} exists: pick a new --run-id (results are never overwritten)")
    else:
        os.makedirs(run_root)
        with open(os.path.join(run_root, "overrides.json"), "w") as fh:
            json.dump(overrides, fh, indent=1)
    t0 = time.time()
    # one core per seed: no XLA / BLAS thread pools fighting over the machine. JAX sizes its own pools
    # from the CPU affinity mask, so inside a Slurm cgroup a worker has ~12 threads (257 on a bare node).
    env = {**os.environ, "XLA_FLAGS": "--xla_cpu_multi_thread_eigen=false",
           "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "VECLIB_MAXIMUM_THREADS": "1",
           "MKL_NUM_THREADS": "1"}
    procs = []
    for s in args.seeds:
        log = open(os.path.join(run_root, f"seed{s}.log"), "a" if args.resume else "w")
        cmd = [sys.executable, os.path.abspath(__file__), "--env", args.env, "--run-id", args.run_id,
               "--worker-seed", str(s), "--results-dir", tuning, "--set", *args.set]
        if args.resume:
            cmd += ["--resume"] + (["--extend-to", str(args.extend_to)] if args.extend_to else [])
        procs.append((s, subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, env=env), log))
    for s, p, log in procs:
        p.wait()
        log.close()
        print(f"  seed {s} exit {p.returncode}")

    cfg = resolve_config(args.env, _run_overrides(run_root) if args.resume else overrides)
    if args.resume and args.extend_to:
        cfg["episodes"] = args.extend_to
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
    row = {"run_id": args.run_id + (" (resumed)" if args.resume else ""), "finished": time.strftime("%Y-%m-%d %H:%M"),
           "git": git,
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
