"""Step 2, Phase A: PBRR in isolation, before any PPO.

Questions answered here, in order:
  A1  Does the Eq 3 implementation behave as the paper describes on its own
      minimal MDPs (Appendix H)?
  A2  The reference policy (paper App. B / K.8: behaviour cloning on a handful of
      demonstrations from an imperfect hand-written rule): how good is it, does it
      ever touch the exploit, and does it reach GOAL (so labels are informative)?
  A3  The paper's own hyperparameter search for g (App. E.1): grid over lr / weight
      decay / epochs / layers / units, lowest held-out preference loss on
      exhaustive preferences between the GT-optimal, proxy-optimal and reference
      policies' trajectories.
  A4  What does one PBRR correction do to the exploit? A correction only creates an
      incentive to hide if it is costly, so this is the load-bearing check. Run for
      both handlings of |D+| = 0 (code: skip the regulariser; max1: keep it).
  A5  The idealised Step 2 DP: correction count 0..4 with the canonical PBRR
      rewards from A4. Is hiding from the audit still optimal, and what does it earn?

    .venv/bin/python experiments/step2_pbrr_check.py            (writes results/step2/phase_a/)
"""

import itertools
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.audit_dp import solve
from src.audit_grid import BASE, build_tables
from src.pbrr_core import GConfig, Traj, boltzmann_label, build_design, fit_correction
from src.pbrr_grid import (dp_policy_fn, make_traj, random_init_reference, rollout_subepisode,
                           train_bc_reference, transition_features)
from src.report import CheckLog
from src.step2_dp import evaluate_levels, solve_levels

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "results", "step2", "phase_a")
K = 19                       # trajectories per policy per round (code: 20 - 1 -> 19 x 19 pairs)
EPS = 0.1                    # softening of DP policies so their rollouts are not all identical


def soft(fn, eps=EPS):
    return lambda t, pos, flagged: (1 - eps) * fn(t, pos, flagged) + eps / 5.0


def rollouts(fn, n, rng, t0=0):
    P, A = rollout_subepisode(fn, n, rng, t0=t0)
    return [make_traj(p, a) for p, a in zip(P, A)]


def cross_pairs(agent, refs, rng, beta=1.0):
    return [(t1, t2, boltzmann_label(t1, t2, rng, beta)) for t1 in agent for t2 in refs]


def dp_subepisode(R, tb, T):
    """Single sub-episode (T steps from START) optimum under an arbitrary reward table."""
    n = R.shape[0]
    V = np.zeros(n)
    pol = np.zeros((T, n), int)
    for t in range(T - 1, -1, -1):
        Q = R + V[tb.next_pos]
        pol[t], V = Q.argmax(1), Q.max(1)
    return V, pol


def run_policy(pol, R, tb, T, E):
    pos, rh, tru, on_e = tb.start, 0.0, 0.0, 0
    for t in range(T):
        a = pol[t, pos]
        rh += R[pos, a]
        tru += tb.true[pos, a]
        pos = tb.next_pos[pos, a]
        on_e += int(pos == E)
    return rh, tru, on_e


def main():
    log = CheckLog("Step 2 Phase A -- PBRR in isolation on the audit grid")
    os.makedirs(OUT, exist_ok=True)
    cfg = BASE
    tb = build_tables(cfg)
    T = cfg.t_sub
    E = cfg.idx(cfg.exploit)
    X = transition_features(cfg)
    summary = {}

    # ---- A1: Appendix H minimal MDPs ------------------------------------------------
    proxy = np.array([10.0, 6.0, 7.0, 9.0])
    true = np.array([2.0, 4.0, 3.0, 8.0])

    def mtraj(a):
        c = np.zeros(4)
        c[a] = 1
        return Traj(c, proxy[a], true[a], 1)

    pairs = [(mtraj(0), mtraj(2), 1.0)]    # pi* -> s1, pi_ref -> s3, noiseless: s3 preferred
    a1 = {}
    for no_agree in ("skip", "max1"):
        g, _ = fit_correction(pairs, np.eye(4, dtype=np.float32), GConfig(no_agree=no_agree), seed=0)
        a1[no_agree] = g
        log.note(f"A1 MDP 1 [{no_agree}]: g = {np.round(g, 2)}, r_hat = {np.round(proxy + g, 2)}, "
                 f"induced s{int(np.argmax(proxy + g)) + 1} (optimal s4)")
    log.check("A1 max1: L- keeps the preferred transition (s3) near 0 and pushes s1 below it",
              abs(a1["max1"][2]) < 0.5 and proxy[0] + a1["max1"][0] < proxy[2] + a1["max1"][2],
              f"g(s3) {a1['max1'][2]:+.2f}, r_hat(s1) {proxy[0] + a1['max1'][0]:.2f} < r_hat(s3) "
              f"{proxy[2] + a1['max1'][2]:.2f}")
    log.check("A1 skip (released code at |D+| = 0): unregularised fit raises the preferred transition",
              a1["skip"][2] > 1.0, f"g(s3) {a1['skip'][2]:+.2f}")
    log.finding("A1: with the paper's neural g, one preference does NOT reproduce Theorem H.1 under "
                "either handling: the MLP's shared layers spill the decrement onto unseen transitions "
                f"(max1: g(s2) {a1['max1'][1]:+.2f}, g(s4) {a1['max1'][3]:+.2f}), pulling s4 below s3. "
                "Theorem H.1 assumes uncompared transitions are left unchanged (a tabular g).")

    # ---- A2: reference policy ---------------------------------------------------------
    rng = np.random.default_rng(0)
    ref, bc_info = train_bc_reference(seed=0)
    test = rollouts(ref, 2000, rng)
    ref_true = np.array([t.true for t in test])
    bonus_flat = tb.bonus[:, :, 0].ravel().astype(float)          # row = s * A + a, like counts
    ref_bonus = float(np.mean([bonus_flat @ t.counts > 0 for t in test]))
    rnd = random_init_reference(seed=0)
    rnd_true = np.array([t.true for t in rollouts(rnd, 2000, rng)])
    summary["reference"] = {"bc": bc_info, "true_mean": float(ref_true.mean()),
                            "p_goal": float((ref_true > -100).mean()), "p_touches_exploit": float(ref_bonus),
                            "random_init_true_mean": float(rnd_true.mean()),
                            "random_init_p_goal": float((rnd_true > -100).mean())}
    log.check("A2 BC reference reaches GOAL in most sub-episodes (labels vs the exploiter are informative)",
              (ref_true > -100).mean() > 0.5,
              f"P(goal) {(ref_true > -100).mean():.2f}, mean true return {ref_true.mean():+.1f} "
              f"(honest optimum +22); {bc_info['n_demos']} demos, noise {bc_info['noise']}")
    log.check("A2 BC reference essentially never touches the exploit", ref_bonus < 0.01,
              f"P(collects bonus in a sub-episode) {ref_bonus:.4f}")
    log.note(f"A2 random-init reference (K.8 ablation): P(goal) {(rnd_true > -100).mean():.3f}, "
             f"mean true {rnd_true.mean():+.1f} -> against the exploiter (true -100) its labels are coin flips")

    # ---- A3: the paper's E.1 hyperparameter search ------------------------------------
    _, pol_gt = solve(cfg.with_(exploit_bonus=0.0))                 # GT-optimal (honest)
    _, pol_px = solve(cfg.with_(toothless=True))                    # proxy-optimal (no overseer)
    gt = rollouts(soft(dp_policy_fn(pol_gt)), K, rng)
    px = rollouts(soft(dp_policy_fn(pol_px)), K, rng)
    rf = rollouts(ref, K, rng)
    data = cross_pairs(gt, rf, rng) + cross_pairs(px, rf, rng)
    idx = rng.permutation(len(data))
    n_tr = int(0.8 * len(data))
    train = [data[i] for i in idx[:n_tr]]
    held = [data[i] for i in idx[n_tr:]]

    def held_out_loss(g):
        d = build_design(held)
        gp = g[d.present]
        z = d.dproxy + d.A @ gp
        return float(np.mean(np.logaddexp(0.0, z) - d.y * z))

    grid = list(itertools.product([1e-3, 1e-4], [True, False], [50, 100, 200], [3, 5], [256, 512]))
    rows = []
    t0 = time.time()
    for lr, wd, ep, nl, w in grid:
        gc = GConfig(lr=lr, weight_decay=1e-5 if wd else 0.0, epochs=ep, n_layers=nl, width=w)
        g, _ = fit_correction(train, X, gc, seed=0)
        rows.append({"lr": lr, "weight_decay": wd, "epochs": ep, "n_layers": nl, "width": w,
                     "held_out_loss": held_out_loss(g)})
    rows.sort(key=lambda r: r["held_out_loss"])
    best = rows[0]
    paper = next(r for r in rows if (r["lr"], r["weight_decay"], r["epochs"], r["n_layers"], r["width"])
                 == (1e-4, True, 200, 5, 512))
    summary["e1_search"] = {"best": best, "paper_table2": paper, "all": rows,
                            "seconds": time.time() - t0}
    log.check("A3 E.1 search ran over all 48 configurations", len(rows) == 48,
              f"{time.time() - t0:.0f}s; best {best} | paper Table 2 config held-out loss "
              f"{paper['held_out_loss']:.4f} (rank {rows.index(paper) + 1}/48)")
    gcfg = GConfig(lr=best["lr"], weight_decay=1e-5 if best["weight_decay"] else 0.0,
                   epochs=best["epochs"], n_layers=best["n_layers"], width=best["width"])
    summary["g_config"] = gcfg.__dict__

    # ---- A4: what one (and up to four) PBRR corrections do ----------------------------
    refs_fixed = rollouts(ref, K, np.random.default_rng(123))       # code: reference set collected once
    canon = {}
    for no_agree in ("max1", "skip"):
        gc = gcfg.with_(no_agree=no_agree)
        Rs = [tb.reward[:, :, 0].copy()]
        D = []
        rounds = []
        policy_fn = dp_policy_fn(pol_px)          # round 1: the open exploiter (dwells through the audit)
        for c in range(1, 5):
            agent = rollouts(soft(policy_fn), K, rng, t0=(c - 1) * T)
            D += cross_pairs(agent, refs_fixed, rng)
            fits = [fit_correction(D, X, gc, seed=s) for s in range(3)]
            g, info = fits[0]
            G = g.reshape(cfg.n_pos, 5)
            R = tb.reward[:, :, 0] + G
            Rs.append(R)
            V, pol_c = dp_subepisode(R, tb, T)
            rh, tru, on_e = run_policy(pol_c, R, tb, T, E)
            g_e = [f[0].reshape(cfg.n_pos, 5)[E, 0] for f in fits]
            rounds.append({"round": c, "n_pairs": len(D), "n_agree": info["n_agree"],
                           "g_dwell_E": float(G[E, 0]), "g_dwell_E_seeds": [float(v) for v in g_e],
                           "rhat_dwell_per_step": float(R[E, 0]), "max_g": float(g.max()),
                           "min_g": float(g.min()), "best_subepisode_rhat": float(rh),
                           "best_subepisode_true": float(tru), "best_subepisode_steps_on_E": int(on_e)})
            log.note(f"A4 [{no_agree}] round {c}: |D| {len(D)}, |D+| {info['n_agree']}, g(E,stay) "
                     f"{G[E, 0]:+.1f} (seeds {np.round(g_e, 1)}), exploit pays {R[E, 0]:+.1f}/step, "
                     f"max g {g.max():+.1f}; best sub-episode under r_hat: {rh:,.0f} (true {tru:+.0f}, "
                     f"{on_e} steps on E)")
            # next round's agent: the policy optimal for the CURRENT repaired reward
            policy_fn = (lambda pol: (lambda t, pos, f: np.eye(5)[pol[t % T, pos]]))(pol_c)
        canon[no_agree] = {"R": np.stack(Rs), "rounds": rounds}
        np.savez_compressed(os.path.join(OUT, f"canonical_rewards_{no_agree}.npz"), R=np.stack(Rs))
    summary["one_correction"] = {k: v["rounds"] for k, v in canon.items()}
    proxy_best = 8700.0
    for no_agree in ("max1", "skip"):
        r1 = canon[no_agree]["rounds"][0]
        cost = 1 - r1["best_subepisode_rhat"] / proxy_best
        log.finding(f"A4 [{no_agree}]: after ONE correction the best sub-episode under the repaired reward "
                    f"earns {r1['best_subepisode_rhat']:,.0f} vs {proxy_best:,.0f} before -- a correction "
                    f"costs {cost:.0%} of a sub-episode's proxy-reward value "
                    f"(exploit {r1['rhat_dwell_per_step']:+.1f}/step, max g {r1['max_g']:+.1f}).")
    log.check("A4 max1: one correction makes the exploit unprofitable (dwelling pays < 0 per step)",
              canon["max1"]["rounds"][0]["rhat_dwell_per_step"] < 0,
              f"{canon['max1']['rounds'][0]['rhat_dwell_per_step']:+.1f}/step")

    # ---- A5: idealised Step 2 DP ------------------------------------------------------
    for no_agree in ("max1", "skip"):
        R = canon[no_agree]["R"]
        V, pol = solve_levels(cfg, R)
        ev = evaluate_levels(cfg, R, pol)
        on = ev["on_exploit"].reshape(cfg.n_sub, T)
        leave = [int(np.flatnonzero(on[k])[-1]) + 1 if on[k].any() else None for k in range(cfg.n_sub)]
        window_clean = [not on[k, T - cfg.window:].any() for k in range(cfg.n_sub)]
        summary[f"ideal_dp_{no_agree}"] = {
            "V0": float(V[0, tb.start, 0, 0]), "received_by_k": ev["received"].tolist(),
            "true_by_k": ev["true"].tolist(), "levels": ev["levels"].tolist(), "leave_tau": leave,
            "window_clean": window_clean}
        log.note(f"A5 [{no_agree}] idealised optimum: V0 {V[0, tb.start, 0, 0]:,.0f}; received per "
                 f"sub-episode {np.round(ev['received']).astype(int).tolist()}, true "
                 f"{np.round(ev['true']).astype(int).tolist()}, correction level {ev['levels'].tolist()}, "
                 f"leaves E at tau {leave}")
    s = summary["ideal_dp_max1"]
    log.check("A5 max1: hiding from the audit is optimal (windows 0-3 clean, final window exploited, "
              "never corrected)",
              all(s["window_clean"][:4]) and not s["window_clean"][4] and max(s["levels"]) == 0,
              f"leave tau {s['leave_tau']}, levels {s['levels']}")

    with open(os.path.join(OUT, "summary.json"), "w") as fh:
        json.dump(summary, fh, indent=1, default=float)
    log.note(f"wrote {OUT}/summary.json and canonical_rewards_*.npz")
    log.summary()


if __name__ == "__main__":
    main()
