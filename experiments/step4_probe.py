"""Step 4: is a PPO run short of the optimum of the reward it was actually given?

For a trained run on an exactly solvable Step 3 task (seed directory under
results/step4/<env>/ppo/), replay the first correction the way training does it:
the final policy plays round 0 (t0 = 0, no correction) in 19 copies, the 19 x 19
pairs against the run's own reference rollouts get Boltzmann labels, and g is fitted
with the run's g config. Then, under r_hat = proxy + g, compare per sub-episode

    best      exact optimum (solve_subepisode), its true return and window exploitation
    honest    the true optimum's value under r_hat
    ppo       the trained policy in round 1 (t0 = t_sub, one correction), Monte Carlo

A run is under-trained iff ppo < best by more than noise. If ppo >= honest while its
true return is below honest's, the correction itself pays for something other than
honesty (a design result, not a PPO one). Fresh RNG streams (n_fits draws); training's
own fits are not logged, so this samples the same distribution, not the same g.

    .venv/bin/python experiments/step4_probe.py results/step4/<env>/ppo/<run_id> [...]

Writes <run>/step4_probe.json (never overwritten).
"""

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sbx import PPO

from src.pbrr_core import GConfig, boltzmann_label
from src.step3.dp import solve_subepisode, table_policy_fn
from src.step3.pbrr import _traj_rows, fit_correction_rows, g_on_rows, g_table, policy_probs_fn, rollouts
from src.step3.protocol import Protocol
from src.step3.reference import build_reference
from src.step3.tasks import get_task

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from step3_check import sub_value  # noqa: E402


def rhat_mc(task, proto, policy_fn, params, t0, n_corr, n=256, seed=7):
    rs = rollouts(task.make_batch(n, seed=seed), policy_fn, proto, np.random.default_rng(seed), t0=t0,
                  n_corr=n_corr)
    g = g_on_rows(params, _traj_rows(rs, task)).reshape(n, -1).sum(axis=1)
    W = proto.window
    return {"rhat": float(np.mean(np.array([r.proxy for r in rs]) + g)),
            "true": float(np.mean([r.true for r in rs])),
            "window": float(np.mean([r.exploit[-W:].any() for r in rs]))}


def probe(seed_dir, n_fits=3):
    with open(os.path.join(seed_dir, "config.json")) as fh:
        cfg = json.load(fh)
    seed = int(cfg["seed"])
    task = get_task(cfg["env"], **cfg["task"])
    proto = Protocol(**cfg["protocol"])
    pb, gcfg = cfg["pbrr"], GConfig(**cfg["g"])
    T, A, tb = proto.t_sub, task.n_actions, task.tables
    ref, _ = build_reference(task, T, {**pb, "seed": pb["ref_seed"]})
    ref_trajs = rollouts(task.make_batch(pb["k"], seed=1000 + seed), ref, proto,
                         np.random.default_rng(1000 + seed))           # the run's own references
    model = PPO.load(os.path.join(seed_dir, "model.zip"), device="cpu")
    policy = policy_probs_fn(model, proto, A)
    pol_gt = solve_subepisode(tb, tb.true, T)
    honest_true = sub_value(tb, pol_gt, tb.true, T)[0]
    fits = []
    for f in range(n_fits):
        rng = np.random.default_rng(90_000 + f)
        agent = rollouts(task.make_batch(pb["k"], seed=80_000 + f), policy, proto, rng)
        D = [(a, r, boltzmann_label(a, r, rng, pb["beta"])) for a in agent for r in ref_trajs]
        params, _ = fit_correction_rows(D, task, gcfg, seed=int(rng.integers(2 ** 31)))
        R = tb.proxy + g_table(params, task)
        best = solve_subepisode(tb, R, T)
        best_r, _ = sub_value(tb, best, R, T)
        bt = rhat_mc(task, proto, table_policy_fn(best, A), params, t0=T, n_corr=1)
        ppo = rhat_mc(task, proto, policy, params, t0=T, n_corr=1)
        fits.append({"agent_round0_true": float(np.mean([a.true for a in agent])),
                     "best_rhat": best_r, "best_true": sub_value(tb, best, tb.true, T)[0],
                     "best_window": bt["window"], "honest_rhat": sub_value(tb, pol_gt, R, T)[0],
                     "honest_true": honest_true, "ppo_rhat": ppo["rhat"], "ppo_true": ppo["true"],
                     "ppo_window": ppo["window"]})
    return fits


def main():
    for run in sys.argv[1:]:
        out = {}
        for s in sorted(x for x in os.listdir(run) if x.startswith("seed") and os.path.isdir(os.path.join(run, x))):
            out[s] = probe(os.path.join(run, s))
            for f in out[s]:
                print(f"{os.path.basename(run)} {s}: best {f['best_rhat']:7.1f} (true {f['best_true']:6.1f}, "
                      f"window {f['best_window']:.2f})  honest {f['honest_rhat']:7.1f} (true {f['honest_true']:.1f})"
                      f"  ppo {f['ppo_rhat']:7.1f} (true {f['ppo_true']:6.1f}, window {f['ppo_window']:.2f})",
                      flush=True)
        path = os.path.join(run, "step4_probe.json")
        if out and not os.path.exists(path):
            with open(path, "w") as fh:
                json.dump(out, fh, indent=1)


if __name__ == "__main__":
    main()
