"""Step 4: has a PPO run reached its exact optimum? The convergence ("loss") curve and verdict.

For every seed of a run, the curve compares the logged training behaviour with the seed's
self-consistent target (experiments/step4_targets.py; found by matching the run's game -- env,
task, protocol, pbrr, g -- and seed), per block of 24 episodes:
  value gap   1 - received return per episode / target V0
  window gap  max over rounds k of |P(window k exploited) - target's|
  true gap    max over rounds k of |true return_k - target's| / (honest - proxy-optimal true)
  corr gap    |corrections per episode - target's|
The target answers the user's hypothesis (its end state) and the curve shows the trend, but the
target is not a ceiling for PPO: PPO's corrections are fitted on its own play and can pay more
(2026-11-05). So the verdict (pre-registered 2026-11-05, docs/step4_optimal.md) comes from the paired
best-response check of the seed's model at its current episode count (experiments/step4_br.py):
  CONVERGED   best-response gap <= 0.03
  IMPROVING   gap > 0.03 and the curve still improves (the value gap over the last 3 blocks is
              >= 0.01 below the 3 blocks ending 20% of the run earlier, or the window / true gap
              >= 0.02 below; runs shorter than 8 blocks count as improving) -> extend
  PLATEAU     gap > 0.03, not improving -> change the PPO config
  NEEDS BR    finished, but no best-response check at this episode count yet -> submit one
  RUNNING     not finished and no check (the gaps to the target are printed as progress)
"matches target" (all four gaps within value +-0.03, window 0.05, true 0.05, corrections 0.10, over
the last 10% of episodes) and "above target" (value gap < -0.03) are reported for information only.

    .venv/bin/python experiments/step4_convergence.py results/step4/<env>/optimal/<run_id> [...]

Writes <run>/step4_convergence.json and <run>/step4_convergence.png (recomputed on every call:
runs keep checkpointing).
"""

import glob
import json
import os
import sys

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from step4_br import TOL_BR, br_path  # noqa: E402
from step4_targets import OUT, game_key  # noqa: E402
from src.plotting import SERIES as PALETTE  # noqa: E402

BLOCK = 24
TOL = {"value": 0.03, "window": 0.05, "true": 0.05, "corr": 0.10}


def find_target(cfg):
    key = json.dumps(game_key(cfg), sort_keys=True)
    for path in sorted(glob.glob(os.path.join(OUT, cfg["env"], "targets", "*", f"seed{cfg['seed']}.json"))):
        with open(path) as fh:
            t = json.load(fh)
        if json.dumps(t["game"], sort_keys=True) == key:
            return path, t
    return None, None


def block_metrics(d, K, T, W, sl):
    on = d["on_exploit"].reshape(-1, K, T, d["on_exploit"].shape[-1])[sl]
    ca = d["caught"].reshape(-1, K, d["caught"].shape[-1])[sl].astype(bool)
    tr = d["env_true"].reshape(-1, K, d["env_true"].shape[-1])[sl]
    rc = d["env_received"].reshape(-1, K, d["env_received"].shape[-1])[sl]
    return {"window_by_k": on[:, :, T - W:, :].any(axis=2).mean((0, 2)),
            "true_by_k": tr.mean((0, 2)), "received_by_k": rc.mean((0, 2)),
            "corrections_per_ep": float(ca[:, :K - 1].sum(1).mean())}


def gaps(m, tg, span):
    return {"value": float(1 - np.sum(m["received_by_k"]) / tg["V0"]),
            "window": float(np.max(np.abs(m["window_by_k"] - np.asarray(tg["window_by_k"])))),
            "true": float(np.max(np.abs(m["true_by_k"] - np.asarray(tg["true_by_k"]))) / span),
            "corr": float(abs(m["corrections_per_ep"] - tg["corrections_per_ep"]))}


def seed_report(seed_dir):
    with open(os.path.join(seed_dir, "config.json")) as fh:
        cfg = json.load(fh)
    tpath, t = find_target(cfg)
    if t is None:
        return {"seed_dir": seed_dir, "verdict": "NO TARGET (run experiments/step4_targets.py for this game and seed)"}
    tg = t["target"]
    p = cfg["protocol"]
    K, T, W = p["n_sub"], p["t_sub"], p["window"]
    d = np.load(os.path.join(seed_dir, "logs.npz"))
    n_ep = len(d["caught"]) // K
    d = {k: d[k][:n_ep * K] for k in ("on_exploit", "caught", "env_true", "env_received")}
    span = abs(t["a1"]["honest_true"] - t["a1"]["proxy_opt_true"])
    curve = []
    for e in range(BLOCK, n_ep + 1, BLOCK):
        g = gaps(block_metrics(d, K, T, W, slice(e - BLOCK, e)), tg, span)
        curve.append({"episode": e, **g})
    n_last = max(BLOCK, int(round(0.1 * n_ep)))
    last = block_metrics(d, K, T, W, slice(max(0, n_ep - n_last), n_ep))
    g = gaps(last, tg, span)
    ok = {k: g[k] <= TOL[k] for k in TOL}
    ok["value"] = -TOL["value"] <= g["value"] <= TOL["value"]
    finished = os.path.exists(os.path.join(seed_dir, "metrics.json"))
    improving = True                                  # too short to tell
    if len(curve) >= 8:
        now = curve[-3:]
        then_end = max(3, len(curve) - max(3, len(curve) // 5))
        then = curve[then_end - 3:then_end]
        mean = lambda xs, k: float(np.mean([x[k] for x in xs]))
        improving = (mean(then, "value") - mean(now, "value") >= 0.01 or mean(then, "window") - mean(now, "window") >= 0.02
                     or mean(then, "true") - mean(now, "true") >= 0.02)
    br, bp = None, br_path(os.path.dirname(seed_dir), os.path.basename(seed_dir), n_ep)
    if os.path.exists(bp):
        with open(bp) as fh:
            br = json.load(fh)
    if br is not None:
        verdict = "CONVERGED" if br["gap"] <= TOL_BR else ("IMPROVING" if improving else "PLATEAU")
    else:
        verdict = "NEEDS BR" if finished else "RUNNING"
    prog = {}
    if os.path.exists(os.path.join(seed_dir, "progress.json")):      # runs from before 2026-11-03 have none
        with open(os.path.join(seed_dir, "progress.json")) as fh:
            prog = json.load(fh)
    return {"seed_dir": seed_dir, "target": os.path.relpath(tpath, os.path.dirname(OUT)), "verdict": verdict,
            "finished": finished, "episodes": n_ep, "of_episodes": prog.get("of_episodes", cfg["episodes"]),
            "last_episodes": n_last, "gaps": g, "pass": ok, "matches_target": bool(all(ok.values())),
            "above_target": bool(g["value"] < -TOL["value"]), "improving": bool(improving),
            "br": None if br is None else {"path": os.path.relpath(bp, os.path.dirname(OUT)), "gap": br["gap"],
                                           "gap_se": br["gap_se"], "best_response": br["best_response"],
                                           "policy": br["policy"], "behaviour": br["behaviour"]},
            "ppo": {k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in last.items()},
            "target_summary": {k: tg[k] for k in ("V0", "received_by_k", "true_by_k", "window_by_k",
                                                   "corrections_per_ep", "end_state")},
            "V_hide": t["V_hide"], "curve": curve}


def plot(run, reports):
    reps = [r for r in reports if "curve" in r]
    if not reps:
        return
    fig, axes = plt.subplots(1, 4, figsize=(16, 3.4), constrained_layout=True)
    names = [("value", "value gap  1 − received / V0*"), ("window", "window gap (max over rounds)"),
             ("true", "true-return gap (max over rounds, / range)"), ("corr", "corrections-per-episode gap")]
    for ax, (k, title) in zip(axes, names):
        for i, r in enumerate(reps):
            ep = [c["episode"] for c in r["curve"]]
            ax.plot(ep, [c[k] for c in r["curve"]], color=PALETTE[i % len(PALETTE)], lw=1.2,
                    label=f"{os.path.basename(r['seed_dir'])}: {r['verdict']}")
        ax.axhline(TOL[k], color="0.4", ls="--", lw=0.8)
        if k == "value":
            ax.axhline(-TOL[k], color="0.4", ls="--", lw=0.8)
        ax.axhline(0, color="0.6", lw=0.6)
        ax.set_title(title, fontsize=9)
        ax.set_xlabel("episode")
    axes[0].legend(fontsize=7)
    fig.suptitle(f"{os.path.relpath(run)} -- gap to the self-consistent exact optimum (24-episode blocks; "
                 "dashed: tolerance)", fontsize=10)
    fig.savefig(os.path.join(run, "step4_convergence.png"), dpi=110)
    plt.close(fig)


def main():
    for run in sys.argv[1:]:
        reports = []
        for s in sorted(x for x in os.listdir(run) if x.startswith("seed") and os.path.isdir(os.path.join(run, x))
                        and os.path.exists(os.path.join(run, x, "logs.npz"))):
            r = seed_report(os.path.join(run, s))
            reports.append(r)
            if "gaps" in r:
                g = r["gaps"]
                b = r["br"]
                brs = ("no best-response check" if b is None else
                       f"BR gap {b['gap']:+.3f} (s.e. {b['gap_se'] or float('nan'):.3f}; best response: "
                       f"{b['best_response']['end_state']}, true {np.round(b['best_response']['true_by_k'], 1).tolist()})")
                print(f"{os.path.relpath(run)} {s}: {r['verdict']:10s} ep {r['episodes']}/{r['of_episodes']}"
                      f"{'' if r['finished'] else ' (running)'}  {brs}  | target gaps: value {g['value']:+.3f} "
                      f"window {g['window']:.3f} true {g['true']:.3f} corr {g['corr']:.2f}"
                      f"{' (above target)' if r['above_target'] else ''}  | PPO true by k "
                      f"{np.round(r['ppo']['true_by_k'], 1).tolist()} vs target "
                      f"{np.round(r['target_summary']['true_by_k'], 1).tolist()} ({r['target_summary']['end_state']})")
            else:
                print(f"{os.path.relpath(run)} {s}: {r['verdict']}")
        if reports:
            with open(os.path.join(run, "step4_convergence.json"), "w") as fh:
                json.dump(reports, fh, indent=1)
            plot(run, reports)


if __name__ == "__main__":
    main()
