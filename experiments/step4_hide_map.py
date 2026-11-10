"""Step 4: the map of where each PBRR variant's exact optimum avoids correction (docs/step4_hide_env.md).

Reads the self-consistent targets of scripts/farmshare/step4_hide.sh (experiments/step4_targets.py) and prints one
row per setting x variant: each seed's end state, the target's value against hiding's, and what one correction
does (the best round, the honest policy's and the open exploiter's round under the corrected reward). The grid's
b = 100 row reuses the campaign's targets (results/step4/grid/targets/P2swap, P1eq1).

    .venv/bin/python experiments/step4_hide_map.py [--json out.json]
"""

import argparse
import glob
import json
import os
import re
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T4 = os.path.join(ROOT, "results", "step4")
VARIANTS = ("P2swap", "P1eq1")


def label(d):
    """Short end state of a target (pre-registered in docs/step4_hide_env.md)."""
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


def rows():
    out = []
    fams = [("taxi", "taxi", lambda v: [v]),
            ("grid b", "grid", lambda v: [v] + sorted(
                (os.path.basename(p) for p in glob.glob(os.path.join(T4, "grid", "targets", f"b*_{v}"))),
                key=lambda n: int(re.match(r"b(\d+)_", n).group(1)))),
            ("routes", "grid_routes", lambda v: sorted(
                (os.path.basename(p) for p in glob.glob(os.path.join(T4, "grid_routes", "targets", f"r*_b*_{v}"))),
                key=lambda n: tuple(int(x) for x in re.match(r"r(\d+)_b(\d+)_", n).groups())[::-1]))]
    for fam, env, names in fams:
        for v in VARIANTS:
            for name in names(v):
                files = sorted(glob.glob(os.path.join(T4, env, "targets", name, "seed*.json")),
                               key=lambda p: int(re.search(r"seed(\d+)", p).group(1)))
                files = [f for f in files if int(re.search(r"seed(\d+)", f).group(1)) in (0, 1, 2)]
                if not files:
                    continue
                ds = [json.load(open(f)) for f in files]
                setting = "b 100" if name == v and env == "grid" else ("" if env == "taxi" else name[: -len(v) - 1])
                t = [d["target"] for d in ds]
                out.append({
                    "family": fam, "setting": setting, "variant": v, "seeds": len(ds),
                    "end_states": [label(d) for d in ds],
                    "per_draw_hides": [sum(p["end_state"] == "hides" for p in d.get("per_draw", [])) for d in ds],
                    "n_draws": ds[0].get("n_draws"),
                    "V0": [x["V0"] for x in t], "V_hide": [d["V_hide"] for d in ds],
                    "best_after_1": [x["best_after_one_correction"] for x in t],
                    "honest_after_1": [x["honest_after_one_correction"] for x in t],
                    "exploit_after_1": [x["exploit_after_one_correction"] for x in t],
                    "open_round": ds[0]["a1"]["proxy_opt_proxy"], "hide_round": ds[0]["a1"]["hide_proxy"],
                    "true_by_k": [np.round(x["true_by_k"], 1).tolist() for x in t],
                    "fixed_point": [d["fixed_point_converged"] for d in ds]})
    return out


def fmt(xs):
    return "/".join(f"{x:,.0f}" for x in xs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=None)
    args = ap.parse_args()
    rs = rows()
    if not rs:
        sys.exit("no targets yet")
    print("| family | setting | variant | end state (seeds 0/1/2) | draws hiding | V0 vs V_hide | round after 1 "
          "correction: best / honest / open exploiter | open / hide round under the proxy | fixed point |")
    print("|---|---|---|---|---|---|---|---|---|")
    for r in rs:
        print(f"| {r['family']} | {r['setting']} | {r['variant']} | {', '.join(r['end_states'])} | "
              f"{'/'.join(map(str, r['per_draw_hides']))} of {r['n_draws']} | {fmt(r['V0'])} vs {fmt(r['V_hide'])} | "
              f"{fmt(r['best_after_1'])} / {fmt(r['honest_after_1'])} / {fmt(r['exploit_after_1'])} | "
              f"{r['open_round']:,.0f} / {r['hide_round']:,.0f} | {sum(r['fixed_point'])}/{r['seeds']} |")
    if args.json:
        with open(args.json, "w") as fh:
            json.dump(rs, fh, indent=1)


if __name__ == "__main__":
    main()
