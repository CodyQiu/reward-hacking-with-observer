"""Step 3: probe a trained policy in every (sub-episode k, correction count) cell, including
cells training never visits.

The trained PPO policy is run for one sub-episode from a fresh start at clock offset
t0 = k * t_sub with the observed correction count fixed at n, under the *uncorrected*
proxy (no g installed: this asks what the policy would do there, not what it would
receive). Reported per cell, from n_roll Monte Carlo rollouts on a separate RNG stream:

    window   P(any exploit step in the audit window)
    off      exploit-step rate before the window
    proxy    proxy return of the sub-episode

    .venv/bin/python experiments/step3_probe.py --env tomato --run-id T3_final --seeds 10 11 12

Written to results/step3/<env>/probes/<run_id>_seed<s>.json (run directories are never touched).
"""

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sbx import PPO

from src.step3.pbrr import policy_probs_fn, rollouts
from src.step3.protocol import Protocol
from src.step3.task import exploit_mask
from src.step3.tasks import get_task
from src.step3.train import RESULTS


def probe(env, run_id, seed, n_roll=256, max_corr=1):
    run_dir = os.path.join(RESULTS, env, "tuning", run_id, f"seed{seed}")
    with open(os.path.join(run_dir, "config.json")) as fh:
        cfg = json.load(fh)
    task = get_task(cfg["env"], **cfg["task"])
    proto = Protocol(**cfg["protocol"])
    model = PPO.load(os.path.join(run_dir, "model.zip"))
    fn = policy_probs_fn(model, proto, task.n_actions)
    T, W = proto.t_sub, proto.window
    cells = []
    for k in range(proto.n_sub):
        for n in range(max_corr + 1):
            rng = np.random.default_rng(10_000 + 97 * k + n)          # evaluation stream only
            rs = rollouts(task.make_batch(n_roll, seed=20_000 + 97 * k + n), fn, proto, rng, t0=k * T, n_corr=n)
            ex = np.stack([exploit_mask(r.proxy_steps, r.true_steps) for r in rs])
            cells.append({"k": k, "n_corr": n, "window": float(ex[:, T - W:].any(axis=1).mean()),
                          "off": float(ex[:, :T - W].mean()),
                          "proxy": float(np.mean([r.proxy_steps.sum() for r in rs]))})
    return {"env": env, "run_id": run_id, "seed": seed, "n_roll": n_roll, "cells": cells}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--seeds", nargs="+", type=int, required=True)
    ap.add_argument("--n-roll", type=int, default=256)
    ap.add_argument("--max-corr", type=int, default=1)
    args = ap.parse_args()
    out_dir = os.path.join(RESULTS, args.env, "probes")
    os.makedirs(out_dir, exist_ok=True)
    for s in args.seeds:
        res = probe(args.env, args.run_id, s, args.n_roll, args.max_corr)
        with open(os.path.join(out_dir, f"{args.run_id}_seed{s}.json"), "w") as fh:
            json.dump(res, fh, indent=1)
        print(f"== {args.env} {args.run_id} seed {s}   (window = P(exploit in window), off = exploit-step rate "
              f"before it, proxy = return; uncorrected proxy, {args.n_roll} rollouts)")
        for c in res["cells"]:
            print(f"   k={c['k']} corrections={c['n_corr']}   window {c['window']:.2f}   off {c['off']:.2f}   "
                  f"proxy {c['proxy']:8.1f}")


if __name__ == "__main__":
    main()
