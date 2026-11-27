"""Step 4 goal fixes, diagnosis (docs/step4_goal_fixes.md). Taxi and Boat Race (goal tasks).

Replays the exact targets' first iteration (experiments/step4_targets.py, iteration 0): correction c is fitted on
the best policy at level c-1 that is caught (dp.solve_subepisode_caught on the mean table of level c-1), with the
same random streams ([seed, d, c, 4]) and the run's own reference rollouts. For every level and draw it decodes the
correction g by transition type and by where the row was seen (the caught rollouts, the reference rollouts, or
nowhere); and for every level it reports the best round under the mean table and under each draw (true return,
received, exploit steps, which exploit copy it uses, whether it meets the goal or ends hidden) against honest play.

    .venv/bin/python experiments/step4_goal_diag.py --env boat_race_goal --variants base P1eq1 P2swap --seeds 0 \
        [--set task.g_index=True] [--ref-seed 1] [--levels 4] --tag main

Writes results/step4/<env>/goal_fixes/diag_<tag>_seed<s>.json (refuses to overwrite).
"""
import argparse
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from step3_ppo import parse_sets  # noqa: E402
from step4_targets import OUT, sub_value, round_window  # noqa: E402
from src.pbrr_core import GConfig, boltzmann_label  # noqa: E402
from src.step3.dp import solve_subepisode, solve_subepisode_caught, table_policy_fn  # noqa: E402
from src.step3.goal import goal_rate  # noqa: E402
from src.step3.pbrr import fit_correction_rows, g_table, rollouts, unseen_override  # noqa: E402
from src.step3.protocol import Protocol  # noqa: E402
from src.step3.reference import build_reference  # noqa: E402
from src.step3.tasks import get_task  # noqa: E402
from src.step3.train import resolve_config  # noqa: E402

VARIANTS = {"base": {}, "P1eq1": {"use_regularization": False}, "P2swap": {"l_minus_on": "dispreferred"}}


# ----------------------------------------------------------------------------- transition types (base task rows)

def types_boat(base):
    """(S_base*A,) type label per base row and the exploit copy (checkpoint index) of step-back rows."""
    ring, cps, side = base.ring, base.checkpoints, base.side
    cell = {rc: i for i, rc in enumerate(ring)}
    L, A, C = len(cps), 4, len(ring)
    D = ((-1, 0), (1, 0), (0, -1), (0, 1))
    lab, copy = [], []
    for i, (r, c) in enumerate(ring):
        for j in range(L):
            for a, (dr, dc) in enumerate(D):
                rc2 = (r + dr, c + dc)
                if rc2 not in cell:
                    lab.append("wall bump"), copy.append(-1)
                    continue
                i2 = cell[rc2]
                if rc2 in cps and cps[rc2][1] == a:
                    lab.append("checkpoint entry (aliased)"), copy.append(cps[rc2][0])
                elif (r, c) in cps and i2 == (i - 1) % C:
                    lab.append("step back off a checkpoint (exploit-only)"), copy.append(cps[(r, c)][0])
                elif i2 == (i + 1) % C:
                    lab.append("ordinary clockwise move"), copy.append(-1)
                else:
                    lab.append("ordinary counter-clockwise move"), copy.append(-1)
    return np.array(lab), np.array(copy), {0: "top", 1: "right", 2: "bottom (hidden)", 3: "left"}


def types_taxi(base):
    from src.step3.tasks.taxi import LOCS, decode_native
    S, A = base.tables.n_states, base.tables.n_actions
    lab, copy = [], []
    for s in range(S):
        row, col, pidx, didx = decode_native(s // 2)
        at = [k for k, rc in enumerate(LOCS) if rc == (row, col)]
        for a in range(A):
            ns = int(base.tables.nxt[s * A + a, 0]) // 2
            if a < 4:
                lab.append("wall bump" if ns == s // 2 else "ordinary move"), copy.append(-1)
            elif a == 4:
                ok = pidx < 4 and at and at[0] == pidx
                lab.append("legal pickup (aliased)" if ok else "illegal pickup"), copy.append(at[0] if ok else -1)
            else:
                if pidx == 4 and at and at[0] == didx:
                    lab.append("delivery"), copy.append(-1)
                elif pidx == 4 and at:
                    lab.append("dropoff in place, not the destination (exploit-only)"), copy.append(at[0] * 4 + didx)
                else:
                    lab.append("illegal dropoff"), copy.append(-1)
    names = {k * 4 + d: f"depot {'RGYB'[k]}{' (hidden)' if k == 3 else ''} -> {'RGYB'[d]}" for k in range(4)
             for d in range(4)}
    names.update({k: f"depot {'RGYB'[k]}" for k in range(4)})
    return np.array(lab), np.array(copy), names


# ----------------------------------------------------------------------------- helpers

def base_rows_of_keys(task, keys):
    """Augmented transition keys -> base rows (s_base * A + a)."""
    s, a, _ = task.decode(np.asarray(keys))
    return (np.asarray(s) // task.n_counter) * task.n_actions + np.asarray(a)


def occupancy(tb, pol, T):
    """Expected visits of every augmented row (S*A,) over one round from mu0."""
    d, occ = tb.mu0.copy(), np.zeros(tb.n_states * tb.n_actions)
    for tau in range(T):
        r = np.arange(tb.n_states) * tb.n_actions + pol[tau]
        occ[r] += d
        m = d[:, None] * tb.prob[r]
        d = np.bincount(tb.nxt[r].ravel(), weights=m.ravel(), minlength=tb.n_states)
    return occ


def round_report(task, tb, R, T, W, labels, copies, names, pol_gt):
    pol = solve_subepisode(tb, R, T)
    occ = occupancy(tb, pol, T)
    A = tb.n_actions
    brow = (np.arange(tb.n_states * A) // A // task.n_counter) * A + np.arange(tb.n_states * A) % A
    ex = labels[brow].astype(str)
    expl = np.char.find(ex, "exploit-only") >= 0
    by_copy = {}
    for cp in np.unique(copies[brow][expl]):
        v = float(occ[expl & (copies[brow] == cp)].sum())
        if v > 0.05:
            by_copy[names.get(int(cp), str(cp))] = round(v, 2)
    gr = goal_rate(task, pol, T)
    return {"received": sub_value(tb, pol, R, T), "true": sub_value(tb, pol, tb.true, T),
            "exploit_steps": float(occ[expl].sum()), "exploit_copies": by_copy,
            "goal_rate": gr["goal"], "hidden_rate": gr["hidden"], "flagged": gr["flagged"],
            "honest_received": sub_value(tb, pol_gt, R, T)}


def decode(g_base, labels, copies, names, seen_caught, seen_ref):
    """Mean g per (type, where seen); and per exploit copy for exploit-only rows."""
    out = {}
    where = np.where(seen_caught & seen_ref, "caught & reference",
                     np.where(seen_caught, "caught only", np.where(seen_ref, "reference only", "unseen")))
    for t in np.unique(labels):
        m = labels == t
        out[t] = {w: [round(float(g_base[m & (where == w)].mean()), 2), int((m & (where == w)).sum())]
                  for w in ("caught & reference", "caught only", "reference only", "unseen") if (m & (where == w)).any()}
    ex = np.char.find(labels.astype(str), "exploit-only") >= 0
    out["exploit-only rows by copy"] = {
        names.get(int(cp), str(cp)): {w: round(float(g_base[ex & (copies == cp) & (where == w)].mean()), 2)
                                      for w in ("caught only", "unseen", "reference only", "caught & reference")
                                      if (ex & (copies == cp) & (where == w)).any()}
        for cp in np.unique(copies[ex])}
    return out


def diag(cfg, levels, n_draws, eps, ref_seed, log):
    seed = int(cfg["seed"])
    task = get_task(cfg["env"], **cfg["task"])
    proto = Protocol(**cfg["protocol"])
    pb, gcfg = cfg["pbrr"], GConfig(**cfg["g"])
    tb, T, W, A = task.tables, proto.t_sub, proto.window, task.n_actions
    base = task.base
    labels, copies, names = (types_boat if "boat" in cfg["env"] else types_taxi)(base)
    rs = seed if ref_seed is None else ref_seed
    ref, _ = build_reference(task, T, {**pb, "seed": pb["ref_seed"]})
    ref_trajs = rollouts(task.make_batch(pb["k"], seed=1000 + rs), ref, proto, np.random.default_rng(1000 + rs))
    pol_gt = solve_subepisode(tb, tb.true, T)
    nb = base.tables.n_states * base.tables.n_actions
    # distinct reward-model rows (g ignores the lap index / the picked-up bit and the counter): decode per row id
    G0 = base.g_rows_from_keys(base.support_keys()[:, 0])
    _, rep, gid = np.unique(G0, axis=0, return_index=True, return_inverse=True)
    gid = gid.reshape(-1)
    labels_g, copies_g = labels[rep], copies[rep]
    seen_ref = np.zeros(len(rep), bool)
    seen_ref[gid[base_rows_of_keys(task, np.concatenate([t.keys for t in ref_trajs]))]] = True
    out = {"levels": [], "level0": round_report(task, tb, tb.proxy, T, W, labels, copies, names, pol_gt)}
    Rbar, D = [tb.proxy.copy()], [[] for _ in range(n_draws)]
    for c in range(1, levels + 1):
        t0 = time.time()
        pol_c = solve_subepisode_caught(tb, Rbar[c - 1], T, W)
        fn = table_policy_fn(pol_c, A, eps)
        acc, rec = np.zeros_like(tb.proxy), {"draws": []}
        for d in range(n_draws):
            rng = np.random.default_rng([seed, d, c, 4])
            agent = rollouts(task.make_batch(pb["k"], seed=int(rng.integers(2 ** 31))), fn, proto, rng,
                             t0=(c - 1) * T, n_corr=c - 1)
            D[d] = D[d] + [(a, r, boltzmann_label(a, r, rng, pb["beta"])) for a in agent for r in ref_trajs]
            params, info = fit_correction_rows(D[d], task, gcfg, seed=int(rng.integers(2 ** 31)))
            g_aug = g_table(params, task)
            if gcfg.unseen_post != "none":
                g_aug = unseen_override(g_aug, params, D[d], task, gcfg.unseen_post)
            Rd = tb.proxy + g_aug
            acc += Rd
            g_rows_ = g_table(params, base)[:, 0][rep]
            seen_c = np.zeros(len(rep), bool)
            seen_c[gid[base_rows_of_keys(task, np.concatenate([t.keys for t in agent]))]] = True
            rec["draws"].append({"decode": decode(g_rows_, labels_g, copies_g, names, seen_c, seen_ref),
                                 "best_round": round_report(task, tb, Rd, T, W, labels, copies, names, pol_gt),
                                 "fit": {k: v for k, v in info.items() if k not in ("g_rows", "rows")}})
        Rbar.append(acc / n_draws)
        rec["mean_table_best_round"] = round_report(task, tb, Rbar[-1], T, W, labels, copies, names, pol_gt)
        rec["caught_policy"] = round_report(task, tb, Rbar[c - 1], T, W, labels, copies, names, pol_gt)
        rec["seconds"] = time.time() - t0
        b = rec["mean_table_best_round"]
        log(f"  level {c}: best round received {b['received']:.1f} true {b['true']:.1f} exploit steps "
            f"{b['exploit_steps']:.1f} {b['exploit_copies']} goal {b['goal_rate']:.2f} flagged {b['flagged']:.2f}; "
            f"honest {b['honest_received']:.1f}; per draw honest-best "
            f"{sum(x['best_round']['honest_received'] >= x['best_round']['received'] - 1e-6 for x in rec['draws'])}"
            f"/{n_draws} ({rec['seconds']:.0f}s)")
        out["levels"].append(rec)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", required=True, choices=["taxi_goal", "boat_race_goal"])
    ap.add_argument("--variants", nargs="+", default=["base", "P1eq1", "P2swap"])
    ap.add_argument("--seeds", nargs="+", type=int, required=True)
    ap.add_argument("--set", nargs="*", default=[], help="extra overrides, e.g. task.g_index=True pbrr.k=50")
    ap.add_argument("--levels", type=int, default=4)
    ap.add_argument("--draws", type=int, default=6)
    ap.add_argument("--eps", type=float, default=0.05)
    ap.add_argument("--ref-seed", type=int, default=None, help="use this seed's reference rollouts")
    ap.add_argument("--tag", required=True)
    args = ap.parse_args()
    out_dir = os.path.join(OUT, args.env, "goal_fixes")
    os.makedirs(out_dir, exist_ok=True)
    for s in args.seeds:
        path = os.path.join(out_dir, f"diag_{args.tag}_seed{s}.json")
        if os.path.exists(path):
            print(f"{path} exists: skipped (never overwritten)")
            continue
        res = {"env": args.env, "seed": s, "set": args.set, "ref_seed": args.ref_seed, "variants": {}}
        for v in args.variants:
            ov = parse_sets(args.set + ["g.epochs=1000"] + [f"g.{k}={val}" for k, val in VARIANTS[v].items()])
            cfg = resolve_config(args.env, {**ov, "seed": s})
            print(f"{args.env} {v} seed {s} ({args.tag}):", flush=True)
            res["variants"][v] = diag(cfg, args.levels, args.draws, args.eps, args.ref_seed,
                                      lambda m: print(m, flush=True))
        with open(path + ".tmp", "w") as fh:
            json.dump(res, fh, indent=1, default=float)
        os.replace(path + ".tmp", path)


if __name__ == "__main__":
    main()
