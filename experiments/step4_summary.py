"""Step 4 summary: one Markdown page with the two tables we keep coming back to.

  Table 1  PPO after the first correction, per seed, against the ideal (honest) true return
           and against the best behaviour under the corrected reward (probe or exact check),
           with a verdict (under-tuned / converged / reward problem).
  Table 2  What the first correction does to the reward, from the exact checks (Phase A):
           sub-episode value of hiding and of exploiting before it, of the honest route, the
           exploit and the best route after it, and the exact optimum's true return by round.

Every number is read from results/ (readouts, probes, Phase A summaries); the grid's values
under the corrected reward are recomputed from Phase A's saved reward tables. Only the
verdicts are written by hand (VERDICTS below): they are judgements on those numbers.

    .venv/bin/python experiments/step4_summary.py [--out docs/step4_summary_1.md]
"""

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from step2_pbrr_check import dp_subepisode, run_policy  # noqa: E402
from step4_readout import readout  # noqa: E402
from src.audit_grid import BASE, build_tables  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R4 = os.path.join(ROOT, "results", "step4")
SEEDS = (10, 11, 12)
ENVS = [("grid", "Grid"), ("absent_supervisor", "Absent Supervisor"), ("tomato", "Tomato"),
        ("boat_race", "Boat Race"), ("taxi", "Taxi"), ("mountain_car", "MountainCar"),
        ("lunar_lander", "LunarLander")]
# label | grid PPO run / grid Phase A name | task PPO run / task Phase A dir
VARIANTS = [("paper's PBRR", None, "base", None, "base"),
            ("swap", "S4_P2swap_seeds10-12", "P2-swap", "S4_P2swap_ep1000_seeds10-12", "P2swap_ep1000"),
            ("swap, no L⁺", "S4_P2swapNoLplus_seeds10-12", "P2-swap-noLplus",
             "S4_P2swapNoLplus_ep1000_seeds10-12", "P2swapNoLplus_ep1000"),
            ("no regulariser", "S4_P1eq1_seeds10-12", "P1-eq1", "S4_P1eq1_ep1000_seeds10-12", "P1eq1_ep1000"),
            ("skip (released code)", "S4_P1skip_seeds10-12", "P1-skip", None, None)]

VERDICTS = {   # (env, variant label) -> judgement on the numbers in its row (see CLAUDE.md 4f)
    ("grid", "swap"): "✓ near ideal",
    ("grid", "swap, no L⁺"): "✓ near ideal",
    ("grid", "no regulariser"): "✓ near ideal",
    ("grid", "skip (released code)"): "2 of 3: seed 10's raise lands on non-honest transitions",
    ("absent_supervisor", "swap"): "**under-tuned**: PPO 2–9% below honest under its own r̂ (no regulariser: 0–3%)",
    ("absent_supervisor", "swap, no L⁺"): "**under-tuned** (1–19% below honest) *and* a reward problem: the best is a −50 route in 6 of 9 fits",
    ("absent_supervisor", "no regulariser"): "✓ converged (88% of ideal)",
    ("tomato", "swap"): "**under-tuned, badly**: seeks a correction every round (4 per episode)",
    ("tomato", "swap, no L⁺"): "seed 10 ✓; seeds 11–12 **under-tuned** (4 corrections per episode)",
    ("tomato", "no regulariser"): "✓ converged (96% of ideal)",
    ("boat_race", "swap"): "✗ reward problem: the corrected reward pays for farming (seed 10 partial)",
    ("boat_race", "swap, no L⁺"): "✗ reward problem: pays for farming",
    ("boat_race", "no regulariser"): "✗ reward problem: PPO ties honest under r̂, but farming is best in 9 of 9",
    ("taxi", "*"): "finished seeds never find the exploit, so are never corrected (exploration); "
                   "the exact checks predict farming",
    ("mountain_car", "*"): "finished seed never finds the exploit; exact checks: swap keeps exploiting, "
                           "no regulariser hides",
    ("lunar_lander", "*"): "can't tell: rarely corrected (0.05–0.4 per episode), no exact solver",
}


def load(path):
    with open(path) as fh:
        return json.load(fh)


def fmt(x, nd=0):
    if x is None:
        return "—"
    return f"{x + 0.0 if round(x, nd) else 0.0:,.{nd}f}".replace("-", "−")


# ---------------------------------------------------------------- table 1: PPO
def ppo_row(env, run):
    """Per seed: (true after the first correction, corrections per episode) or None if unfinished."""
    rdir = os.path.join(R4, "ppo" if env == "grid" else f"{env}/ppo", run)
    out = []
    for s in SEEDS:
        d = os.path.join(rdir, f"seed{s}")
        if not os.path.exists(os.path.join(d, "metrics.json")):
            out.append(None)
            continue
        m = readout(d)
        out.append((m["true_after_first_correction"], m["corrections_per_ep"]))
    return out


def ppo_cell(per_seed):
    def one(x):
        if x is None:
            return "running"
        ta, c = x
        return f"{fmt(ta)} ({c:.1f})" if ta is not None else f"never corrected ({c:.1f})"
    return " / ".join(one(x) for x in per_seed)


def best_cell(env, run, phase_a, honest, exploit):
    """The best behaviour under the corrected reward: the probe's 9 fits if there is one,
    else the exact check (the canonical fit)."""
    probe = os.path.join(R4, f"{env}/ppo", run or "", "step4_probe.json")
    if run and os.path.exists(probe):
        bt = [f["best_true"] for fits in load(probe).values() for f in fits]
        tol = 0.05 * abs(honest - exploit)
        n_h = sum(b >= honest - tol for b in bt)
        rest = [b for b in bt if b < honest - tol]
        s = f"honest in {n_h} of {len(bt)} fits"
        if rest:
            lo, hi = fmt(min(rest)), fmt(max(rest))
            s += f"; else true {lo}" + ("" if lo == hi else f" to {hi}")
        gap = [100 * (f["honest_rhat"] - f["ppo_rhat"]) / abs(f["honest_rhat"])
               for fits in load(probe).values() for f in fits]
        return s + f". PPO vs honest under r̂: {fmt(-max(gap))}% to {fmt(-min(gap))}%"
    if phase_a is None:
        return "—"
    return f"{fmt(phase_a)}* (exact check)"


# ---------------------------------------------------------------- table 2: the reward after one correction
def grid_values(name):
    """Sub-episode values on the grid from Phase A's saved tables (a4 sequence, network fit, seed 0)."""
    tb = build_tables(BASE)
    T, E = BASE.t_sub, BASE.idx(BASE.exploit)
    R = np.load(os.path.join(R4, "phase_a", f"R_{name}_a4_neural.npz"))["R"]
    _, pol_h = dp_subepisode(tb.true, tb, T)
    _, pol_x = dp_subepisode(R[0], tb, T)
    _, pol_b = dp_subepisode(R[1], tb, T)
    opt = load(os.path.join(R4, "phase_a", "summary.json"))["variants"][name]["a4/neural"]["optimum"]
    return {"hide": 7700.0, "exploit_before": run_policy(pol_x, R[0], tb, T, E)[0],
            "honest_before": run_policy(pol_h, R[0], tb, T, E)[0],
            "honest": run_policy(pol_h, R[1], tb, T, E)[0], "exploit": run_policy(pol_x, R[1], tb, T, E)[0],
            "best": run_policy(pol_b, R[1], tb, T, E)[0], "best_true": run_policy(pol_b, R[1], tb, T, E)[1],
            "true_by_k": opt["true_by_k"], "epochs": None}


def task_values(env, vdir):
    p = os.path.join(R4, env, "phase_a", vdir, "summary.json")
    if not os.path.exists(p):
        return None
    d = load(p)
    a1, r = d["a1"], d["a4"][0]
    base = load(os.path.join(R4, env, "phase_a", "base", "summary.json"))
    hide = a1.get("avoid_opt_proxy", base["ideal"]["received_by_k"][0])   # the hiding optimum's round
    return {"hide": hide, "exploit_before": a1["proxy_opt_proxy"], "honest_before": a1["honest_proxy"],
            "honest": r["honest_value_rhat"], "exploit": r["open_exploiter_value_rhat"],
            "best": r["best_value_rhat"], "best_true": r["best_true"],
            "true_by_k": d["ideal"]["true_by_k"], "epochs": d["g_config"]["epochs"]}


def what_it_does(v):
    dh, dx = v["honest"] - v["honest_before"], v["exploit"] - v["exploit_before"]
    tol = 0.02 * max(abs(v["exploit_before"]), 1.0)
    part = lambda d, what: (f"raises {what} {fmt(d)}" if d > tol else f"fines {what} {fmt(-d)}" if d < -tol
                            else f"leaves {what}")
    s = f"{part(dh, 'honest')}, {part(dx, 'the exploit')}"
    s += ("; one correction pays ≥ hiding" if v["best"] >= v["hide"] else "; one correction pays < hiding")
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "docs", "step4_summary_1.md"))
    args = ap.parse_args()

    consts = {}
    for env, _ in ENVS:
        if env == "grid":
            consts[env] = (22.0, -100.0)
        else:
            a1 = load(os.path.join(ROOT, "results", "step3", env, "phase_a", "summary.json"))["a1"]
            if "honest" in a1:
                consts[env] = (a1["honest"]["true"], a1["open"]["true"])
            else:
                consts[env] = (a1.get("sim_honest", {}).get("true", a1["honest_true"]),
                               a1.get("sim_proxy_opt", {}).get("true", a1["proxy_opt_true"]))

    L = ["# Step 4 summary 1: which correction lets the agent be corrected once and then behave",
         "",
         "Generated by `experiments/step4_summary.py` from `results/step4/` (readouts, probes, exact checks). "
         "Rerun it after new runs finish; only the verdict column is written by hand.",
         "",
         "**Goal.** The agent is corrected in the first window and then behaves well (honest true return) "
         "in every later window. *Ideal* = the honest route's true return per sub-episode.",
         "",
         "## Table 1. PPO after the first correction",
         "",
         "PPO column: true return per sub-episode in the rounds after an env's first correction, last 10% of "
         "episodes, seeds 10 / 11 / 12, with corrections per episode in brackets (≈ 1.0 is the goal; 4.0 = "
         "corrected every round). *Best under the corrected reward*: the probe (`step4_probe.py`) refits g on "
         "the final policy's round-0 play 3 times per seed and solves the next round exactly; * = no probe, "
         "the exact check's canonical fit instead. If PPO is well below a best that is honest, PPO is "
         "under-tuned; if the best is not honest, the corrected reward itself is the problem.",
         "",
         "| Env (ideal) | Variant | PPO, seeds 10 / 11 / 12 | Best under the corrected reward | Verdict |",
         "|---|---|---|---|---|"]
    for env, title in ENVS:
        honest, exploit = consts[env]
        first = True
        for label, grun, gname, trun, tdir in VARIANTS:
            if label == "paper's PBRR":
                continue
            run = grun if env == "grid" else trun
            if run is None:
                continue
            rdir = os.path.join(R4, "ppo" if env == "grid" else f"{env}/ppo", run)
            if not os.path.isdir(rdir):
                continue
            per_seed = ppo_row(env, run)
            if env == "grid":
                pa = load(os.path.join(R4, "phase_a", "summary.json"))["variants"][gname]["a4/neural"]["levels"][0]
                pa_best = pa["best_subepisode_true"]
            else:
                v = task_values(env, tdir)
                pa_best = None if v is None else v["best_true"]
            verdict = VERDICTS.get((env, label), VERDICTS.get((env, "*"), ""))
            head = f"**{title}** ({fmt(honest)}{', scripted' if env == 'lunar_lander' else ''})" if first else ""
            L.append(f"| {head} | {label} | {ppo_cell(per_seed)} | "
                     f"{best_cell(env, run, pa_best, honest, exploit)} | {verdict} |")
            first = False

    L += ["",
          "## Table 2. What the first correction does to the reward (exact checks)",
          "",
          "Values of one sub-episode (100 steps; MountainCar 200) under the reward in force. *Before*: the "
          "uncorrected proxy, where the agent's options are to hide (exploit off-window, comply in the audit) or "
          "exploit through the audit and be corrected. *After*: r̂ = proxy + g after one correction of the open "
          "exploiter (Phase A's canonical fit; grid: network fit seed 0). Hiding pays iff the best route after the "
          "correction is worth less than hiding (with γ = 1 the agent compares these levels across the boundary); "
          "the *shape* (honest vs exploit after) decides whether being corrected leads to honest play. "
          "Last column: the exact optimum of the whole episode under that PBRR (true return in rounds 0–4).",
          "",
          "| Env | PBRR | Before: hide / exploit | After: honest | After: exploit | After: best (its true) "
          "| What the correction does | Exact optimum, true by round |",
          "|---|---|---|---|---|---|---|---|"]
    for env, title in ENVS:
        if env == "lunar_lander":
            continue
        first = True
        for label, _, gname, _, tdir in VARIANTS:
            if env != "grid" and tdir is None:
                continue
            v = grid_values(gname) if env == "grid" else task_values(env, tdir)
            if v is None:
                continue
            ep = "" if v["epochs"] in (None, 1000) else f" (g fit {v['epochs']} epochs, Step 3's)"
            name = f"**{label}**" if label == "no regulariser" else label
            L.append(f"| {f'**{title}**' if first else ''} | {name}{ep} | {fmt(v['hide'])} / "
                     f"{fmt(v['exploit_before'])} | {fmt(v['honest'])} | {fmt(v['exploit'])} | "
                     f"{fmt(v['best'])} ({fmt(v['best_true'])}) | {what_it_does(v)} | "
                     f"{' / '.join(fmt(x) for x in v['true_by_k'])} |")
            first = False
    L += ["",
          "LunarLander has no exact solver (its references are scripted strategies), so it has no row here. "
          "Honest true return per sub-episode: " + ", ".join(
              f"{t} {fmt(consts[e][0])}" for e, t in ENVS) + ".",
          ""]
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as fh:
        fh.write("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
