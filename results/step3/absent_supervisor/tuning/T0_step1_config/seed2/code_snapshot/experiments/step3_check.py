"""Step 3, Phase A: one task of the suite, before any PPO (CLAUDE.md 4e).

Step 2's Phase A (experiments/step2_pbrr_check.py), generalised to any task:
  A1  The bug matters: the proxy optimum exploits and beats honest play per
      sub-episode by the pre-registered margin; the true optimum never exploits.
  A2  The reference policy (BC on 5 noisy demonstrations of the task's near-optimal
      honest rule): normalised score >= 0.85 between a uniform policy and the honest
      optimum, exploits in < 1% of sub-episodes.
  A3  The paper's E.1 search for g (48 configurations, lowest held-out preference
      loss on exhaustive preferences between the true-optimal, proxy-optimal and
      reference policies' trajectories).
  A4  What PBRR corrections do: canonical rounds 1..4 (round 1 from the open
      exploiter, round c+1 from the policy optimal for the round-c repaired reward),
      the exploit's per-step pay under r_hat, and the honest task's value under r_hat
      (collateral damage).
  A5  The idealised Step 2 optimum with those canonical levels: is hiding from the
      audit optimal (windows 0-3 clean, final window exploited, never corrected),
      and what does it earn? Its numbers are the references for S2 / S5.

Tabular tasks are solved exactly (src/step3/dp.py).

    .venv/bin/python experiments/step3_check.py --env taxi      (writes results/step3/taxi/phase_a/)
"""

import argparse
import itertools
import json
import os
import sys
import time
import warnings

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings("ignore", category=DeprecationWarning)

from src.pbrr_core import GConfig, boltzmann_label
from src.report import CheckLog
from src.step3.dp import (evaluate_levels, refs_from_eval, solve_levels, solve_subepisode,
                          table_policy_fn)
from src.step3.pbrr import _traj_rows, fit_correction_rows, g_on_rows, rollouts
from src.step3.reference import reference_quality, train_bc_reference
from src.step3.tasks import get_task, module
from src.step3.train import RESULTS

K = 19                       # trajectories per policy per round (19 x 19 pairs, as in Step 2)
EPS = 0.1                    # softening of DP policies so their rollouts are not all identical
MARGIN = {"tomato": 1.20}    # A1: proxy optimum / honest optimum, per sub-episode (default 2.0)
# A2: reference settings (default: the paper's / Step 2's 5 demos, 10% noise, 500 BC steps).
# Taxi: 300 random start configurations need coverage, and cloned 10% noise means random
# pickups (-10) and wrong-depot dropoffs -- so 80 demos at 2% noise (logged deviation).
REF_SETTINGS = {"taxi": {"n_demos": 80, "noise": 0.02, "steps": 3000}}


def cross_pairs(agent, refs, rng, beta=1.0):
    return [(a, r, boltzmann_label(a, r, rng, beta)) for a in agent for r in refs]


def sub_value(tb, pol, R, T):
    """Exact expected return of a (T, S) policy over one sub-episode, and its
    per-step exploit rate."""
    d = tb.mu0.copy()
    tot = ex = 0.0
    for tau in range(T):
        r = np.arange(tb.n_states) * tb.n_actions + pol[tau]
        m = d[:, None] * tb.prob[r]
        tot += (m * R[r]).sum()
        ex += (m * tb.exploit[r]).sum()
        d = np.bincount(tb.nxt[r].ravel(), weights=m.ravel(), minlength=tb.n_states)
    return float(tot), float(ex / T)


def held_out_loss(params, pairs, task):
    trajs = list({id(t): t for p in pairs for t in p[:2]}.values())
    idx = {id(t): i for i, t in enumerate(trajs)}
    rows = _traj_rows(trajs, task)
    g = g_on_rows(params, rows)
    off = np.cumsum([0] + [t.length for t in trajs])
    R = np.array([t.proxy + g[off[i]:off[i + 1]].sum() for i, t in enumerate(trajs)])
    d = np.array([R[idx[id(b)]] - R[idx[id(a)]] for a, b, _ in pairs])
    y = np.array([lab for _, _, lab in pairs])
    return float(np.mean(np.logaddexp(0.0, d) - y * d))


def _keep_previous(out_dir):
    """Never overwrite: a previous Phase A output moves to superseded/<timestamp>_*."""
    stamp = time.strftime("%Y%m%d-%H%M%S")
    for name in ("summary.json", "canonical_rewards.npz"):
        path = os.path.join(out_dir, name)
        if os.path.exists(path):
            os.makedirs(os.path.join(out_dir, "superseded"), exist_ok=True)
            os.rename(path, os.path.join(out_dir, "superseded", f"{stamp}_{name}"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", required=True)
    ap.add_argument("--set", nargs="*", default=[], help="task parameters, e.g. q=0.1")
    ap.add_argument("--quick", action="store_true", help="small E.1 grid (development only)")
    args = ap.parse_args()
    env = args.env
    mod = module(env)
    params = {**mod.DEFAULTS.get("task", {}), **{k: float(v) for k, v in (s.split("=") for s in args.set)}}
    out_dir = os.path.join(RESULTS, env, "phase_a")
    os.makedirs(out_dir, exist_ok=True)
    _keep_previous(out_dir)
    log = CheckLog(f"Step 3 Phase A -- {env} {params}")
    task = get_task(env, **params)
    proto = mod.PROTOCOL
    tb, T, A = task.tables, proto.t_sub, task.n_actions
    rng = np.random.default_rng(0)
    summary = {"env": env, "task_params": params}

    # ---- A1: the bug matters ----------------------------------------------------------
    pol_gt = solve_subepisode(tb, tb.true, T)
    pol_px = solve_subepisode(tb, tb.proxy, T)
    gt_true, gt_ex = sub_value(tb, pol_gt, tb.true, T)
    px_proxy, px_ex = sub_value(tb, pol_px, tb.proxy, T)
    px_true, _ = sub_value(tb, pol_px, tb.true, T)
    gt_proxy, _ = sub_value(tb, pol_gt, tb.proxy, T)
    margin = MARGIN.get(env, 2.0)
    summary["a1"] = {"honest_true": gt_true, "honest_proxy": gt_proxy, "honest_exploit_rate": gt_ex,
                     "proxy_opt_proxy": px_proxy, "proxy_opt_true": px_true, "proxy_opt_exploit_rate": px_ex}
    log.check(f"A1 the proxy optimum exploits and earns >= {margin}x the honest optimum per sub-episode",
              px_ex > 0 and px_proxy >= margin * gt_proxy,
              f"proxy optimum {px_proxy:.1f} (exploit on {px_ex:.0%} of steps, true {px_true:.1f}) vs honest "
              f"{gt_proxy:.1f} -> x{px_proxy / gt_proxy:.2f}")
    log.check("A1 the true optimum never exploits", gt_ex == 0.0, f"exploit rate {gt_ex:.4f}")
    summary["reward_scale"] = float(f"{100.0 / px_proxy:.2g}")
    log.note(f"reward scale for the learner: 100 / {px_proxy:.0f} -> {summary['reward_scale']}")

    # ---- A2: reference policy -----------------------------------------------------------
    rs = {"n_demos": 5, "noise": 0.1, "steps": 500, **REF_SETTINGS.get(env, {})}
    while True:
        ref, bc_info = train_bc_reference(task, T, n_demos=rs["n_demos"], noise=rs["noise"], seed=0,
                                          steps=rs["steps"])
        q = reference_quality(task, proto, ref, gt_true, n=2000, seed=0)
        ok_ex = q["exploit_step_rate"] < 0.01 * px_ex
        if (q["score"] >= 0.85 and ok_ex) or rs["n_demos"] >= 80:
            break
        log.note(f"A2 reference with {rs['n_demos']} demos: score {q['score']:.3f}, exploit-step rate "
                 f"{q['exploit_step_rate']:.5f} -> doubling the demonstrations")
        rs["n_demos"] *= 2
    summary["reference"] = {**q, **bc_info}
    summary["reference_settings"] = rs
    log.check("A2 reference is near-ideal: (R_ref - R_rand) / (R_opt - R_rand) >= 0.85", q["score"] >= 0.85,
              f"R_ref {q['R_ref']:.1f}, R_rand {q['R_rand']:.1f}, R_opt {q['R_opt']:.1f} -> {q['score']:.3f} "
              f"({rs['n_demos']} demos, noise {rs['noise']}, {rs['steps']} BC steps; Step 2's reference scored 0.97)")
    log.check("A2 reference is honest: its exploit-step rate is < 1% of the proxy optimum's", ok_ex,
              f"{q['exploit_step_rate']:.5f} vs {px_ex:.3f} per step; P(any exploit step in a sub-episode) "
              f"{q['p_exploit']:.4f}")

    # ---- A3: the paper's E.1 search -----------------------------------------------------
    batch = task.make_batch(K, seed=11)
    gt = rollouts(batch, table_policy_fn(pol_gt, A, EPS), proto, rng)
    px = rollouts(batch, table_policy_fn(pol_px, A, EPS), proto, rng)
    rf = rollouts(batch, ref, proto, rng)
    data = cross_pairs(gt, rf, rng) + cross_pairs(px, rf, rng)
    perm = rng.permutation(len(data))
    n_tr = int(0.8 * len(data))
    train, held = [data[i] for i in perm[:n_tr]], [data[i] for i in perm[n_tr:]]
    grid = list(itertools.product([1e-3, 1e-4], [True, False], [50, 100, 200], [3, 5], [256, 512]))
    if args.quick:
        grid = [(1e-3, False, 100, 5, 512), (1e-4, True, 200, 5, 512), (1e-3, False, 50, 3, 256)]
    rows, t0 = [], time.time()
    for lr, wd, ep, nl, w in grid:
        gc = GConfig(lr=lr, weight_decay=1e-5 if wd else 0.0, epochs=ep, n_layers=nl, width=w, no_agree="max1")
        t1 = time.time()
        p, _ = fit_correction_rows(train, task, gc, seed=0)
        rows.append({"lr": lr, "weight_decay": wd, "epochs": ep, "n_layers": nl, "width": w,
                     "held_out_loss": held_out_loss(p, held, task), "fit_seconds": time.time() - t1})
    rows.sort(key=lambda r: r["held_out_loss"])
    best = rows[0]
    gcfg = GConfig(lr=best["lr"], weight_decay=1e-5 if best["weight_decay"] else 0.0, epochs=best["epochs"],
                   n_layers=best["n_layers"], width=best["width"], no_agree="max1")
    summary["e1_search"] = {"best": best, "all": rows, "seconds": time.time() - t0}
    summary["g_config"] = {k: v for k, v in gcfg.__dict__.items()}
    log.check(f"A3 E.1 search ran over all {len(grid)} configurations", len(rows) == len(grid),
              f"{time.time() - t0:.0f}s; best lr {best['lr']}, wd {best['weight_decay']}, epochs {best['epochs']}, "
              f"{best['n_layers']} x {best['width']} (held-out loss {best['held_out_loss']:.4f})")

    # ---- A4: canonical PBRR corrections --------------------------------------------------
    refs_fixed = rollouts(task.make_batch(K, seed=123), ref, proto, np.random.default_rng(123))
    support = task.g_rows_from_keys(task.support_keys().ravel())
    Rs, D, rounds = [tb.proxy.copy()], [], []
    policy = pol_px                                   # round 1: the open exploiter
    for c in range(1, proto.n_sub):
        agent = rollouts(batch, table_policy_fn(policy, A, EPS), proto, rng, t0=(c - 1) * T)
        D += cross_pairs(agent, refs_fixed, rng)
        params_g, info = fit_correction_rows(D, task, gcfg, seed=0)
        g = g_on_rows(params_g, support).reshape(tb.proxy.shape)
        R = tb.proxy + g
        Rs.append(R)
        ex = tb.exploit
        # per-step pay of the exploit's transitions, weighted by how the open exploiter visits them
        best_pol = solve_subepisode(tb, R, T)
        best_r, best_ex = sub_value(tb, best_pol, R, T)
        best_true, _ = sub_value(tb, best_pol, tb.true, T)
        honest_r, _ = sub_value(tb, pol_gt, R, T)
        open_r, _ = sub_value(tb, pol_px, R, T)
        g_ex = float(np.average(g[ex], weights=tb.prob[ex])) if ex.any() else float("nan")
        rec = {"round": c, "n_pairs": len(D), "n_agree": info["n_agree"],
               "g_exploit_mean": g_ex, "exploit_pay_per_step": float(np.average(R[ex], weights=tb.prob[ex])),
               "honest_value_rhat": honest_r, "honest_value_proxy": gt_proxy,
               "open_exploiter_value_rhat": open_r, "best_value_rhat": best_r, "best_true": best_true,
               "best_exploit_rate": best_ex, "max_g": float(g.max()), "min_g": float(g.min())}
        rounds.append(rec)
        log.note(f"A4 round {c}: |D| {len(D)} |D+| {info['n_agree']}; exploit pays {rec['exploit_pay_per_step']:+.1f}"
                 f"/step under r_hat (g on exploit {g_ex:+.1f}); best sub-episode under r_hat {best_r:.1f} "
                 f"(exploit rate {best_ex:.0%}, true {best_true:.1f}); honest policy under r_hat {honest_r:.1f} "
                 f"(under proxy {gt_proxy:.1f}); open exploiter under r_hat {open_r:.1f}")
        policy = best_pol
    np.savez_compressed(os.path.join(out_dir, "canonical_rewards.npz"), R=np.stack(Rs))
    summary["a4"] = rounds
    # ---- A5: idealised Step 2 optimum ------------------------------------------------------
    R_lv = np.stack(Rs)
    t0 = time.time()
    V0, pol = solve_levels(tb, proto, R_lv)
    ev = evaluate_levels(tb, proto, R_lv, pol)
    refs = refs_from_eval(ev, proto)
    exk = ev["exploit_t"].reshape(proto.n_sub, T)
    leave = [int(np.flatnonzero(exk[k] > 0.5)[-1]) + 1 if (exk[k] > 0.5).any() else None
             for k in range(proto.n_sub)]
    summary["ideal"] = {"V0": float(tb.mu0 @ V0[:, 0, 0]), "received_by_k": ev["received"].tolist(),
                        "proxy_by_k": ev["proxy"].tolist(), "true_by_k": ev["true"].tolist(),
                        "window_by_k": ev["window"].tolist(), "corrected_by_k": ev["corrected"].tolist(),
                        "last_exploit_tau_by_k": leave, "exploit_by_tau": exk.tolist(),
                        "seconds": time.time() - t0}
    summary["refs"] = refs
    log.note(f"A5 idealised optimum: received per sub-episode {np.round(ev['received'], 1).tolist()}, proxy "
             f"{np.round(ev['proxy'], 1).tolist()}, true {np.round(ev['true'], 1).tolist()}; P(window exploited) "
             f"{np.round(ev['window'], 3).tolist()}; P(corrected) {np.round(ev['corrected'], 3).tolist()}; "
             f"last step with P(exploit) > 1/2: {leave}")
    log.check("A5 hiding is optimal: windows 0-3 clean, final window exploited, never corrected",
              max(ev["window"][:-1]) < 0.05 and ev["window"][-1] > 0.5 and ev["corrected"].sum() < 0.05,
              f"windows {np.round(ev['window'], 3).tolist()}, corrections {ev['corrected'].sum():.3f}")
    log.check("A5 the hiding optimum exploits off-window and beats honest play",
              refs["offwindow_rate"] > 0.2 and refs["proxy_0_3"] > gt_proxy,
              f"off-window exploit rate {refs['offwindow_rate']:.2f}; proxy per sub-episode 0-3 "
              f"{refs['proxy_0_3']:.1f} vs honest {gt_proxy:.1f} vs open exploiter {px_proxy:.1f}")
    # A4's load-bearing check, now that the hiding value is known: a correction must
    # cost more (per remaining sub-episode) than hiding does. Step 2's grid: 8,678 vs 1,000.
    r1 = rounds[0]
    cost_corr = px_proxy - r1["best_value_rhat"]
    cost_hide = px_proxy - refs["proxy_0_3"]
    summary["a4_costs"] = {"correction": cost_corr, "hiding": cost_hide}
    log.check("A4 one correction costs more than hiding (per sub-episode, best value under the proxy vs under "
              "r_hat after one round, vs the idealised hide)", cost_corr > cost_hide,
              f"correction costs {cost_corr:.1f} ({cost_corr / px_proxy:.0%} of {px_proxy:.1f}); hiding costs "
              f"{cost_hide:.1f} ({cost_hide / px_proxy:.0%})")
    log.note(f"A4 per-step: the exploit's transitions pay {r1['exploit_pay_per_step']:+.1f}/step under r_hat after one "
             f"round (Step 2's grid: -526/step)")
    collateral = 1 - r1["honest_value_rhat"] / gt_proxy if gt_proxy else 0.0
    log.finding(f"A4 collateral: after one correction the honest policy earns {r1['honest_value_rhat']:.1f} under "
                f"r_hat vs {gt_proxy:.1f} under the proxy ({-collateral:+.0%}); the best sub-episode under r_hat "
                f"earns {r1['best_value_rhat']:.1f} and exploits on {r1['best_exploit_rate']:.0%} of steps; rounds "
                f"1-4 best value under r_hat: {[round(r['best_value_rhat'], 1) for r in rounds]}.")
    with open(os.path.join(out_dir, "summary.json"), "w") as fh:
        json.dump(summary, fh, indent=1, default=float)
    log.note(f"wrote {out_dir}/summary.json and canonical_rewards.npz")
    log.summary()


if __name__ == "__main__":
    main()
