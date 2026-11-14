"""Step 4: is a PPO run a best response to the corrections its own play induces? (the paired check)

Why not the target's value. The self-consistent target (step4_targets.py) fits correction 1 on the
exact optimum's round-0 play; training fits it on PPO's. In Absent Supervisor and Tomato, PPO's
corrections pay 7-15% more than any of the target's six draws (2026-11-05: PPO's received return is
above every single-draw optimum of its target, 4-13 standard errors above V0), so the target is not a
ceiling for PPO and a value gap against it cannot say whether PPO is optimal. This check asks the
question directly, around PPO's own play:

  * read the trained policy as an exact table over (t, s, correction level, audit flag) and propagate
    it exactly (dp.evaluate_levels_probs): its audit behaviour and its state-action occupancy;
  * fit correction c as training does (src/step3/pbrr.py: Overseer): 19 rollouts of PPO's policy at
    level c-1 in the round where PPO most likely gets its c-th correction, against the run's own
    reference rollouts, D accumulated over the episode. If PPO (almost) never gets a c-th correction
    (probability < 0.05), fit it on the best policy at level c-1 that would be caught there
    (dp.solve_subepisode_caught, as the target does), so "seek one more correction" is an option;
    "never be corrected" (hiding) always is;
  * N overseer draws per level; the level DP on their mean tables is the best response, V_BR (exact:
    the policy cannot see the draw);
  * PPO's exact value on the same tables, V_PPO. gap = 1 - V_PPO / V_BR >= 0.
Both values are linear in the tables for a fixed policy, so every draw gives a paired difference and
the gap gets a standard error; the overseer's noise, which is 10-15% of a single draw's value on the
grid, largely cancels.

This is one policy-improvement step from PPO's own play: a run is epsilon-optimal only if no policy
beats it by more than epsilon against the overseer's response to the run's own behaviour. Like the
target, it does not search over odd behaviours in a caught round that would induce other corrections.
Pre-registered (docs/step4_optimal.md, 2026-11-05): CONVERGED iff gap <= 0.03.

    .venv/bin/python experiments/step4_br.py results/step4/<env>/optimal/<run> [...] [--finished-only]
    .venv/bin/python experiments/step4_br.py --missing results/step4/*/optimal/*/   (runs that need one)

Writes <run>/step4_br/seed<s>_ep<N>.json, N = the model's episode count (never overwritten).
"""

import argparse
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from step4_targets import end_state, game_key, sub_value  # noqa: E402
from src.pbrr_core import GConfig, boltzmann_label  # noqa: E402
from src.step3.dp import (evaluate_levels_probs, onehot_probs, solve_levels, solve_subepisode,  # noqa: E402
                          solve_subepisode_caught, table_policy_fn, value_from_occupancy)
from src.step3.pbrr import fit_correction_rows, g_table, policy_probs_fn, rollouts  # noqa: E402
from src.step3.protocol import Protocol, encode_obs  # noqa: E402
from src.step3.reference import build_reference  # noqa: E402
from src.step3.tasks import get_task  # noqa: E402

TOL_BR = 0.03          # pre-registered: within 3% of the best response
P_MIN = 0.05           # below this, PPO "never" gets the c-th correction: fit it on the counterfactual


def br_dir(run):
    return os.path.join(run, "step4_br")


def br_path(run, seed_name, n_ep):
    return os.path.join(br_dir(run), f"{seed_name}_ep{int(n_ep)}.json")


def ppo_probs_at(model, proto, phi_obs, n_levels, n_actions):
    """``probs_at`` for dp.evaluate_levels_probs: the trained policy at every (s, level, flag) of step t.
    Only the reachable entries are computed (levels <= k in round k; the flag only inside the window)."""
    state = model.policy.actor_state
    S, T = len(phi_obs), proto.t_sub

    def at(t):
        k = t // T
        flags = (0, 1) if proto.in_window(t) else (0,)
        combos = [(c, f) for c in range(min(k + 1, n_levels)) for f in flags]
        obs = encode_obs(proto, np.tile(phi_obs, (len(combos), 1)), t,
                         np.repeat([c for c, _ in combos], S), np.repeat([bool(f) for _, f in combos], S))
        p = np.clip(np.asarray(state.apply_fn(state.params, obs).probs_parameter(), float)[:, :n_actions], 0.0, None)
        p /= p.sum(axis=1, keepdims=True)
        out = np.full((S, n_levels, 2, n_actions), 1.0 / n_actions)
        for i, (c, f) in enumerate(combos):
            out[:, c, f] = p[i * S:(i + 1) * S]
        return out
    return at


def best_response(cfg, policy_fn, probs_at, n_draws=6, eps=0.05, log=print):
    """The paired check for one policy (``policy_fn`` samples it for the overseer's rollouts, ``probs_at``
    reads it exactly), in the game of ``cfg`` (a run's config.json). Returns a JSON-able dict."""
    seed = int(cfg["seed"])
    task = get_task(cfg["env"], **cfg["task"])
    proto = Protocol(**cfg["protocol"])
    pb, gcfg = cfg["pbrr"], GConfig(**cfg["g"])
    tb, T, W, K, A = task.tables, proto.t_sub, proto.window, proto.n_sub, task.n_actions
    ref, _ = build_reference(task, T, {**pb, "seed": pb["ref_seed"]})
    ref_trajs = rollouts(task.make_batch(pb["k"], seed=1000 + seed), ref, proto,
                         np.random.default_rng(1000 + seed))           # the run's own references
    t0 = time.time()
    ev_p = evaluate_levels_probs(tb, proto, np.stack([tb.proxy] * K), probs_at)   # behaviour + occupancy
    log(f"  policy read exactly ({time.time() - t0:.0f}s): windows {np.round(ev_p['window'], 2).tolist()}, "
        f"corrections {np.round(ev_p['corrected'], 2).tolist()}")
    wbl = np.asarray(ev_p["window_by_level"])
    Rbar, D, behaviour = [tb.proxy.copy()], [[] for _ in range(n_draws)], []
    rbar_d = np.zeros((n_draws, K, tb.n_states * A))                   # each draw's expected reward tables
    rbar_d[:, 0] = (tb.prob * tb.proxy).sum(axis=1)
    for c in range(1, K):
        w = wbl[:K - 1, c - 1]
        if w.max() >= P_MIN:                                           # PPO's own caught round
            k = int(w.argmax())
            fn = policy_fn
            behaviour.append({"correction": c, "from": "policy", "round": k, "p_caught": float(w[k])})
        else:                                                          # counterfactual: the best caught policy
            k = c - 1
            fn = table_policy_fn(solve_subepisode_caught(tb, Rbar[c - 1], T, W), A, eps)
            behaviour.append({"correction": c, "from": "best caught policy (counterfactual)", "round": k,
                              "p_caught_policy": float(w.max())})
        acc = np.zeros_like(tb.proxy)
        for d in range(n_draws):
            rng = np.random.default_rng([seed, d, c, 5])               # own stream (the targets use ..., 4)
            agent = rollouts(task.make_batch(pb["k"], seed=int(rng.integers(2 ** 31))), fn, proto, rng,
                             t0=k * T, n_corr=c - 1)
            D[d] = D[d] + [(a, r, boltzmann_label(a, r, rng, pb["beta"])) for a in agent for r in ref_trajs]
            params, _ = fit_correction_rows(D[d], task, gcfg, seed=int(rng.integers(2 ** 31)))
            Rd = tb.proxy + g_table(params, task)
            acc += Rd
            rbar_d[d, c] = (tb.prob * Rd).sum(axis=1)
        Rbar.append(acc / n_draws)
        log(f"  correction {c}: fitted on {behaviour[-1]['from']} in round {k} ({time.time() - t0:.0f}s)")
    R_lv = np.stack(Rbar)
    V, pol = solve_levels(tb, proto, R_lv)
    ev_b = evaluate_levels_probs(tb, proto, R_lv, onehot_probs(pol, A))
    V_br = float(tb.mu0 @ V[:, 0, 0])
    bonus_p = proto.update_bonus * np.asarray(ev_p["corrected"])       # the update bonus (protocol.py), per round
    bonus_b = proto.update_bonus * np.asarray(ev_b["corrected"])
    ppo_k = value_from_occupancy(tb, ev_p["occ"], R_lv) + bonus_p
    V_ppo = float(ppo_k.sum())
    vb_d = np.einsum("klr,dlr->d", ev_b["occ"], rbar_d) + bonus_b.sum()   # the BR policy, draw by draw
    vp_d = np.einsum("klr,dlr->d", ev_p["occ"], rbar_d) + bonus_p.sum()
    gap_d = (vb_d - vp_d) / V_br
    pol_gt = solve_subepisode(tb, tb.true, T)

    def summ(ev, received):
        return {"received_by_k": np.asarray(received).tolist(), "true_by_k": ev["true"].tolist(),
                "proxy_by_k": ev["proxy"].tolist(), "window_by_k": ev["window"].tolist(),
                "corrected_by_k": ev["corrected"].tolist(),
                "corrections_per_ep": float(np.sum(ev["corrected"][:K - 1])), "end_state": end_state(ev, K)}
    return {"game": game_key(cfg), "seed": seed, "n_draws": n_draws, "eps": eps, "behaviour": behaviour,
            "V_br": V_br, "V_policy": V_ppo, "gap": 1.0 - V_ppo / V_br,
            "gap_se": float(gap_d.std(ddof=1) / np.sqrt(n_draws)) if n_draws > 1 else None,
            "gap_by_draw": gap_d.tolist(), "converged": bool(1.0 - V_ppo / V_br <= TOL_BR),
            "best_response": summ(ev_b, ev_b["received"]), "policy": summ(ev_p, ppo_k),
            "after_one_correction": {"best": sub_value(tb, solve_subepisode(tb, R_lv[1], T), R_lv[1], T),
                                     "honest": sub_value(tb, pol_gt, R_lv[1], T),
                                     "honest_true": sub_value(tb, pol_gt, tb.true, T)},
            "seconds": time.time() - t0}


def check_seed(seed_dir, n_draws=6, eps=0.05, log=print):
    from sbx import PPO
    with open(os.path.join(seed_dir, "config.json")) as fh:
        cfg = json.load(fh)
    proto = Protocol(**cfg["protocol"])
    task = get_task(cfg["env"], **cfg["task"])
    model = PPO.load(os.path.join(seed_dir, "model.zip"), device="cpu")
    n_ep = int(model.num_timesteps // (int(cfg["n_envs"]) * proto.t_ep))
    res = best_response(cfg, policy_probs_fn(model, proto, task.n_actions),
                        ppo_probs_at(model, proto, task.tables.phi_obs, proto.n_sub, task.n_actions),
                        n_draws=n_draws, eps=eps, log=log)
    res.update({"episodes": n_ep, "finished": os.path.exists(os.path.join(seed_dir, "metrics.json"))})
    return n_ep, res


def seeds_of(run):
    return sorted(x for x in os.listdir(run) if x.startswith("seed") and "_nockpt_" not in x
                  and os.path.isdir(os.path.join(run, x)))


def missing(run):
    """Finished seeds of ``run`` without a check at their final episode count."""
    out = []
    for s in seeds_of(run):
        sd = os.path.join(run, s)
        if not os.path.exists(os.path.join(sd, "metrics.json")):
            continue
        with open(os.path.join(sd, "config.json")) as fh:
            n_ep = json.load(fh)["episodes"]
        if not os.path.exists(br_path(run, s, n_ep)):
            out.append(s)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--seeds", nargs="*", type=int)
    ap.add_argument("--draws", type=int, default=6)
    ap.add_argument("--eps", type=float, default=0.05, help="action noise of the counterfactual caught policy")
    ap.add_argument("--finished-only", action="store_true")
    ap.add_argument("--missing", action="store_true", help="print the runs with finished seeds lacking a check")
    args = ap.parse_args()
    if args.missing:
        for run in args.runs:
            if os.path.isdir(run) and missing(run.rstrip("/")):
                print(run.rstrip("/"))
        return
    for run in (r.rstrip("/") for r in args.runs):
        for s in seeds_of(run):
            sd = os.path.join(run, s)
            if args.seeds and int(s[4:]) not in args.seeds:
                continue
            if not os.path.exists(os.path.join(sd, "model.zip")):
                continue
            done = os.path.exists(os.path.join(sd, "metrics.json"))
            if args.finished_only and not done:
                continue
            if done:                                                   # a finished seed's episode count is known
                with open(os.path.join(sd, "config.json")) as fh:
                    if os.path.exists(br_path(run, s, json.load(fh)["episodes"])):
                        continue
            print(f"{run} {s}:", flush=True)
            n_ep, res = check_seed(sd, args.draws, args.eps, log=lambda m: print(m, flush=True))
            path = br_path(run, s, n_ep)
            os.makedirs(br_dir(run), exist_ok=True)
            if os.path.exists(path):
                print(f"  {path} exists: kept (never overwritten)")
                continue
            with open(path + ".tmp", "w") as fh:
                json.dump(res, fh, indent=1, default=float)
            os.replace(path + ".tmp", path)
            b, p = res["best_response"], res["policy"]
            print(f"  -> gap {res['gap']:+.4f} (s.e. {res['gap_se'] or float('nan'):.4f}) at episode {n_ep}: "
                  f"{'CONVERGED' if res['converged'] else 'not converged'}. Best response: {b['end_state']}, "
                  f"true {np.round(b['true_by_k'], 1).tolist()}; policy: {p['end_state']}, true "
                  f"{np.round(p['true_by_k'], 1).tolist()}", flush=True)


if __name__ == "__main__":
    main()
