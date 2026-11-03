"""Step 4, Phase A: PBRR variants that should make a correction pay, before any PPO.

Variants (one GConfig change each from Step 2's max1 PBRR):
  base               the paper (L- on the preferred trajectory, L+ on)    -- control: hides
  P1-skip            released code's |D+| = 0 handling (no regulariser in round 1)
  P1-eq1             no regulariser at all (Eq 1)
  P2-swap            the mentor's swap: L- on the DISPREFERRED trajectory
  P2-swap-noLplus    the swap without L+
  P2-floor           the swap with g >= 0: the network fitted as usual, then clipped
                     at 0 (the tabular fit uses the bound g >= 0)
  P2-floor-noLplus   the swap with the floor, without L+
  P2-softplus        the swap with g = softplus(MLP) during the fit (diagnostic)

For each variant, two sequences of corrections (who is caught at level k):
  a4         Step 2's A4 recipe: the level-k rollouts come from the policy optimal
             for one sub-episode under r_hat_{k-1} (level 1: the open exploiter)
  exploiter  the open exploiter at every level (most D- pairs: worst case for a raise)
and two fits of g: the paper's network (3 seeds; seed 0 is the canonical one) and the
exact tabular fit (uncompared transitions keep g = 0; a small ridge picks the minimal
change). Every variant sees the same rollouts and labels at level 1 (common random
numbers).

Per level: monotonicity (min g over all transitions, against the proxy; min of
r_hat_k - r_hat_{k-1}), what dwelling on E pays, the best sub-episode under r_hat_k
(value, true return, steps on E) and its overshoot over the proxy's best (8,700).
Then the idealised level DP (src/step2_dp.py) gives the optimum and its end state.

    .venv/bin/python experiments/step4_check.py [--run-id phase_a] [--quick]
"""

import argparse
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from experiments.step2_pbrr_check import K, cross_pairs, dp_subepisode, rollouts, run_policy, soft
from src.audit_dp import solve
from src.audit_grid import BASE, build_tables
from src.pbrr_core import GConfig, fit_correction, fit_correction_tabular
from src.pbrr_grid import dp_policy_fn, train_bc_reference, transition_features
from src.report import CheckLog
from src.step2_dp import evaluate_levels, solve_levels

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PHASE_A2 = os.path.join(ROOT, "results", "step2", "phase_a", "summary.json")
OUT = os.path.join(ROOT, "results", "step4")
PROXY_BEST = 8700.0          # best sub-episode under the uncorrected proxy (dwell all 100 steps)
HONEST_TRUE = 22.0
RIDGE = 1e-3

VARIANTS = {
    "base": {},
    "P1-skip": {"no_agree": "skip"},
    "P1-eq1": {"use_regularization": False},
    "P2-swap": {"l_minus_on": "dispreferred"},
    "P2-swap-noLplus": {"l_minus_on": "dispreferred", "l_plus": False},
    "P2-floor": {"l_minus_on": "dispreferred", "g_floor": "clip"},
    "P2-floor-noLplus": {"l_minus_on": "dispreferred", "l_plus": False, "g_floor": "clip"},
    "P2-softplus": {"l_minus_on": "dispreferred", "g_floor": "softplus"},
}
SEQUENCES = ("a4", "exploiter")


def end_state(ev, cfg):
    """O-label of an idealised optimum's single deterministic episode."""
    T, W = cfg.t_sub, cfg.window
    on = ev["on_exploit"].reshape(cfg.n_sub, T)
    lv = ev["levels"]
    n_corr = int(lv[-1])
    caught_at = [k for k in range(cfg.n_sub - 1) if lv[k + 1] > lv[k]]
    # a round "exploits" iff its true return is below honest play's (an honest path may
    # cross E once: E costs no detour on the open grid)
    exploits = np.asarray(ev["true"]) < HONEST_TRUE - 0.5
    if n_corr == 0:
        label = "O0 hides" if exploits[:cfg.n_sub - 1].any() else "O1/O4 no exploit while correctable"
    elif not exploits[caught_at[0] + 1:].any():
        label = f"O3 corrected in round {caught_at[0]}, then honest"
    elif n_corr == 1:
        label = f"corrected in round {caught_at[0]}, keeps exploiting unseen"
    else:
        label = f"seeks corrections: caught after rounds {caught_at}, keeps exploiting"
    return {"label": label, "n_corrections": n_corr, "caught_after_rounds": caught_at,
            "levels": lv.tolist(), "received_by_k": ev["received"].tolist(), "true_by_k": ev["true"].tolist(),
            "steps_on_E_by_k": on.sum(1).tolist(), "window_on_E_by_k": on[:, T - W:].sum(1).tolist()}


def level_stats(R, R_prev, G, present, tb, T, E):
    V, pol = dp_subepisode(R, tb, T)
    rh, tru, on_e = run_policy(pol, R, tb, T, E)
    g = G.ravel()
    unseen = np.ones(g.size, bool)
    unseen[present] = False
    return {"min_g": float(g.min()), "max_g": float(g.max()),
            "min_g_present": float(g[present].min()),
            "min_g_unseen": float(g[unseen].min()) if unseen.any() else None,
            "n_negative_g": int((g < -1e-6).sum()),
            "min_step_change": float((R - R_prev).min()),
            "n_step_decreases": int(((R - R_prev) < -1e-6).sum()),
            "g_dwell_E": float(G[E, 0]), "rhat_dwell_E": float(R[E, 0]),
            "best_subepisode_rhat": float(rh), "best_subepisode_true": float(tru),
            "best_subepisode_steps_on_E": int(on_e), "overshoot": float(rh - PROXY_BEST)}


def run_sequence(gc, seq, refs, pol_px, X, tb, cfg, n_seeds, seed_base):
    """Fit levels 1..4. Returns {fit: {"R": (5, P, A), "levels": [...]}} for fit in
    neural (seed 0 canonical, others summarised) and tabular."""
    T, E = cfg.t_sub, cfg.idx(cfg.exploit)
    out = {}
    for fit in ("neural", "tabular"):
        rng_f = np.random.default_rng(seed_base)         # same data for both fits
        Rs = [tb.reward[:, :, 0].copy()]
        D, levels = [], []
        policy_fn = dp_policy_fn(pol_px)
        for c in range(1, cfg.n_sub):
            agent = rollouts(soft(policy_fn), K, rng_f, t0=(c - 1) * T)
            D += cross_pairs(agent, refs, rng_f)
            present = np.flatnonzero(np.any([t.counts > 0 for p in D for t in p[:2]], axis=0))
            if fit == "neural":
                fits = [fit_correction(D, X, gc, seed=s) for s in range(n_seeds)]
                g, info = fits[0]
                extra = {"g_dwell_E_seeds": [float(f[0].reshape(cfg.n_pos, 5)[E, 0]) for f in fits],
                         "min_g_seeds": [float(f[0].min()) for f in fits],
                         "max_g_seeds": [float(f[0].max()) for f in fits]}
            else:
                g, info = fit_correction_tabular(D, X.shape[0], gc, ridge=RIDGE)
                extra = {"converged": info["converged"]}
            G = g.reshape(cfg.n_pos, 5)
            R = tb.reward[:, :, 0] + G
            st = level_stats(R, Rs[-1], G, present, tb, T, E)
            st.update({"level": c, "n_pairs": len(D), "n_agree": info["n_agree"], **extra})
            levels.append(st)
            Rs.append(R)
            if seq == "a4":
                _, pol_c = dp_subepisode(R, tb, T)
                policy_fn = (lambda pol: (lambda t, pos, f: np.eye(5)[pol[t % T, pos]]))(pol_c)
        out[fit] = {"R": np.stack(Rs), "levels": levels}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default="phase_a")
    ap.add_argument("--quick", action="store_true", help="1 neural seed, a4 sequence only")
    args = ap.parse_args()
    out_dir = os.path.join(OUT, args.run_id)
    if os.path.exists(out_dir):
        raise FileExistsError(f"{out_dir} exists; runs are never overwritten -- pick a new --run-id")
    os.makedirs(out_dir)

    log = CheckLog("Step 4 Phase A -- PBRR variants that should make a correction pay")
    cfg = BASE
    tb = build_tables(cfg)
    X = transition_features(cfg)
    with open(PHASE_A2) as fh:
        g_base = {**json.load(fh)["g_config"], "no_agree": "max1"}
    ref, _ = train_bc_reference(seed=0)
    refs = rollouts(ref, K, np.random.default_rng(123))      # reference set collected once (as Step 2)
    _, pol_px = solve(cfg.with_(toothless=True))            # the open exploiter
    n_seeds = 1 if args.quick else 3
    seqs = ("a4",) if args.quick else SEQUENCES

    summary = {"g_base": g_base, "ridge": RIDGE, "n_seeds": n_seeds, "variants": {}}
    t0 = time.time()
    for name, kw in VARIANTS.items():
        gc = GConfig(**{**g_base, **kw})
        summary["variants"][name] = {"gconfig": kw}
        for si, seq in enumerate(seqs):
            res = run_sequence(gc, seq, refs, pol_px, X, tb, cfg, n_seeds, seed_base=1000 + si)
            for fit, r in res.items():
                V, pol = solve_levels(cfg, r["R"])
                es = end_state(evaluate_levels(cfg, r["R"], pol), cfg)
                es["V0"] = float(V[0, tb.start, 0, 0])
                key = f"{seq}/{fit}"
                summary["variants"][name][key] = {"levels": r["levels"], "optimum": es}
                np.savez_compressed(os.path.join(out_dir, f"R_{name}_{seq}_{fit}.npz"), R=r["R"])
                lv = r["levels"]
                log.note(f"{name:17s} {key:17s} min g by level {[round(l['min_g'], 1) for l in lv]}, "
                         f"min step change {[round(l['min_step_change'], 1) for l in lv]}, "
                         f"E pays {[round(l['rhat_dwell_E'], 1) for l in lv]}/step, "
                         f"best round {[round(l['best_subepisode_rhat']) for l in lv]} "
                         f"(true {[round(l['best_subepisode_true']) for l in lv]}) "
                         f"-> {es['label']}; received {np.round(es['received_by_k']).astype(int).tolist()}, "
                         f"true {np.round(es['true_by_k']).astype(int).tolist()}")
        log.note(f"  ({time.time() - t0:.0f}s so far)")

    V = summary["variants"]
    base = V["base"]["a4/neural"]["optimum"]
    log.check("base (Step 2 max1) still hides: never corrected, windows 0-3 clean, final window exploited",
              base["label"] == "O0 hides" and base["window_on_E_by_k"][4] > 0
              and not any(base["window_on_E_by_k"][:4]),
              f"V0 {base['V0']:,.0f}, received {np.round(base['received_by_k']).astype(int).tolist()}")
    skip = V["P1-skip"]["a4/neural"]["optimum"]
    log.check("P1-skip reproduces Step 2: caught in round 0 on purpose", skip["caught_after_rounds"][:1] == [0],
              f"{skip['label']}, received {np.round(skip['received_by_k']).astype(int).tolist()}")
    for name in ("P2-floor", "P2-floor-noLplus", "P2-softplus"):
        mins = [l["min_g"] for k, v in V[name].items() if "/" in k for l in v["levels"]]
        log.check(f"{name}: g >= 0 on every transition at every level", min(mins) >= 0.0,
                  f"min g {min(mins):.4f}")
    for name in ("P2-swap", "P2-swap-noLplus"):
        for key in [k for k in V[name] if "/" in k]:
            lv = V[name][key]["levels"]
            log.finding(f"{name} [{key}]: monotone vs proxy? min g {min(l['min_g'] for l in lv):+.2f} "
                        f"({max(l['n_negative_g'] for l in lv)} transitions < 0; present-only min "
                        f"{min(l['min_g_present'] for l in lv):+.2f}); monotone across levels? min step "
                        f"change {min(l['min_step_change'] for l in lv):+.2f}; overshoot by level "
                        f"{[round(l['overshoot']) for l in lv]}; optimum: {V[name][key]['optimum']['label']}")

    with open(os.path.join(out_dir, "summary.json"), "w") as fh:
        json.dump(summary, fh, indent=1, default=float)
    log.note(f"wrote {out_dir}/summary.json and R_*.npz ({time.time() - t0:.0f}s)")
    log.summary()


if __name__ == "__main__":
    main()
