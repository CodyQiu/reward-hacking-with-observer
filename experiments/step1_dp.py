"""Step 1, exact DP: does the reward-maximising policy avoid the audit?

15x15 grid, START (0,0), GOAL (14,14), one exploit tile at (4,9). Proxy: -1/step,
+50 GOAL, +100 per step on the exploit. Corrected (= true): the exploit tile is an
ordinary -1 tile. Five 100-step sub-episodes per 500-step episode; at each boundary
the overseer audits the last W steps and, on detecting the bonus there, patches the
proxy to the corrected reward for the rest of the episode. The reward resets at the
episode end. gamma = 1.

Everything here is exact backward induction (src/audit_dp.py); every number below
is either checked against a closed form or reported as a DP output.

    .venv/bin/python experiments/step1_dp.py
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.audit_dp import evaluate, greedy_probs, hand_returns, signatures, solve
from src.audit_grid import BASE, manhattan
from src.plotting import plot_lines
from src.plotting import INK_2
from src.plots_step1 import PROXY_COLOR, TRUE_COLOR, plot_by_k, plot_within_episode
from src.report import CheckLog, approx
from src.solver import find_threshold


def run(cfg, myopic=False):
    V, pol = solve(cfg, myopic=myopic)
    ev = evaluate(cfg, greedy_probs(cfg, pol))
    ev["sig"] = signatures(cfg, ev["bonus_unpatched"])
    ev["V0"] = V[0, cfg.idx(cfg.start), 0, 0]
    ev["policy"] = pol
    return ev


def main():
    log = CheckLog("Step 1 -- exact DP on the 15x15 audit grid (gamma = 1)")
    cfg = BASE
    d_s, d_g = manhattan(cfg.start, cfg.exploit), manhattan(cfg.exploit, cfg.goal)
    log.note(f"exploit {cfg.exploit}: d(START, E) = {d_s}, d(E, GOAL) = {d_g}; "
             f"T_sub = {cfg.t_sub}, K = {cfg.n_sub}, W = {cfg.window}, p = {cfg.p_detect}")

    # ---- main condition --------------------------------------------------------
    hand = hand_returns(cfg)
    main_ev = run(cfg)
    sig = main_ev["sig"]
    log.check("optimal proxy return = closed form (timing evasion)",
              approx(main_ev["V0"], hand["evade"]) and approx(main_ev["proxy_return"], hand["evade"]),
              f"DP {main_ev['V0']:.1f} vs closed form {hand['evade']:.1f}")
    log.check("optimal true return = closed form", approx(main_ev["true_return"], hand["evade_true"]),
              f"{main_ev['true_return']:.1f}")
    log.check("steps off the exploit exactly when the window opens, k = 0..3",
              sig["step_off_nonfinal"],
              f"P(bonus) at tau=89: {sig['pre'][:-1]}, in window: {sig['window'][:-1]}")
    log.check("keeps exploiting through the final window (nothing left to protect)",
              sig["final_dwell"], f"final-window P(bonus) = {sig['window'][-1]:.2f}")
    log.check("no effective correction is ever triggered", approx(main_ev["corrections"], 0.0),
              f"corrections = {main_ev['corrections']:.3f}; final audit detects "
              f"{main_ev['final_audit_detection']:.2f} (reward resets before it bites)")
    for name, val in (("open exploitation", hand["open"]), ("honest", hand["honest"]),
                      ("no overseer", hand["no_overseer"])):
        log.note(f"reference: {name:18s} proxy return {val:9.1f}")

    log.check("per round: proxy 7,700 in rounds 0..3 and 8,700 in round 4; true -100 in every round",
              np.allclose(main_ev["proxy_by_k"], [7700] * 4 + [8700])
              and np.allclose(main_ev["true_by_k"], -100),
              f"proxy {main_ev['proxy_by_k']}, true {main_ev['true_by_k']}")

    # (Controls -- myopic credit, whole-window audit, toothless patch -- are kept as unit
    # tests in tests/test_step1.py; they are not part of the current results.)
    log.figure(plot_within_episode(
        cfg,
        [("Main: audit the last 10 steps of each sub-episode",
          main_ev["proxy_t"], main_ev["true_t"], None, None)],
        "step1_dp_within_episode.png",
        "Exact optimum: exploit until the audit window opens, every sub-episode but the last",
        subtitle="Exact DP, gamma = 1. Cumulative reward within each 100-step sub-episode, restarting "
                 "at 0 at every boundary; proxy and true have their own y scales. Proxy 7,700 per "
                 "sub-episode (8,700 in the last), true -100, never corrected.",
    ))

    # ---- window sweep ----------------------------------------------------------
    Ws = [1, 5, 10, 14, 15, 16, 20, 30, 50, 70, 86, 87, 88, 90, 100]
    rows = []
    for W in Ws:
        wcfg = cfg.with_(window=W)
        ev = run(wcfg)
        h = hand_returns(wcfg)
        valid = W <= cfg.t_sub - d_s   # closed form needs the exploit reachable before the window
        rows.append((W, ev, h["evade"] if valid else None))
        if valid:
            log.check(f"W = {W:3d}: DP = closed form", approx(ev["V0"], h["evade"]),
                      f"{ev['V0']:.0f}; step-off k<4: {ev['sig']['step_off_nonfinal']}, "
                      f"P(GOAL by boundary, k=0) = {ev['goal_by_k'][0]:.0f}")
        else:
            log.note(f"W = {W:3d}: DP {ev['V0']:.0f} (exploit unreachable before the window; "
                     f"corrections {ev['corrections']:.2f}, step-off {ev['sig']['step_off_nonfinal']})")
    walk = [W for W, ev, _ in rows if ev["goal_by_k"][0] > 0.5 and ev["sig"]["step_off_nonfinal"]]
    log.check("window behaviour switches from idling to a goal run once W >= d(E, GOAL)",
              walk and min(walk) == d_g and all(W >= d_g for W in walk),
              f"goal run during the window for W in {walk}")
    log.figure(plot_lines(
        [W for W, *_ in rows],
        [
            ("return in round 0", {"proxy": [ev["proxy_by_k"][0] for _, ev, _ in rows],
                                   "true": [ev["true_by_k"][0] for _, ev, _ in rows]}),
            ("true return\nin round 0", {"true": [ev["true_by_k"][0] for _, ev, _ in rows]}),
            ("rounds 0..3\nwith a step-off",
             {"step-off": [int(ev["sig"]["step_off"][:-1].sum()) for _, ev, _ in rows]}),
        ],
        "step1_dp_window_sweep.png",
        "Audit-window length W: evasion persists until the window covers the exploit run",
        "audit window W (steps)",
        subtitle=f"Exact DP; returns are per round (round 0), not per episode. The true return "
                 f"jumps at W = {d_g} = d(E, GOAL), where the agent can step off and still reach "
                 "GOAL inside the window. Past W = 87 the exploit cannot be reached before the "
                 "window opens, so a step-off is impossible: the exploit then pays in only one round "
                 "per episode, and round 0 is played honestly (+22).",
        colors={"proxy": PROXY_COLOR, "true": TRUE_COLOR, "step-off": INK_2},
    ))

    # ---- detection-probability sweep -------------------------------------------
    gain = cfg.window * cfg.exploit_bonus                    # dwell the window vs idle in it
    loss_k3 = hand_returns(cfg.with_(n_sub=1))["no_overseer"] - (
        cfg.step_cost * manhattan(cfg.start, cfg.goal) + cfg.goal_bonus)
    p3_closed = gain / loss_k3

    def exploits_window(p, k):
        return run(cfg.with_(p_detect=p))["sig"]["window"][k] > 0.5

    thresholds = []
    for k in range(cfg.n_sub - 1):
        thresholds.append(find_threshold(lambda p: exploits_window(p, k), 1e-4, 1.0, tol=1e-5))
    log.check("k = 3 threshold p* = W*b / (V_open(k=4) - V_patched(k=4)) (closed form)",
              abs(thresholds[3] - p3_closed) < 2e-5,
              f"bisection {thresholds[3]:.5f} vs {gain:.0f}/{loss_k3:.0f} = {p3_closed:.5f}")
    log.check("earlier sub-episodes have more future to protect, so lower thresholds",
              all(np.diff(thresholds) > 0),
              "p*_k = " + ", ".join(f"{x:.4f}" for x in thresholds))
    ps = np.linspace(0, 0.2, 201)  # every threshold lies below 0.12; p > 0.2 is flat
    sweep = [run(cfg.with_(p_detect=p)) for p in ps]
    log.figure(plot_by_k(
        ps,
        [[ev["sig"]["window"][k] for ev in sweep] for k in range(cfg.n_sub)],
        "step1_dp_p_sweep.png",
        "Detection probability: the window is kept clean once p exceeds a per-k threshold",
        "P(detect | bonus collected in the audit window)",
        "P(bonus in window k | loophole open)",
        ylim=(-0.05, 1.08),
        extra_panels=[("corrections / episode", [ev["corrections"] for ev in sweep])],
        subtitle="Exact DP, p in [0, 0.2] (nothing changes above). Thresholds p*_k = " + ", ".join(f"{x:.3f}" for x in thresholds)
                 + " for k = 0..3; the final window (k = 4) is always exploited.",
    ))

    log.finding("At the exact optimum the agent exploits for 78 of every 100 steps, steps off the "
                "tile at the moment the audit window opens in sub-episodes 0-3, and never gets "
                "patched. In the last sub-episode it exploits through the window, because nothing "
                "is left to protect. Proxy 39,500 vs true -500.")
    log.summary()


if __name__ == "__main__":
    main()
