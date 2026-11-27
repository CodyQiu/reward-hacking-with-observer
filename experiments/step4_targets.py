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

With g.offset (the compensated correction, docs/step4_comp.md) each correction also installs a level per
draw: level_offset(V_before, V_ref_after), with V_before the caught policy's exact value in its caught
round under that draw's reward in force (dp.round_value, without the rollouts' action noise: the agent is
the deterministic optimum, and its own rollouts would carry no noise) and V_ref_after the run's reference
rollouts' mean under proxy + the draw's new g, as the overseer computes it in training. With
g.offset_rule=exact (exact indifference, docs/step4_indiff.md) the level instead rises by
[M(r_old) - M(r_new)] / T per draw (dp.best_round_value, levels excluded), as the overseer computes it.
With g.offset_rule=twin, each correction's level is priced by the overseer's own one-round optimiser at
convergence (the best round of the level's mean correction, valued under each draw): the theorem with random
corrections. With g.offset_rule=pool, M is estimated as in training from one pool of plays (``pool_level``); the agent's
final-round play is the previous iteration's optimum (iteration 0: reference and caught play only), and
the exact M is recorded beside the estimate (m_before / m_after) for the validation.

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
from src.step3.dp import (best_round_value, evaluate_levels, round_probs, round_value,  # noqa: E402
                          solve_levels, solve_subepisode, solve_subepisode_caught, table_policy_fn)
from src.step3.pbrr import (exact_level, fit_correction_rows, g_table, level_offset, unseen_override,  # noqa: E402
                            rollout_returns, rollouts)


def pool_level(tb, proto, task, ref_trajs, caught, finals, rb_old, rb_new, p_old, p_new):
    """The pool estimate of M before and after a correction (GConfig.offset_rule = "pool",
    docs/step4_indiff.md), exactly as the overseer forms it but with the agent's plays valued exactly:
    candidates = the reference rollouts (relabelled, as in training), the caught play ``caught`` = (probs_at,
    round) and the agent's final-round play ``finals`` = [(level, probs_at at round K-1)].
    rb_* are the expected reward tables (no level), p_* the corrections in force. Returns a dict."""
    K = proto.n_sub

    def vals(rb, params):
        v = [float(rollout_returns(ref_trajs, task, params).mean()), round_value(tb, proto, rb, *caught)]
        return np.array(v + [round_value(tb, proto, rb, pa, K - 1) for _, pa in finals])

    names = ["reference", "caught"] + [f"final lvl{c}" for c, _ in finals]
    vb, va = vals(rb_old, p_old), vals(rb_new, p_new)
    ib, ia = int(np.argmax(vb)), int(np.argmax(va))
    return {"m_hat_before": float(vb[ib]), "m_hat_after": float(va[ia]), "best_before": names[ib],
            "best_after": names[ia]}
from src.step3.protocol import EnsembleCorrection, MinCorrection, Protocol  # noqa: E402
from src.step3.reference import build_reference  # noqa: E402
from src.step3.tasks import get_task  # noqa: E402
from src.step3.train import ROOT, resolve_config  # noqa: E402

OUT = os.path.join(ROOT, "results", "step4")
KEY_FIELDS = ("env", "task", "protocol", "pbrr", "g")      # what defines the game (not PPO's knobs)


OFF = {"protocol": {"update_bonus": 0.0, "learn_exempt": False},
       "g": {"n_ensemble": 1, "reg_rows": "traj", "unseen": "none", "unseen_post": "none"}}   # fields added later, at their "off" value


def ensemble_draw(task, proto, pb, gcfg, ref_trajs, fn, rng, k, c, D_members, corr, d, G_in, m_prev, lvl_prev):
    """One draw of correction c under GConfig.offset_rule = "exact_mean", as the training overseer makes it
    (pbrr.Overseer._ensemble_round): ``n_ensemble`` fits, each on its own rollouts of ``fn`` in round k and its
    own labels (its own D, extended in place), applied as their mean (fines only: mean_i min(G_in, g_i)); the
    level rises by [M(r_old) - M(r_mean)] / T on exactly that mean. Updates corr[d], G_in[d], m_prev[d],
    lvl_prev[d]; returns the reward table without the level, and the level record."""
    tb, T = task.tables, proto.t_sub
    fits = []
    for i in range(gcfg.n_ensemble):
        agent = rollouts(task.make_batch(pb["k"], seed=int(rng.integers(2 ** 31))), fn, proto, rng,
                         t0=k * T, n_corr=c - 1)
        D_members[i] = D_members[i] + [(a, r, boltzmann_label(a, r, rng, pb["beta"])) for a in agent
                                       for r in ref_trajs]
        fits.append(fit_correction_rows(D_members[i], task, gcfg, seed=int(rng.integers(2 ** 31)))[0])
    Gs = np.stack([g_table(p, task) for p in fits])
    if gcfg.fine_only:
        Gs = np.minimum(G_in[d][None], Gs)
    G = Gs.mean(axis=0).astype(np.float32)
    if gcfg.fine_only:
        G_in[d] = G
    corr[d] = EnsembleCorrection(corr[d], fits, gcfg.fine_only)
    Rd = tb.proxy + G
    m_new = best_round_value(tb, Rd, T)
    rec = {"level": exact_level(lvl_prev[d], m_prev[d], m_new, T), "m_before": m_prev[d], "m_after": m_new}
    m_prev[d], lvl_prev[d] = m_new, rec["level"]
    return Rd, rec


def game_key(cfg):
    """What defines the game. A field added to the config later is left out at its "off" value, so the
    runs and targets written before it existed keep matching (protocol.update_bonus, 2026-11-13)."""
    key = {k: dict(cfg[k]) if isinstance(cfg[k], dict) else cfg[k] for k in KEY_FIELDS}
    for group, fields in OFF.items():
        for f, v in fields.items():
            if key[group].get(f, v) == v:
                key[group].pop(f, None)
            elif not isinstance(v, str):                    # string-valued fields (reg_rows, unseen) stay strings
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


def round_window(tb, pol, T, W):
    """P(a single sub-episode policy ``pol`` (T, S) exploits at least once in the last W steps), from mu0."""
    d = np.stack([tb.mu0, np.zeros(tb.n_states)], axis=1)              # (S, flag)
    for tau in range(T):
        r = np.arange(tb.n_states) * tb.n_actions + pol[tau]
        hit = tb.flag[r] & (tau >= T - W)                               # (S, F) caught there
        nd = np.zeros_like(d)
        for f in (0, 1):
            m = d[:, f][:, None] * tb.prob[r]
            to1 = m * hit if f == 0 else m
            nd[:, 1] += np.bincount(tb.nxt[r].ravel(), weights=to1.ravel(), minlength=tb.n_states)
            if f == 0:
                nd[:, 0] += np.bincount(tb.nxt[r].ravel(), weights=(m * ~hit).ravel(), minlength=tb.n_states)
        d = nd
    return float(d[:, 1].sum())


def best_rounds(tb, R_lv, T, W, proto=None):
    """Per correction level: the best single round under the mean reward in force -- whether it uses the bug
    in the audit window (then a correction there is under-correction, not farming; docs/step4_indiff.md A3)
    and its true and received return. With ``proto`` also the two tolerances an estimate of M must meet
    (docs/step4_indiff.md, "Estimating M"): ``received_caught``, the best round that is caught (so
    ``received - received_caught`` is what a deliberate correction costs), and ``received_avoid``, the best
    round that keeps the window clean (so ``received - received_avoid`` is what hiding costs a round)."""
    out = []
    for R in R_lv:
        pol = solve_subepisode(tb, R, T)
        rec = {"window": round_window(tb, pol, T, W), "true": sub_value(tb, pol, tb.true, T),
               "received": sub_value(tb, pol, R, T)}
        if proto is not None:
            rbar = (tb.prob * R).sum(axis=1)
            rec["received_caught"] = round_value(tb, proto, rbar, round_probs(solve_subepisode_caught(tb, R, T, W),
                                                                              tb.n_actions), 0)
            rec["received_avoid"] = sub_value(tb, solve_subepisode(tb, R, T, avoid_window=W), R, T)
        out.append(rec)
    return out


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
            "window_by_level": ev["window_by_level"].tolist(), "level_dist_by_k": ev["level_dist"].tolist(),
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
        # each draw's expected reward in force (offset only); rebound, never written in place
        rprev = [(tb.prob * tb.proxy).sum(axis=1)] * n_draws if gcfg.offset else None
        corr = [None] * n_draws                               # each draw's correction in force
        G_in = [np.zeros(tb.proxy.shape, np.float32) for _ in range(n_draws)] if gcfg.fine_only else None
        exact = gcfg.offset and gcfg.offset_rule == "exact"   # exact indifference (docs/step4_indiff.md)
        pool = gcfg.offset and gcfg.offset_rule == "pool"     # ... with M estimated from a pool of plays
        ens = gcfg.offset and gcfg.offset_rule == "exact_mean"   # ... priced on the mean of n fits per catch
        twin = gcfg.offset and gcfg.offset_rule == "twin"     # ... priced by the overseer's one-round optimiser
        if twin:   # the converged twin at the level before: the best round of the (deterministic) proxy
            pol_tw_prev, R_nl_prev = solve_subepisode(tb, tb.proxy, T), [tb.proxy] * n_draws
        if ens:                                               # each draw = one catch's n_ensemble fits
            D = [[[] for _ in range(gcfg.n_ensemble)] for _ in range(n_draws)]
        if exact or pool or ens or twin:                      # each draw's M (best round, no level) and level
            m_prev, lvl_prev = [best_round_value(tb, tb.proxy, T)] * n_draws, [0.0] * n_draws
        if pool:   # the reward tables in force (no level); the agent's final-round play: last iteration's optimum,
            # at the levels it reaches in the final round (training only ever stores those)
            rnl_prev = [(tb.prob * tb.proxy).sum(axis=1)] * n_draws
            finals = [] if pol is None else [(c, round_probs(pol, A, level=c)) for c in range(K)
                                             if ev["level_dist"][K - 1][c] >= 0.05]
        for c in range(1, K):
            w = None if ev is None else np.asarray(ev["window_by_level"])[:K - 1, c - 1]
            if w is not None and w.max() >= 0.05:            # the optimum's own caught round
                k = int(w.argmax())
                fn, exact_p = table_policy_fn(pol, A, eps), round_probs(pol, A, level=c - 1)
                behaviour.append({"correction": c, "from": "optimum", "round": k, "p_caught": float(w[k])})
            else:                                             # counterfactual: the best policy that is caught
                k = c - 1
                pol_c = solve_subepisode_caught(tb, Rbar[c - 1], T, W)
                fn, exact_p = table_policy_fn(pol_c, A, eps), round_probs(pol_c, A)
                behaviour.append({"correction": c, "from": "best caught policy (counterfactual)", "round": k})
            acc, lv, twin_R = np.zeros_like(tb.proxy), [], []
            for d in range(n_draws):
                rng = np.random.default_rng([seed, d, c, 4])    # common random numbers across iterations
                if ens:                                       # the average correction (GConfig "exact_mean")
                    Rd, rec_lv = ensemble_draw(task, proto, pb, gcfg, ref_trajs, fn, rng, k, c, D[d], corr, d,
                                               G_in, m_prev, lvl_prev)
                    lv.append(rec_lv)
                    Rd = Rd + rec_lv["level"]
                    acc += Rd
                    if per_draw:
                        draws[d].append(Rd.astype(np.float32))
                    continue
                agent = rollouts(task.make_batch(pb["k"], seed=int(rng.integers(2 ** 31))), fn, proto, rng,
                                 t0=k * T, n_corr=c - 1)
                D[d] = D[d] + [(a, r, boltzmann_label(a, r, rng, pb["beta"])) for a in agent for r in ref_trajs]
                params, _ = fit_correction_rows(D[d], task, gcfg, seed=int(rng.integers(2 ** 31)))
                corr_old = corr[d]
                if gcfg.fine_only:                               # fines only, never relaxed (min with the last)
                    G_in[d] = np.minimum(G_in[d], g_table(params, task)).astype(np.float32)
                    corr[d] = (corr[d] or MinCorrection(())).then(params)
                    Rd = tb.proxy + G_in[d]
                else:
                    corr[d] = params
                    gt = g_table(params, task)
                    if gcfg.unseen_post != "none":           # opt-in (docs/step4_goal_fixes.md)
                        gt = unseen_override(gt, params, D[d], task, gcfg.unseen_post)
                    Rd = tb.proxy + gt
                if twin:                                      # priced once every draw of this level is in
                    twin_R.append(Rd)
                    continue
                if exact:                                     # the exact-indifference level
                    m_new = best_round_value(tb, Rd, T)
                    lv.append({"level": exact_level(lvl_prev[d], m_prev[d], m_new, T), "m_before": m_prev[d],
                               "m_after": m_new})
                    m_prev[d], lvl_prev[d] = m_new, lv[-1]["level"]
                    Rd = Rd + lv[-1]["level"]
                elif pool:                                    # the same rule, M estimated from the pool
                    m_new, rb_new = best_round_value(tb, Rd, T), (tb.prob * Rd).sum(axis=1)
                    est = pool_level(tb, proto, task, ref_trajs, (exact_p, k), finals, rnl_prev[d], rb_new,
                                     corr_old, corr[d])
                    lv.append({"level": exact_level(lvl_prev[d], est["m_hat_before"], est["m_hat_after"], T),
                               "m_before": m_prev[d], "m_after": m_new, **est})
                    m_prev[d], lvl_prev[d], rnl_prev[d] = m_new, lv[-1]["level"], rb_new
                    Rd = Rd + lv[-1]["level"]
                elif gcfg.offset:                             # the compensated correction's level
                    v_before = round_value(tb, proto, rprev[d], exact_p, k)
                    v_ref = float(rollout_returns(ref_trajs, task, corr[d]).mean())
                    lv.append({"level": level_offset(gcfg, v_before, v_ref, T), "v_before": v_before,
                               "v_ref_after": v_ref})
                    Rd = Rd + lv[-1]["level"]
                    rprev[d] = (tb.prob * Rd).sum(axis=1)
                acc += Rd
                if per_draw:
                    draws[d].append(Rd.astype(np.float32))
            if twin:   # the twin at convergence: the best round of this level's mean correction (it cannot see the
                # draw), valued under each draw's own correction; so is the twin of the level before
                pol_tw = solve_subepisode(tb, np.mean(twin_R, axis=0), T)
                for d, Rd in enumerate(twin_R):
                    v_before, v_after = sub_value(tb, pol_tw_prev, R_nl_prev[d], T), sub_value(tb, pol_tw, Rd, T)
                    lv.append({"level": exact_level(lvl_prev[d], v_before, v_after, T), "m_before": v_before,
                               "m_after": v_after, "m_exact_after": best_round_value(tb, Rd, T)})
                    lvl_prev[d], R_nl_prev[d] = lv[-1]["level"], Rd
                    Rd = Rd + lv[-1]["level"]
                    acc += Rd
                    if per_draw:
                        draws[d].append(Rd.astype(np.float32))
                pol_tw_prev = pol_tw
            if lv:
                behaviour[-1]["level"] = {key: [x[key] for x in lv] for key in lv[0]}
            Rbar.append(acc / n_draws)
            if exact or pool or ens or twin:  # the policy cannot see the draw: the best round of the mean table
                mean_lvl = float(np.mean(behaviour[-1]["level"]["level"]))
                behaviour[-1]["level"]["m_after_mean_table"] = best_round_value(tb, Rbar[-1] - mean_lvl, T)
        R_lv = np.stack(Rbar)
        V0, pol = solve_levels(tb, proto, R_lv)
        ev = evaluate_levels(tb, proto, R_lv, pol)
        rec = {"iteration": it, "behaviour": behaviour,
               **summarise(ev, float(tb.mu0 @ V0[:, 0, 0]), K, T), "seconds": time.time() - t_it}
        pol_1 = solve_subepisode(tb, R_lv[1], T)
        rec["best_after_one_correction"] = sub_value(tb, pol_1, R_lv[1], T)
        rec["best_after_one_correction_true"] = sub_value(tb, pol_1, tb.true, T)
        rec["honest_after_one_correction"] = sub_value(tb, pol_gt, R_lv[1], T)
        rec["exploit_after_one_correction"] = sub_value(tb, pol_px, R_lv[1], T)
        rec["best_round_by_level"] = best_rounds(tb, R_lv, T, W, proto)
        if proto.learn_exempt:    # the outcome audit's "still learning" bar, which the exact DP leaves out (src/step3/goal.py)
            from src.step3.goal import exemption_check, ref_table_value
            rec["exemption_by_level"] = [
                exemption_check(ref_table_value(task, ref_trajs, R_lv[c]), b["received_avoid"], b["received_caught"])
                for c, b in enumerate(rec["best_round_by_level"])]
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
