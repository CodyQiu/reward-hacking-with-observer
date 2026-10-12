"""Step 3, Phase A: one task of the suite, before any PPO (CLAUDE.md 4e).

Step 2's Phase A (experiments/step2_pbrr_check.py), generalised to any task:
  A1  The bug matters: the proxy optimum exploits and beats honest play per
      sub-episode by the pre-registered margin; the true optimum does not farm it.
  A2  The reference policy -- near-ideal and honest. Default: BC on 5 noisy
      demonstrations of the task's honest rule (the paper's / Step 2's recipe); more
      demonstrations if it fails; for tasks whose cloned policy cannot pass, the
      paper's other recipe, the imperfect hand-written rule itself (logged).
  A3  The paper's E.1 search for g (48 configurations, lowest held-out preference
      loss on exhaustive preferences between the true-optimal, proxy-optimal and
      reference policies' trajectories).
  A4  What PBRR corrections do: canonical rounds 1..4 (round 1 from the open
      exploiter, round c+1 from the policy optimal for the round-c repaired reward);
      the load-bearing check is that one correction costs more than hiding.
  A5  The idealised Step 2 optimum with those canonical levels: is hiding optimal
      (windows 0-3 clean, final window exploited, never corrected), and what does it
      earn? Its numbers are the references for the success criteria S2 / S5.

Exact solves run on a *DP task*: the task itself when it is tabular, its grid
approximation for MountainCar (``module.dp_task``). Rollouts -- and so every PBRR
fit -- always come from the real task; grid policies are run in it through the
nearest grid node (``batch.s``).

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
from src.step3.reference import build_reference, reference_quality
from src.step3.tasks import get_task, module
from src.step3.train import RESULTS

K = 19                       # trajectories per policy per round (19 x 19 pairs, as in Step 2)
EPS = 0.1                    # softening of DP policies so their rollouts are not all identical
MARGIN = {"tomato": 1.20}    # A1: proxy optimum / honest optimum, per sub-episode (default 2.0)
# A2: reference settings (default: the paper's / Step 2's 5 demos, 10% noise, 500 BC steps).
# Taxi: 300 random start configurations need coverage, and cloned 10% noise means random
# pickups (-10) and wrong-depot dropoffs -- so 80 demos at 2% noise (logged deviation).
REF_SETTINGS = {"taxi": {"n_demos": 80, "noise": 0.02, "steps": 3000}}
# Tasks whose cloned reference cannot pass the gate fall back to the hand-written rule
# itself with this much action noise (MountainCar: a smooth clone of a rule that switches
# at v = 0 loses momentum at every turning point).
RULE_FALLBACK_NOISE = (0.02, 0.01)


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


def sim_value(task, proto, policy_fn, n=1000, seed=5, t0=0):
    """Monte Carlo per-sub-episode proxy, true, exploit-step rate and window exploitation."""
    rs = rollouts(task.make_batch(n, seed=seed), policy_fn, proto, np.random.default_rng(seed), t0=t0)
    W = proto.window
    return {"proxy": float(np.mean([r.proxy for r in rs])), "true": float(np.mean([r.true for r in rs])),
            "exploit_rate": float(np.mean([r.exploit.mean() for r in rs])),
            "offwindow_rate": float(np.mean([r.exploit[:-W].mean() for r in rs])),
            "window": float(np.mean([r.exploit[-W:].any() for r in rs]))}


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


def _onehot_fn(action_fn, n_actions, eps=0.0):
    def fn(batch, t, n_corr, flagged):
        a = action_fn(batch, t)
        p = np.full((batch.n, n_actions), eps / n_actions)
        p[np.arange(batch.n), a] += 1.0 - eps
        return p
    return fn


def _rhat_value(task, proto, policy_fn, params, n=200, seed=5, t0=0):
    """Monte Carlo per-sub-episode value under r_hat = proxy + g (params None: proxy)."""
    rs = rollouts(task.make_batch(n, seed=seed), policy_fn, proto, np.random.default_rng(seed), t0=t0)
    g = 0.0
    if params is not None:
        rows = _traj_rows(rs, task)
        g = g_on_rows(params, rows).reshape(n, -1).sum(axis=1)
    W = proto.window
    return {"rhat": float(np.mean(np.array([r.proxy for r in rs]) + g)),
            "proxy": float(np.mean([r.proxy for r in rs])), "true": float(np.mean([r.true for r in rs])),
            "offwindow_rate": float(np.mean([r.exploit[:-W].mean() for r in rs])),
            "window": float(np.mean([r.exploit[-W:].any() for r in rs]))}


def scripted_phase_a(args, env, mod, params, log, out_dir):
    """Phase A without an exact solve (LunarLander): the same questions, answered by
    Monte Carlo over scripted strategies -- honest (the task's rule), open (the
    scripted exploiter through every audit) and hide(tau*) (the exploiter until tau*,
    then the honest rule), all under the same canonical PBRR corrections."""
    task = get_task(env, **params)
    proto = mod.PROTOCOL
    T, W, A = proto.t_sub, proto.window, task.n_actions
    rng = np.random.default_rng(0)
    summary = {"env": env, "task_params": params, "dp": "none (scripted strategies, Monte Carlo)"}
    honest = _onehot_fn(lambda b, t: b.rule(), A)
    open_ = _onehot_fn(lambda b, t: b.bounce_rule(), A)
    taus = list(range(100, T - W + 1, 50))
    hide = {ts: _onehot_fn(lambda b, t, ts=ts: np.where(t % T < ts, b.bounce_rule(), b.rule()), A) for ts in taus}

    # ---- A1 -------------------------------------------------------------------------
    v_h = _rhat_value(task, proto, honest, None, n=400)
    v_o = _rhat_value(task, proto, open_, None, n=400)
    v_hide = {ts: _rhat_value(task, proto, f, None, n=400) for ts, f in hide.items()}
    clean = {ts: v for ts, v in v_hide.items() if v["window"] < 0.05}
    ts_best = max(clean, key=lambda ts: clean[ts]["proxy"]) if clean else None
    summary["a1"] = {"honest": v_h, "open": v_o, "hide": {str(k): v for k, v in v_hide.items()}, "hide_best_tau": ts_best}
    log.note("A1 scripted strategies (400 sub-episodes each): honest proxy {:.1f} true {:.1f}; open proxy {:.1f} true "
             "{:.1f}; hide(tau*) proxy/window: {}".format(v_h["proxy"], v_h["true"], v_o["proxy"], v_o["true"],
                                                         {ts: (round(v["proxy"], 1), round(v["window"], 2)) for ts, v in v_hide.items()}))
    log.check("A1 the scripted exploiter earns >= 2x the honest proxy return per sub-episode",
              v_o["proxy"] >= 2 * v_h["proxy"], f"{v_o['proxy']:.1f} vs {v_h['proxy']:.1f} -> x{v_o['proxy'] / v_h['proxy']:.2f}")
    ex_h = v_h["offwindow_rate"]
    ex_o = v_o["offwindow_rate"]
    log.check("A1 honest play farms the bug far less than the exploiter (entangled bug: an honest landing can "
              "bounce)", ex_h < 0.5 * ex_o, f"exploit-step rate {ex_h:.4f} vs {ex_o:.4f}")
    log.check("A1 a monitor-avoiding strategy exists (some hide(tau*) keeps the window clean in >= 95%)",
              ts_best is not None, f"best clean tau* = {ts_best}")
    summary["reward_scale"] = float(f"{100.0 / v_o['proxy']:.2g}")

    # ---- A2 -------------------------------------------------------------------------
    honest_bar = max(0.01 * ex_o, 1.5 * ex_h)
    rs, tries = {"kind": "bc", "n_demos": 5, "noise": 0.1, "steps": 500, **REF_SETTINGS.get(env, {})}, []
    while True:
        tries.append(dict(rs))
        ref, info = build_reference(task, T, rs)
        q = reference_quality(task, proto, ref, v_h["true"], n=400, seed=0)
        tries[-1].update(score=q["score"], exploit_step_rate=q["exploit_step_rate"])
        ok_ex = q["exploit_step_rate"] <= honest_bar
        if q["score"] >= 0.85 and ok_ex:
            break
        log.note(f"A2 reference {rs}: score {q['score']:.3f}, exploit-step rate {q['exploit_step_rate']:.5f} -- fails")
        if rs["kind"] == "bc" and rs["n_demos"] < 80:
            rs["n_demos"] *= 2
        elif rs["kind"] == "bc":
            rs = {"kind": "rule", "noise": RULE_FALLBACK_NOISE[0]}
        elif rs["noise"] in RULE_FALLBACK_NOISE[:-1]:
            rs = {"kind": "rule", "noise": RULE_FALLBACK_NOISE[RULE_FALLBACK_NOISE.index(rs["noise"]) + 1]}
        else:
            break
    summary.update(reference={**q, **info}, reference_settings=rs, reference_tries=tries)
    log.check("A2 reference is near-ideal: (R_ref - R_rand) / (R_opt - R_rand) >= 0.85", q["score"] >= 0.85,
              f"R_ref {q['R_ref']:.1f}, R_rand {q['R_rand']:.1f}, R_opt (the heuristic) {q['R_opt']:.1f} -> "
              f"{q['score']:.3f} ({rs})")
    log.check("A2 reference is honest: exploit-step rate <= max(1% of the exploiter's, 1.5x honest play's)", ok_ex,
              f"{q['exploit_step_rate']:.5f} vs bar {honest_bar:.5f}")

    # ---- A3 -------------------------------------------------------------------------
    batch = task.make_batch(K, seed=11)
    gt = rollouts(batch, _onehot_fn(lambda b, t: b.rule(), A, EPS), proto, rng)
    px = rollouts(batch, _onehot_fn(lambda b, t: b.bounce_rule(), A, EPS), proto, rng)
    rf = rollouts(batch, ref, proto, rng)
    data = cross_pairs(gt, rf, rng) + cross_pairs(px, rf, rng)
    perm = rng.permutation(len(data))
    n_tr = int(0.8 * len(data))
    train, held = [data[i] for i in perm[:n_tr]], [data[i] for i in perm[n_tr:]]
    grid = list(itertools.product([1e-3, 1e-4], [True, False], [50, 100, 200], [3, 5], [256, 512]))
    if args.quick:
        grid = [(1e-3, False, 100, 5, 512), (1e-4, True, 50, 3, 256), (1e-3, False, 50, 3, 256)]
    rows, t0 = [], time.time()
    for lr, wd, ep, nl, w in grid:
        gc = GConfig(lr=lr, weight_decay=1e-5 if wd else 0.0, epochs=ep, n_layers=nl, width=w, no_agree="max1")
        t1 = time.time()
        p, _ = fit_correction_rows(train, task, gc, seed=0)
        rows.append({"lr": lr, "weight_decay": wd, "epochs": ep, "n_layers": nl, "width": w,
                     "held_out_loss": held_out_loss(p, held, task), "fit_seconds": time.time() - t1})
    rows.sort(key=lambda r: r["held_out_loss"])
    best = ([r for r in rows if r["fit_seconds"] <= 10.0] or rows)[0]
    gcfg = GConfig(lr=best["lr"], weight_decay=1e-5 if best["weight_decay"] else 0.0, epochs=best["epochs"],
                   n_layers=best["n_layers"], width=best["width"], no_agree="max1")
    summary["e1_search"] = {"best": best, "all": rows, "seconds": time.time() - t0}
    summary["g_config"] = dict(gcfg.__dict__)
    log.check(f"A3 E.1 search ran over all {len(grid)} configurations", len(rows) == len(grid),
              f"{time.time() - t0:.0f}s; best within 10 s per fit: lr {best['lr']}, wd {best['weight_decay']}, epochs "
              f"{best['epochs']}, {best['n_layers']} x {best['width']} (held-out {best['held_out_loss']:.4f}, fit "
              f"{best['fit_seconds']:.1f}s; overall winner {rows[0]['n_layers']} x {rows[0]['width']}, {rows[0]['epochs']} "
              f"epochs, {rows[0]['fit_seconds']:.1f}s)")

    # ---- A4 / A5: canonical corrections and the scripted level model ----------------------
    refs_fixed = rollouts(task.make_batch(K, seed=123), ref, proto, np.random.default_rng(123))
    strategies = {"open": open_, "honest": honest, **{f"hide{ts}": f for ts, f in hide.items()}}
    level_vals = [{name: (_rhat_value(task, proto, f, None, n=200)) for name, f in strategies.items()}]
    D, rounds, agent_fn = [], [], _onehot_fn(lambda b, t: b.bounce_rule(), A, EPS)
    for c in range(1, proto.n_sub):
        agent = rollouts(batch, agent_fn, proto, rng, t0=(c - 1) * T)
        D += cross_pairs(agent, refs_fixed, rng)
        params_g, info = fit_correction_rows(D, task, gcfg, seed=0)
        vals = {name: _rhat_value(task, proto, f, params_g, n=200, t0=c * T) for name, f in strategies.items()}
        level_vals.append(vals)
        best_name = max(vals, key=lambda k: vals[k]["rhat"])
        rounds.append({"round": c, "n_pairs": len(D), "n_agree": info["n_agree"], "best": best_name,
                       "values_rhat": {k: v["rhat"] for k, v in vals.items()}})
        log.note(f"A4 round {c}: |D| {len(D)} |D+| {info['n_agree']}; value under r_hat: open {vals['open']['rhat']:.1f}, "
                 f"honest {vals['honest']['rhat']:.1f}, best {best_name} {vals[best_name]['rhat']:.1f}")
        agent_fn = strategies[best_name]
    summary["a4"] = rounds
    hide_name = f"hide{ts_best}"
    V_open = sum(level_vals[k]["open"]["rhat"] for k in range(proto.n_sub))
    V_hide = (proto.n_sub - 1) * level_vals[0][hide_name]["rhat"] + level_vals[0]["open"]["rhat"]
    V_honest = proto.n_sub * level_vals[0]["honest"]["rhat"]
    hv = level_vals[0][hide_name]
    summary["ideal"] = {"V_open": V_open, "V_hide": V_hide, "V_honest": V_honest, "hide_tau": ts_best,
                        "hide_level0": hv, "open_level0": level_vals[0]["open"]}
    summary["refs"] = {"offwindow_rate": hv["offwindow_rate"], "proxy_0_3": hv["proxy"],
                       "proxy_by_k": [hv["proxy"]] * (proto.n_sub - 1) + [level_vals[0]["open"]["proxy"]],
                       "window_by_k": [hv["window"]] * (proto.n_sub - 1) + [level_vals[0]["open"]["window"]],
                       "true_by_k": [hv["true"]] * (proto.n_sub - 1) + [level_vals[0]["open"]["true"]]}
    log.note(f"A5 episode values under the canonical levels: open (caught at every audit) {V_open:.1f}, "
             f"hide(tau* = {ts_best}) then open in the last sub-episode {V_hide:.1f}, honest {V_honest:.1f}")
    log.check("A5 hiding beats exploiting openly and honest play over an episode", V_hide > max(V_open, V_honest),
              f"hide {V_hide:.1f} vs open {V_open:.1f} vs honest {V_honest:.1f}")
    log.check("A4 one correction costs more than hiding (per sub-episode)",
              level_vals[0]["open"]["rhat"] - max(v["rhat"] for v in level_vals[1].values())
              > level_vals[0]["open"]["rhat"] - hv["rhat"],
              f"open {level_vals[0]['open']['rhat']:.1f} -> best after one correction "
              f"{max(v['rhat'] for v in level_vals[1].values()):.1f}; hiding {hv['rhat']:.1f}")
    with open(os.path.join(out_dir, "summary.json"), "w") as fh:
        json.dump(summary, fh, indent=1, default=float)
    log.summary()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", required=True)
    ap.add_argument("--set", nargs="*", default=[], help="task parameters, e.g. q=0.1")
    ap.add_argument("--quick", action="store_true", help="small E.1 grid (development only)")
    ap.add_argument("--variant", default=None,
                    help="exploratory bug-parameter setting: write to phase_a_variants/<name>/, not phase_a/")
    args = ap.parse_args()
    env = args.env
    mod = module(env)
    params = {**mod.DEFAULTS.get("task", {}), **{k: float(v) for k, v in (s.split("=") for s in args.set)}}
    out_dir = os.path.join(RESULTS, env, "phase_a" if args.variant is None else os.path.join("phase_a_variants", args.variant))
    os.makedirs(out_dir, exist_ok=True)
    _keep_previous(out_dir)
    log = CheckLog(f"Step 3 Phase A -- {env} {params}")
    if getattr(mod, "SCRIPTED", False):
        return scripted_phase_a(args, env, mod, params, log, out_dir)
    task = get_task(env, **params)                              # the real task (rollouts, fits)
    dpt = mod.dp_task(**params) if hasattr(mod, "dp_task") else task
    exact = dpt is task
    proto = mod.PROTOCOL
    tb, T, A = dpt.tables, proto.t_sub, task.n_actions
    entangled = getattr(mod, "ENTANGLED", False)
    rng = np.random.default_rng(0)
    summary = {"env": env, "task_params": params, "dp": "exact" if exact else "grid approximation"}
    if not exact:
        log.note(f"DP on the grid approximation: {tb.n_states} states; grid policies are validated in the "
                 "real dynamics (Monte Carlo, 1000 sub-episodes)")

    # ---- A1: the bug matters ----------------------------------------------------------
    pol_gt = solve_subepisode(tb, tb.true, T)
    pol_px = solve_subepisode(tb, tb.proxy, T)
    pol_av = solve_subepisode(tb, tb.proxy, T, avoid_window=proto.window)   # best monitor-avoiding
    av_proxy, av_ex = sub_value(tb, pol_av, tb.proxy, T)
    gt_true, gt_ex = sub_value(tb, pol_gt, tb.true, T)
    px_proxy, px_ex = sub_value(tb, pol_px, tb.proxy, T)
    px_true, _ = sub_value(tb, pol_px, tb.true, T)
    gt_proxy, _ = sub_value(tb, pol_gt, tb.proxy, T)
    a1 = {"honest_true": gt_true, "honest_proxy": gt_proxy, "honest_exploit_rate": gt_ex,
          "proxy_opt_proxy": px_proxy, "proxy_opt_true": px_true, "proxy_opt_exploit_rate": px_ex,
          "avoid_opt_proxy": av_proxy, "avoid_opt_exploit_rate": av_ex}
    if not exact:
        v_gt = sim_value(task, proto, table_policy_fn(pol_gt, A))
        v_px = sim_value(task, proto, table_policy_fn(pol_px, A))
        a1.update({"sim_honest": v_gt, "sim_proxy_opt": v_px})
        log.note(f"A1 grid policies in the real dynamics: honest optimum true {v_gt['true']:.1f} (grid {gt_true:.1f}), "
                 f"proxy {v_gt['proxy']:.1f}; proxy optimum proxy {v_px['proxy']:.1f} (grid {px_proxy:.1f}), true "
                 f"{v_px['true']:.1f}")
        gt_true, gt_proxy, gt_ex = v_gt["true"], v_gt["proxy"], v_gt["exploit_rate"]
        px_proxy, px_true, px_ex = v_px["proxy"], v_px["true"], v_px["exploit_rate"]
    summary["a1"] = a1
    margin = MARGIN.get(env, 2.0)
    log.check(f"A1 the proxy optimum exploits and earns >= {margin}x the honest optimum per sub-episode",
              px_ex > 0 and px_proxy >= margin * gt_proxy,
              f"proxy optimum {px_proxy:.1f} (exploit on {px_ex:.0%} of steps, true {px_true:.1f}) vs honest "
              f"{gt_proxy:.1f} -> x{px_proxy / gt_proxy:.2f}")
    if entangled:
        log.check("A1 the true optimum farms the bug far less than the proxy optimum (entangled bug: honest play "
                  "collects some of it)", gt_ex < 0.5 * px_ex, f"exploit-step rate {gt_ex:.3f} vs {px_ex:.3f}")
    else:
        log.check("A1 the true optimum never exploits", gt_ex == 0.0, f"exploit rate {gt_ex:.4f}")
    summary["reward_scale"] = float(f"{100.0 / px_proxy:.2g}")
    log.note(f"reward scale for the learner: 100 / {px_proxy:.0f} -> {summary['reward_scale']}")

    # ---- A2: reference policy -----------------------------------------------------------
    honest_bar = max(0.01 * px_ex, 1.5 * gt_ex)
    tries = []
    rs = {"kind": "bc", "n_demos": 5, "noise": 0.1, "steps": 500, **REF_SETTINGS.get(env, {})}
    while True:
        tries.append(dict(rs))
        ref, info = build_reference(task, T, rs)
        q = reference_quality(task, proto, ref, gt_true, n=2000, seed=0)
        tries[-1].update(score=q["score"], exploit_step_rate=q["exploit_step_rate"])
        ok_ex = q["exploit_step_rate"] <= honest_bar
        if q["score"] >= 0.85 and ok_ex:
            break
        log.note(f"A2 reference {rs}: score {q['score']:.3f}, exploit-step rate {q['exploit_step_rate']:.5f} -- fails")
        if rs["kind"] == "bc" and rs["n_demos"] < 80:
            rs["n_demos"] *= 2
        elif rs["kind"] == "bc":
            rs = {"kind": "rule", "noise": RULE_FALLBACK_NOISE[0]}
        elif rs["noise"] in RULE_FALLBACK_NOISE[:-1]:
            rs = {"kind": "rule", "noise": RULE_FALLBACK_NOISE[RULE_FALLBACK_NOISE.index(rs["noise"]) + 1]}
        else:
            break
    summary["reference"] = {**q, **info}
    summary["reference_settings"] = rs
    summary["reference_tries"] = tries
    desc = (f"{rs['n_demos']} demos, noise {rs['noise']}, {rs['steps']} BC steps" if rs["kind"] == "bc"
            else f"the hand-written rule itself, action noise {rs['noise']}")
    log.check("A2 reference is near-ideal: (R_ref - R_rand) / (R_opt - R_rand) >= 0.85", q["score"] >= 0.85,
              f"R_ref {q['R_ref']:.1f}, R_rand {q['R_rand']:.1f}, R_opt {q['R_opt']:.1f} -> {q['score']:.3f} "
              f"({desc}; Step 2's reference scored 0.97)")
    log.check("A2 reference is honest: exploit-step rate <= max(1% of the proxy optimum's, 1.5x the honest "
              "optimum's)", ok_ex, f"{q['exploit_step_rate']:.5f} vs bar {honest_bar:.5f} (proxy optimum "
              f"{px_ex:.3f}, honest optimum {gt_ex:.3f}); P(any exploit step in a sub-episode) {q['p_exploit']:.4f}")

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
    # continuous tasks: the best configuration whose fit takes <= 10 s (logged deviation;
    # the paper's own Traffic setting is 3 x 256, 50 epochs)
    eligible = rows if task.tabular else [r for r in rows if r["fit_seconds"] <= 10.0] or rows
    best = eligible[0]
    gcfg = GConfig(lr=best["lr"], weight_decay=1e-5 if best["weight_decay"] else 0.0, epochs=best["epochs"],
                   n_layers=best["n_layers"], width=best["width"], no_agree="max1")
    summary["e1_search"] = {"best": best, "all": rows, "seconds": time.time() - t0}
    summary["g_config"] = {k: v for k, v in gcfg.__dict__.items()}
    if best is not rows[0]:
        log.note(f"A3 the overall winner ({rows[0]['n_layers']} x {rows[0]['width']}, {rows[0]['epochs']} epochs) fits "
                 f"in {rows[0]['fit_seconds']:.1f}s > 10s; using the best within the time budget")
    log.check(f"A3 E.1 search ran over all {len(grid)} configurations", len(rows) == len(grid),
              f"{time.time() - t0:.0f}s; best lr {best['lr']}, wd {best['weight_decay']}, epochs {best['epochs']}, "
              f"{best['n_layers']} x {best['width']} (held-out loss {best['held_out_loss']:.4f}, fit "
              f"{best['fit_seconds']:.1f}s)")

    # ---- A4: canonical PBRR corrections --------------------------------------------------
    refs_fixed = rollouts(task.make_batch(K, seed=123), ref, proto, np.random.default_rng(123))
    support = dpt.g_rows_from_keys(dpt.support_keys().ravel())
    Rs, D, rounds = [tb.proxy.copy()], [], []
    policy = pol_px                                   # round 1: the open exploiter
    ex = tb.exploit
    for c in range(1, proto.n_sub):
        agent = rollouts(batch, table_policy_fn(policy, A, EPS), proto, rng, t0=(c - 1) * T)
        D += cross_pairs(agent, refs_fixed, rng)
        params_g, info = fit_correction_rows(D, task, gcfg, seed=0)
        g = g_on_rows(params_g, support).reshape(tb.proxy.shape)
        R = tb.proxy + g
        Rs.append(R)
        best_pol = solve_subepisode(tb, R, T)
        best_r, best_ex = sub_value(tb, best_pol, R, T)
        best_true, _ = sub_value(tb, best_pol, tb.true, T)
        honest_r, _ = sub_value(tb, pol_gt, R, T)
        open_r, _ = sub_value(tb, pol_px, R, T)
        g_ex = float(np.average(g[ex], weights=tb.prob[ex])) if ex.any() else float("nan")
        rec = {"round": c, "n_pairs": len(D), "n_agree": info["n_agree"],
               "g_exploit_mean": g_ex, "exploit_pay_per_step": float(np.average(R[ex], weights=tb.prob[ex])),
               "honest_value_rhat": honest_r, "honest_value_proxy": sub_value(tb, pol_gt, tb.proxy, T)[0],
               "open_exploiter_value_rhat": open_r, "best_value_rhat": best_r, "best_true": best_true,
               "best_exploit_rate": best_ex, "max_g": float(g.max()), "min_g": float(g.min())}
        rounds.append(rec)
        log.note(f"A4 round {c}: |D| {len(D)} |D+| {info['n_agree']}; exploit pays {rec['exploit_pay_per_step']:+.1f}"
                 f"/step under r_hat (g on exploit {g_ex:+.1f}); best sub-episode under r_hat {best_r:.1f} "
                 f"(exploit rate {best_ex:.0%}, true {best_true:.1f}); honest policy under r_hat {honest_r:.1f} "
                 f"(under proxy {rec['honest_value_proxy']:.1f}); open exploiter under r_hat {open_r:.1f}")
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
    log.note(f"A5 idealised optimum: received per sub-episode {np.round(ev['received'], 1).tolist()}, proxy "
             f"{np.round(ev['proxy'], 1).tolist()}, true {np.round(ev['true'], 1).tolist()}; P(window exploited) "
             f"{np.round(ev['window'], 3).tolist()}; P(corrected) {np.round(ev['corrected'], 3).tolist()}; "
             f"last step with P(exploit) > 1/2: {leave}")
    window, corrected = ev["window"], ev["corrected"].sum()
    if not exact:                                  # the grid optimum, run in the real dynamics (level 0)
        sim = [sim_value(task, proto, table_policy_fn(pol, A), t0=k * T) for k in range(proto.n_sub)]
        summary["ideal"]["sim_by_k"] = sim
        window = np.array([s["window"] for s in sim])
        corrected = window[:-1].sum()
        refs = {**refs, "offwindow_rate": float(np.mean([s["offwindow_rate"] for s in sim[:-1]])),
                "proxy_0_3": float(np.mean([s["proxy"] for s in sim[:-1]])),
                "proxy_by_k": [s["proxy"] for s in sim], "true_by_k": [s["true"] for s in sim],
                "window_by_k": window.tolist(), "grid_refs": refs}
        log.note(f"A5 in the real dynamics: proxy per sub-episode {[round(s['proxy'], 1) for s in sim]}, true "
                 f"{[round(s['true'], 1) for s in sim]}, P(window exploited) {np.round(window, 3).tolist()}")
    summary["refs"] = refs
    log.check("A5 hiding is optimal: windows 0-3 clean, final window exploited, never corrected",
              max(window[:-1]) < 0.05 and window[-1] > 0.5 and corrected < 0.05,
              f"windows {np.round(window, 3).tolist()}, corrections {corrected:.3f}")
    log.check("A5 the hiding optimum exploits off-window and beats honest play",
              refs["offwindow_rate"] > 0.1 and refs["proxy_0_3"] > gt_proxy,
              f"off-window exploit rate {refs['offwindow_rate']:.2f}; proxy per sub-episode 0-3 "
              f"{refs['proxy_0_3']:.1f} vs honest {gt_proxy:.1f} vs open exploiter {px_proxy:.1f}")
    # A4's load-bearing check, now that the hiding value is known: a correction must cost
    # more (per remaining sub-episode) than hiding does. Step 2's grid: 8,678 vs 1,000.
    r1 = rounds[0]
    px_grid = sub_value(tb, pol_px, tb.proxy, T)[0]
    cost_corr = px_grid - r1["best_value_rhat"]
    cost_hide = px_grid - av_proxy                    # best monitor-avoiding sub-episode under the proxy
    summary["a4_costs"] = {"correction": cost_corr, "hiding": cost_hide}
    log.check("A4 one correction costs more than hiding (per sub-episode: best value under the proxy vs under "
              "r_hat after one round, vs the idealised hide)", cost_corr > cost_hide,
              f"correction costs {cost_corr:.1f} ({cost_corr / px_grid:.0%} of {px_grid:.1f}); hiding costs "
              f"{cost_hide:.1f} ({cost_hide / px_grid:.0%})")
    log.note(f"A4 per-step: the exploit's transitions pay {r1['exploit_pay_per_step']:+.1f}/step under r_hat after one "
             f"round (Step 2's grid: -526/step)")
    hv = r1["honest_value_proxy"]
    log.finding(f"A4 collateral: after one correction the honest policy earns {r1['honest_value_rhat']:.1f} under "
                f"r_hat vs {hv:.1f} under the proxy ({(r1['honest_value_rhat'] - hv) / abs(hv):+.0%}); the best "
                f"sub-episode under r_hat earns {r1['best_value_rhat']:.1f} and exploits on "
                f"{r1['best_exploit_rate']:.0%} of steps; rounds 1-4 best value under r_hat: "
                f"{[round(r['best_value_rhat'], 1) for r in rounds]}.")
    with open(os.path.join(out_dir, "summary.json"), "w") as fh:
        json.dump(summary, fh, indent=1, default=float)
    log.note(f"wrote {out_dir}/summary.json and canonical_rewards.npz")
    log.summary()


if __name__ == "__main__":
    main()
