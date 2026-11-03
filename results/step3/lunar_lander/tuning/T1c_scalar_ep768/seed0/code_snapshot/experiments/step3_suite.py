"""Step 3 suite figure: every environment's final runs side by side, plus Step 2's grid.

    .venv/bin/python experiments/step3_suite.py --runs absent_supervisor:T3_final:10,11,12 taxi:T3_final:10,11,12 ...

Each row: the fraction of audit windows 0-3 exploited, the off-window exploit rate
(relative to the env's idealised optimum), the final window exploited, and PBRR
rounds per episode, over training (logged data, seed mean and each seed). Step 2's
grid comes from results/step2/tuning/T3_final_seeds10-12 (same exploit semantics:
proxy != true exactly on arrival at the exploit tile).
"""

import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from experiments.step3_figures import load, per_episode, reference_lines
from src.plots_step3 import plot_suite
from src.report import CheckLog
from src.step3.protocol import Protocol
from src.step3.tasks.grid import PROTOCOL as GRID_PROTOCOL
from src.step3.tasks.grid import refs as grid_refs
from src.step3.train import ROOT

LABELS = {"grid": "grid (Step 2)", "tomato": "Tomato Watering", "taxi": "Taxi", "absent_supervisor": "Absent Supervisor",
          "mountain_car": "MountainCar", "lunar_lander": "LunarLander"}


def step2_runs(run_id="T3_final_seeds10-12", seeds=(10, 11, 12)):
    refs = grid_refs()
    out = []
    for s in seeds:
        d = os.path.join(ROOT, "results", "step2", "tuning", run_id, f"seed{s}")
        logs = dict(np.load(os.path.join(d, "logs.npz")))
        out.append(per_episode(logs, [], GRID_PROTOCOL, refs, 16))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", required=True, help="env:run_id:seed,seed,...")
    ap.add_argument("--no-step2", action="store_true")
    args = ap.parse_args()
    log = CheckLog("Step 3 suite figure")
    rows = [] if args.no_step2 else [(LABELS["grid"], step2_runs())]
    for spec in args.runs:
        env, run_id, seeds = spec.split(":")
        loaded = [load(env, run_id, int(s)) for s in seeds.split(",")]
        proto = Protocol(**loaded[0][2]["protocol"])
        _, _, refs = reference_lines(env)
        rows.append((LABELS.get(env, env), [per_episode(l, r, proto, refs, int(c["n_envs"])) for l, r, c in loaded]))
    log.figure(plot_suite(
        rows, "step3_suite.png", "Step 3: does the agent learn to exploit off-window and keep the audits clean?",
        subtitle="Each row: one environment, final configuration, 3 fresh seeds (light) and their mean (dark); logged "
                 "training data. Exploit step = proxy != true. Off-window exploitation is relative to the environment's "
                 "idealised optimum. The Step 2 story: audit windows 0-3 go clean, off-window exploitation and "
                 "final-window exploitation stay high, PBRR rounds fall to ~0."))
    log.summary()


if __name__ == "__main__":
    main()
