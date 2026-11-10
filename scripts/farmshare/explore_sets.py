"""The exploration wave's configs on top of one base run (docs/step4_optimal.md, rule 6b), one line each:
"<factor tag><TAB><--set words>". Each is the base run's own overrides (run_sets.py) with its episode count
reset to the wave length, plus the factor; the factor's values are read from the base's resolved config.

    .venv/bin/python scripts/farmshare/explore_sets.py results/step4/<env>/optimal/<run_id> <episodes> [stage2]

Stage 1: ENT3 (entropy 3x), ES10 (entropy starts at 10x and falls to 1x by episode 768), N4 (4x the envs
and the batch, same 4 minibatches; at most 256 envs), ES10+N4. Stage 2, for the best stage-1 run if stage 1
plateaus: ENT10, ES30 (30x, falling to 1x by episode 1536), ES30+N4.
"""
import glob
import json
import os
import subprocess
import sys

MAX_ENVS = 256

run, episodes = sys.argv[1], int(sys.argv[2])
stage2 = len(sys.argv) > 3 and sys.argv[3] == "stage2"
here = os.path.dirname(os.path.abspath(__file__))
words = subprocess.check_output([sys.executable, os.path.join(here, "run_sets.py"), run], text=True).split()
words = [w for w in words if not w.startswith("episodes=")] + [f"episodes={episodes}"]
cfg_paths = sorted(glob.glob(os.path.join(run, "seed*", "config.json")))
if not cfg_paths:
    sys.exit(f"{run}: no seed config.json")
with open(cfg_paths[0]) as fh:
    cfg = json.load(fh)
ent, n, batch = float(cfg["ppo"]["ent_coef"]), int(cfg["n_envs"]), int(cfg["ppo"]["batch_size"])
n4 = min(4 * n, MAX_ENVS)
N4 = [f"n_envs={n4}", f"ppo.batch_size={batch * n4 // n}"] if n4 > n else None


def es(start, until):
    return [f"anneal.ent_start={start}", f"anneal.ent_episodes={until}"]


factors = ({"ENT10": [f"ppo.ent_coef={10 * ent:g}"], "ES30": es(30, 1536),
            "ES30+N4": es(30, 1536) + N4 if N4 else None} if stage2 else
           {"ENT3": [f"ppo.ent_coef={3 * ent:g}"], "ES10": es(10, 768), "N4": N4,
            "ES10+N4": es(10, 768) + N4 if N4 else None})
for tag, extra in factors.items():
    if extra is not None:                      # an N4 factor is skipped when the base already has MAX_ENVS
        merged = dict(w.split("=", 1) for w in words + extra)     # the factor's value replaces the base's
        print(f"{tag}\t{' '.join(f'{k}={v}' for k, v in merged.items())}")
