"""Print a run's --set overrides (overrides.json) as k=v words, with the episode count and annealing its
seeds actually ended with (a tuned run may have been extended): the config a confirmation run repeats.
    .venv/bin/python scripts/farmshare/run_sets.py results/step4/<env>/optimal/<run_id>
"""
import glob
import json
import os
import sys

run = sys.argv[1]
with open(os.path.join(run, "overrides.json")) as fh:
    ov = json.load(fh)
cfgs = []
for p in glob.glob(os.path.join(run, "seed*", "config.json")):
    with open(p) as fh:
        cfgs.append(json.load(fh))
if cfgs:
    ov["episodes"] = max(c["episodes"] for c in cfgs)
    ov["anneal"] = cfgs[0].get("anneal", ov.get("anneal"))
words = []
for g, v in ov.items():
    for k, x in (v.items() if isinstance(v, dict) else [(None, v)]):
        x = json.dumps(x, separators=(",", ":")) if isinstance(x, (list, dict)) else x
        words.append(f"{g}.{k}={x}" if k else f"{g}={x}")
print(" ".join(words))
