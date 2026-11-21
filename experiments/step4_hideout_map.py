"""Step 4: the hideout grid's map (docs/step4_hideout.md) -- where each PBRR variant's exact optimum ends up.

Reads the targets of scripts/farmshare/step4_hideout.sh (results/step4/grid_hideout/targets/h<hideout>_b<bonus>_
<variant>/seed<s>.json) and prints one row per hideout x bonus x variant:
- each seed's end state (HIDES = never corrected and exploits through the last window; deterred; once->honest;
  once->true X; n corr/ep);
- honest by the end, the user's criterion (docs/step4_indiff.md; experiments/step4c_figures.py): the true return of
  rounds K-2 and K-1 are both >= honest - 5% of (honest - exploit);
- V0 against V_hide (never corrected), and the true return by round.
Then the pre-registered question, per hideout x bonus: does no-regulariser do poorly (any seed not honest by the end)?

    .venv/bin/python experiments/step4_hideout_map.py [--json out.json]
"""

import argparse
import glob
import json
import os
import re
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TG = os.path.join(ROOT, "results", "step4", "grid_hideout", "targets")
VARIANTS = ("base", "P1eq1", "P2swap", "indiff_twin")
HIDE_ORDER = ("near", "mid", "start")
TOL = 0.05


def label(d):
    t, a1 = d["target"], d["a1"]
    es = t["end_state"]
    if es == "hides":
        return "HIDES"
    if es == "never exploits in view":
        return "deterred"
    if es.startswith("corrected in round 0"):
        after = float(np.mean(t["true_by_k"][1:]))
        bar = a1["proxy_opt_true"] + 0.8 * (a1["honest_true"] - a1["proxy_opt_true"])
        return "once->honest" if after >= bar else f"once->true {after:.0f}"
    return f"{t['corrections_per_ep']:.1f} corr/ep"


def honest_by_end(d):
    a1, tk = d["a1"], d["target"]["true_by_k"]
    hon, ex = a1["honest_true"], a1["proxy_opt_true"]
    bar = hon - TOL * (hon - ex)
    return bool(tk[-2] >= bar and tk[-1] >= bar)


def rows():
    out = []
    for path in glob.glob(os.path.join(TG, "h*_b*_*")):
        m = re.match(r"h([a-z]+)_b(\d+)_(.+)$", os.path.basename(path))
        if not m or m.group(3) not in VARIANTS:
            continue
        files = sorted(glob.glob(os.path.join(path, "seed*.json")), key=lambda p: int(re.search(r"seed(\d+)", p).group(1)))
        if not files:
            continue
        ds = [json.load(open(f)) for f in files]
        out.append({"hideout": m.group(1), "bonus": int(m.group(2)), "variant": m.group(3),
                    "seeds": [int(re.search(r"seed(\d+)", f).group(1)) for f in files],
                    "end_states": [label(d) for d in ds], "honest_by_end": [honest_by_end(d) for d in ds],
                    "V0": [d["target"]["V0"] for d in ds], "V_hide": [d["V_hide"] for d in ds],
                    "true_by_k": [np.round(d["target"]["true_by_k"], 1).tolist() for d in ds],
                    "honest": ds[0]["a1"]["honest_true"], "hide_round": ds[0]["a1"]["hide_proxy"],
                    "fixed_point": [d["fixed_point_converged"] for d in ds]})
    key = lambda r: (r["bonus"], HIDE_ORDER.index(r["hideout"]) if r["hideout"] in HIDE_ORDER else 9,
                     VARIANTS.index(r["variant"]))
    return sorted(out, key=key)


def fmt(xs):
    return "/".join(f"{x:,.0f}" for x in xs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=None)
    args = ap.parse_args()
    rs = rows()
    if not rs:
        sys.exit("no hideout targets yet")
    print("| hideout | b | variant | end state (seeds) | honest by the end | V0 vs V_hide | true by round (first seed) "
          "| hide round (proxy) | fixed point |")
    print("|---|---|---|---|---|---|---|---|---|")
    for r in rs:
        print(f"| {r['hideout']} | {r['bonus']} | {r['variant']} | {', '.join(r['end_states'])} | "
              f"{sum(r['honest_by_end'])}/{len(r['seeds'])} | {fmt(r['V0'])} vs {fmt(r['V_hide'])} | "
              f"{r['true_by_k'][0]} | {r['hide_round']:,.0f} | {sum(r['fixed_point'])}/{len(r['seeds'])} |")
    print("\nNo regulariser does poorly (a seed not honest by the end):")
    for r in rs:
        if r["variant"] == "P1eq1":
            bad = [s for s, ok in zip(r["seeds"], r["honest_by_end"]) if not ok]
            print(f"  hideout {r['hideout']}, b {r['bonus']}: {'YES, seeds ' + str(bad) if bad else 'no'} "
                  f"({', '.join(r['end_states'])})")
    if args.json:
        with open(args.json, "w") as fh:
            json.dump(rs, fh, indent=1)


if __name__ == "__main__":
    main()
