"""Step 4: the exact optimum a PPO run must reach -- self-consistent with its own corrections.

Phase A's A5 optimum (experiments/step3_check.py) fixes the corrections in advance: correction 1
is fitted on a softened open exploiter, correction c+1 on the single-sub-episode optimum under
correction c, from one random draw. PPO plays a different game: each correction is fitted on the
rollouts of *its own* policy in the round where it was caught (src/step3/pbrr.py: Overseer), with
fresh random draws every time. A PPO run already earns more received reward than the A5 optimum
(Tomato and Absent Supervisor, no regulariser), so A5 is not a ceiling for it.

The target here is a fixed point of "behaviour -> corrections -> optimal behaviour":
  * correction c is fitted, as in training, on K rollouts of the policy at correction level c-1 in
    the round where the current optimum gets its c-th correction, against the run's own reference
    rollouts (seed 1000 + seed), with D accumulated over the episode; if the optimum never reaches
    a c-th correction, on the best policy at level c-1 that *would* be caught there
    (dp.solve_subepisode_caught) -- the alternative that "not seeking it" must beat;
  * N independent overseer draws (rollouts, Boltzmann labels, fit seed) per level; the policy does
    not observe the draw, so the optimum against the random corrections is exactly the optimum
    against their mean tables (rewards enter linearly, transitions do not depend on g);
  * solve the level DP on the mean tables, evaluate it exactly, and iterate until its correction
    pattern stops changing.
It ignores one thing PPO could in principle exploit: choosing an odd behaviour in a caught round to
shape the correction it gets. A run whose received return clearly exceeds the target's V0 is doing
something outside this model (step4_converge.py flags it).

Also reported: the value of never being corrected (hiding) and the margin by which the target beats
it, and each single draw's own optimum (how robust the end state is to the overseer's randomness).

    .venv/bin/python experiments/step4_targets.py --env absent_supervisor --name P2swap_ep1000 \
        --seeds 0 1 2 --set ppo.ent_coef=0.1 g.l_minus_on=dispreferred g.epochs=1000

--set takes the PPO run's own overrides (only task / protocol / pbrr / g matter). Writes
results/step4/<env>/targets/<name>/seed<s>.json; refuses to overwrite.
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
from src.pbrr_core import GConfig, boltzmann_label  # noqa: E402
from src.step3.dp import (evaluate_levels, solve_levels, solve_subepisode,  # noqa: E402
                          solve_subepisode_caught, table_policy_fn)
from src.step3.pbrr import fit_correction_rows, g_table, rollouts  # noqa: E402
from src.step3.protocol import Protocol  # noqa: E402
from src.step3.reference import build_reference  # noqa: E402
from src.step3.tasks import get_task  # noqa: E402
from src.step3.train import ROOT, resolve_config  # noqa: E402

OUT = os.path.join(ROOT, "results", "step4")
KEY_FIELDS = ("env", "task", "protocol", "pbrr", "g")      # what defines the game (not PPO's knobs)


OFF = {"protocol": {"update_bonus": 0.0}}                   # fields added later, at their "off" value


def game_key(cfg):
    """What defines the game. A field added to the config later is left out at its "off" value, so the
    runs and targets written before it existed keep matching (protocol.update_bonus, 2026-11-13)."""
    key = {k: dict(cfg[k]) if isinstance(cfg[k], dict) else cfg[k] for k in KEY_FIELDS}
    for group, fields in OFF.items():
        for f, v in fields.items():
            if key[group].get(f, v) == v:
                key[group].pop(f, None)
            else:
                key[group][f] = float(key[group][f])        # "=1" and "=1.0" are the same game
    return key


def sub_value(tb, pol, R, T):
    d, tot = tb.mu0.copy(), 0.0
    for tau in range(T):
        r = np.arange(tb.n_states) * tb.n_actions + pol[tau]
        m = d[:, None] * tb.prob[r]
        tot += (m * R[r]).sum()
        d = np.bincount(tb.nxt[r].ravel(), weights=m.ravel(), minlength=tb.n_states)
    return float(tot)


def end_state(ev, K):
    corr = np.asarray(ev["corrected"][:K - 1])
    n = float(corr.sum())
    if n < 0.1:
        return "hides" if ev["window"][K - 1] > 0.5 else "never exploits in view"
    if corr[0] > 0.9 and corr[1:].sum() < 0.1:
        return "corrected in round 0, then never again"
    return f"{n:.2f} corrections per episode (by round {np.round(corr, 2).tolist()})"


def summarise(ev, V0, K, T):
    return {"V0": V0, "received_by_k": ev["received"].tolist(), "proxy_by_k": ev["proxy"].tolist(),
            "true_by_k": ev["true"].tolist(), "window_by_k": ev["window"].tolist(),
            "corrected_by_k": ev["corrected"].tolist(),
            "corrections_per_ep": float(np.sum(ev["corrected"][:K - 1])),
            "window_by_level": ev["window_by_level"].tolist(),
            "exploit_by_tau": np.asarray(ev["exploit_t"]).reshape(K, T).tolist(),
            "end_state": end_state(ev, K)}


def target(cfg, n_draws=6, max_iter=5, eps=0.05, per_draw=True, log=print):
    seed = int(cfg["seed"])
    task = get_task(cfg["env"], **cfg["task"])
    proto = Protocol(**cfg["protocol"])
    pb, gcfg = cfg["pbrr"], GConfig(**cfg["g"])
    tb, T, W, K, A = task.tables, proto.t_sub, proto.window, proto.n_sub, task.n_actions
    ref, _ = build_reference(task, T, {**pb, "seed": pb["ref_seed"]})
    ref_trajs = rollouts(task.make_batch(pb["k"], seed=1000 + seed), ref, proto,
                         np.random.default_rng(1000 + seed))           # the run's own references
    pol_gt = solve_subepisode(tb, tb.true, T)
    pol_px = solve_subepisode(tb, tb.proxy, T)
    pol_av = solve_subepisode(tb, tb.proxy, T, avoid_window=W)
    a1 = {"honest_true": sub_value(tb, pol_gt, tb.true, T), "honest_proxy": sub_value(tb, pol_gt, tb.proxy, T),
          "proxy_opt_proxy": sub_value(tb, pol_px, tb.proxy, T), "proxy_opt_true": sub_value(tb, pol_px, tb.true, T),
          "hide_proxy": sub_value(tb, pol_av, tb.proxy, T)}
    # never corrected: being caught is made ruinous, so the optimum avoids it (the hiding value)
    R_hide = np.stack([tb.proxy] + [tb.proxy - 1e6] * (K - 1))
    V_hide = float(tb.mu0 @ solve_levels(tb, proto, R_hide)[0][:, 0, 0])

    pol, ev, prev_sig, iters = None, None, None, []
    for it in range(max_iter):
        t_it = time.time()
        Rbar, D, draws, behaviour = [tb.proxy.copy()], [[] for _ in range(n_draws)], [[] for _ in range(n_draws)], []
        for c in range(1, K):
            w = None if ev is None else np.asarray(ev["window_by_level"])[:K - 1, c - 1]
            if w is not None and w.max() >= 0.05:            # the optimum's own caught round
                k = int(w.argmax())
                fn = table_policy_fn(pol, A, eps)
                behaviour.append({"correction": c, "from": "optimum", "round": k, "p_caught": float(w[k])})
            else:                                             # counterfactual: the best policy that is caught
                k = c - 1
                fn = table_policy_fn(solve_subepisode_caught(tb, Rbar[c - 1], T, W), A, eps)
                behaviour.append({"correction": c, "from": "best caught policy (counterfactual)", "round": k})
            acc = np.zeros_like(tb.proxy)
            for d in range(n_draws):
                rng = np.random.default_rng([seed, d, c, 4])    # common random numbers across iterations
                agent = rollouts(task.make_batch(pb["k"], seed=int(rng.integers(2 ** 31))), fn, proto, rng,
                                 t0=k * T, n_corr=c - 1)
                D[d] = D[d] + [(a, r, boltzmann_label(a, r, rng, pb["beta"])) for a in agent for r in ref_trajs]
                params, _ = fit_correction_rows(D[d], task, gcfg, seed=int(rng.integers(2 ** 31)))
                Rd = tb.proxy + g_table(params, task)
                acc += Rd
                if per_draw:
                    draws[d].append(Rd.astype(np.float32))
            Rbar.append(acc / n_draws)
        R_lv = np.stack(Rbar)
        V0, pol = solve_levels(tb, proto, R_lv)
        ev = evaluate_levels(tb, proto, R_lv, pol)
        rec = {"iteration": it, "behaviour": behaviour,
               **summarise(ev, float(tb.mu0 @ V0[:, 0, 0]), K, T), "seconds": time.time() - t_it}
        rec["best_after_one_correction"] = sub_value(tb, solve_subepisode(tb, R_lv[1], T), R_lv[1], T)
        rec["honest_after_one_correction"] = sub_value(tb, pol_gt, R_lv[1], T)
        rec["exploit_after_one_correction"] = sub_value(tb, pol_px, R_lv[1], T)
        iters.append(rec)
        log(f"  iteration {it}: {rec['end_state']}; V0 {rec['V0']:.1f} (hide {V_hide:.1f}); true by k "
            f"{np.round(rec['true_by_k'], 1).tolist()}; windows {np.round(rec['window_by_k'], 2).tolist()} "
            f"({rec['seconds']:.0f}s)")
        sig = np.round(np.asarray(ev["window_by_level"]), 2)
        if prev_sig is not None and np.allclose(sig, prev_sig, atol=0.02):
            break
        prev_sig = sig
    converged = len(iters) >= 2 and np.allclose(np.round(np.asarray(iters[-1]["window_by_level"]), 2),
                                                np.round(np.asarray(iters[-2]["window_by_level"]), 2), atol=0.02)
    out = {"game": game_key(cfg), "seed": seed, "n_draws": n_draws, "eps": eps, "a1": a1,
           "V_hide": V_hide, "target": iters[-1], "margin_over_hiding": iters[-1]["V0"] - V_hide,
           "fixed_point_converged": bool(converged), "iterations": iters}
    if per_draw:                                              # each draw's own optimum (robustness)
        out["per_draw"] = []
        for d in range(n_draws):
            R_d = np.stack([tb.proxy] + [x.astype(float) for x in draws[d]])
            V_d, pol_d = solve_levels(tb, proto, R_d)
            ev_d = evaluate_levels(tb, proto, R_d, pol_d)
            out["per_draw"].append({"V0": float(tb.mu0 @ V_d[:, 0, 0]), "end_state": end_state(ev_d, K),
                                    "true_by_k": ev_d["true"].tolist(), "corrected_by_k": ev_d["corrected"].tolist()})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", required=True)
    ap.add_argument("--name", required=True, help="the variant label, e.g. P2swap_ep1000")
    ap.add_argument("--seeds", nargs="+", type=int, required=True)
    ap.add_argument("--set", nargs="*", default=[], help="the PPO run's overrides (task / protocol / pbrr / g)")
    ap.add_argument("--draws", type=int, default=6)
    ap.add_argument("--max-iter", type=int, default=5)
    ap.add_argument("--eps", type=float, default=0.05, help="action noise of the caught policy's rollouts")
    args = ap.parse_args()
    ov = parse_sets(args.set)
    out_dir = os.path.join(OUT, args.env, "targets", args.name)
    os.makedirs(out_dir, exist_ok=True)
    for s in args.seeds:
        path = os.path.join(out_dir, f"seed{s}.json")
        if os.path.exists(path):
            print(f"{path} exists: skipped (never overwritten)")
            continue
        cfg = resolve_config(args.env, {**ov, "seed": s})
        print(f"{args.env} {args.name} seed {s}:", flush=True)
        t0 = time.time()
        res = target(cfg, n_draws=args.draws, max_iter=args.max_iter, eps=args.eps,
                     log=lambda m: print(m, flush=True))
        res.update({"name": args.name, "overrides": ov, "seconds": time.time() - t0})
        with open(path + ".tmp", "w") as fh:
            json.dump(res, fh, indent=1, default=float)
        os.replace(path + ".tmp", path)
        t = res["target"]
        print(f"  -> {t['end_state']}; V0 {t['V0']:.1f}, hide {res['V_hide']:.1f}, margin "
              f"{res['margin_over_hiding']:+.1f}; fixed point {'converged' if res['fixed_point_converged'] else 'NOT converged'}"
              f"; per draw: {[p['end_state'] for p in res.get('per_draw', [])]}", flush=True)


if __name__ == "__main__":
    main()
