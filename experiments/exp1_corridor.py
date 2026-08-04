"""Exp 1 -- corridor gridworld: hiding as an emergent property of the map.

Same three-way choice as Exp 0, with the circularity removed. There is no "hide"
action here. There are two loophole tiles that pay identically:

    F_LOUD  = (0,1)   one step from START, in the row the overseer watches
    F_QUIET = (1,2)   a three-step detour away, in the row it does not

Detection is a property of *where the agent stands while it farms*, not of which
action it picks. So concealment has to be discovered: the agent must give up three
steps of discounting to buy a lower detection hazard. The control switches the
observation gap off (p_unwatch := p_watch) and changes nothing else -- same map,
same rewards, same actions -- and the detour has to disappear.

Run:  python experiments/exp1_corridor.py
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.environments import (
    CORRIDOR_ACTIONS,
    CORRIDOR_BASE,
    F_LOUD_POS,
    F_QUIET_POS,
    START_POS,
    build_corridor_mdp,
    classify_corridor_policy,
    rc_of,
    state_of,
)
from src.plotting import (
    plot_dumbbell,
    plot_grid_policy,
    plot_phase_1d,
    plot_phase_2d,
    plot_sweeps,
)
from src.report import CheckLog, approx
from src.solver import check_agreement, find_threshold, policy_iteration, value_iteration

GAMMA_HIGH = 0.95
# Acceptance numbers supplied with the experiment spec.
ACC_V_QUIET = 11.97
ACC_V_LOUD = 8.03
ACC_V_NOGAP = 5.80
ACC_GAMMA_FARM = 0.82
ACC_PATH_GAP = [(0, 0), (1, 0), (1, 1), (1, 2)]


def solve(gamma, solver=policy_iteration, **params):
    """Exact solve + intent classification of the corridor at one parameter point."""
    R, P, meta = build_corridor_mdp(**{**CORRIDOR_BASE, **params})
    V, policy, Q, _ = solver(R, P, gamma)
    info = classify_corridor_policy(policy)
    info.update(V=V, policy=policy, Q=Q, meta=meta)
    return info


def main():
    log = CheckLog("EXPERIMENT 1 -- corridor gridworld (20 states, 5 actions)")
    log.note(f"base params: {CORRIDOR_BASE}")
    log.note(
        "F_LOUD = (0,1) watched, 1 step from START;  "
        "F_QUIET = (1,2) unwatched, 3 steps from START"
    )

    # ---------------------------------------------------------------- #
    # 1. solver hygiene on this environment
    # ---------------------------------------------------------------- #
    R, P, meta = build_corridor_mdp(**CORRIDOR_BASE)
    for gamma in (0.5, 0.82, 0.95, 0.99):
        d = check_agreement(R, P, gamma)
        log.check(
            f"VI == policy iteration on the corridor at gamma={gamma}",
            d["agree"],
            f"max|V_vi - V_pi| = {d['max_value_gap']:.2e}, "
            f"residuals {d['residual_vi']:.1e}/{d['residual_pi']:.1e}",
        )
    V_vi, pi_vi, Q_vi, info_vi = value_iteration(R, P, GAMMA_HIGH)
    log.check(
        f"Bellman optimality residual is ~0 at gamma={GAMMA_HIGH}",
        info_vi["residual"] < 1e-9,
        f"residual = {info_vi['residual']:.2e}, "
        f"||V - V*||_inf bound = {info_vi['value_error_bound']:.2e}",
    )

    # ---------------------------------------------------------------- #
    # 2. THE CORE RESULT: gap vs no gap at high gamma
    # ---------------------------------------------------------------- #
    gap = solve(GAMMA_HIGH)
    nogap = solve(GAMMA_HIGH, p_unwatch=CORRIDOR_BASE["p_watch"])

    v_q_gap = gap["V"][state_of(F_QUIET_POS, 0)]
    v_l_gap = gap["V"][state_of(F_LOUD_POS, 0)]
    v_q_no = nogap["V"][state_of(F_QUIET_POS, 0)]
    v_l_no = nogap["V"][state_of(F_LOUD_POS, 0)]

    log.check(
        f"WITH gap: V(F_QUIET, unpatched) = {ACC_V_QUIET}",
        approx(v_q_gap, ACC_V_QUIET, 5e-3),
        f"exact {v_q_gap:.4f}",
    )
    log.check(
        f"WITH gap: V(F_LOUD, unpatched) = {ACC_V_LOUD}",
        approx(v_l_gap, ACC_V_LOUD, 5e-3),
        f"exact {v_l_gap:.4f}",
    )
    log.check(
        "WITH gap: the unwatched loophole is worth strictly more",
        v_q_gap > v_l_gap,
        f"advantage of the far, quiet tile = {v_q_gap - v_l_gap:+.4f}",
    )
    log.check(
        f"WITH gap: greedy path from START detours through the unwatched row {ACC_PATH_GAP}",
        gap["path_rc"][: len(ACC_PATH_GAP)] == ACC_PATH_GAP and gap["detour"],
        f"path = {gap['path_rc'][:6]}, label = {gap['label']}",
    )

    log.check_control(
        f"NO gap: V(F_QUIET, unpatched) = V(F_LOUD, unpatched) = {ACC_V_NOGAP}",
        approx(v_q_no, ACC_V_NOGAP, 5e-3)
        and approx(v_l_no, ACC_V_NOGAP, 5e-3)
        and approx(v_q_no, v_l_no, 1e-12),
        f"V(F_QUIET) = {v_q_no:.4f}, V(F_LOUD) = {v_l_no:.4f}, "
        f"difference = {abs(v_q_no - v_l_no):.2e}",
    )
    log.check_control(
        "NO gap: the far tile's value advantage is exactly zero",
        approx(v_q_no - v_l_no, 0.0, 1e-12),
        f"advantage {v_q_no - v_l_no:+.2e} vs {v_q_gap - v_l_gap:+.4f} with the gap",
    )
    log.check_control(
        "NO gap: the agent does not detour into the unwatched row",
        not nogap["detour"] and nogap["path_rc"][1] == (0, 1),
        f"path = {nogap['path_rc'][:6]}, label = {nogap['label']}",
    )

    # how robust is that first move? report the action-value margin at START.
    q_start = gap["Q"][state_of(START_POS, 0)]
    best, second = np.sort(q_start)[::-1][:2]
    log.note(
        f"action-value margin at START (gap regime): "
        f"{CORRIDOR_ACTIONS[int(q_start.argmax())]} beats the runner-up by "
        f"{best - second:.4f} -- not a numerical tie"
    )
    q_start_no = nogap["Q"][state_of(START_POS, 0)]
    b2, s2 = np.sort(q_start_no)[::-1][:2]
    log.note(
        f"action-value margin at START (control): "
        f"{CORRIDOR_ACTIONS[int(q_start_no.argmax())]} beats the runner-up by "
        f"{b2 - s2:.4f}"
    )

    # ---------------------------------------------------------------- #
    # 3. the gamma phase transition
    # ---------------------------------------------------------------- #
    g_farm = find_threshold(
        lambda g: solve(g)["label"] == "goto_goal", 0.6, 0.9, tol=1e-7
    )
    log.check(
        f"do-the-task -> farm transition at gamma = {ACC_GAMMA_FARM}",
        approx(g_farm, ACC_GAMMA_FARM, 5e-3),
        f"bisection {g_farm:.6f}",
    )
    g_stealth = find_threshold(lambda g: not solve(g)["detour"], 0.83, 0.95, tol=1e-7)
    log.check(
        "a second, distinct boundary exists where farming turns stealthy",
        g_stealth > g_farm,
        f"detour begins at gamma = {g_stealth:.6f} (farming begins at {g_farm:.6f})",
    )
    log.finding(
        f"the gap regime has THREE bands, not two: do the task (gamma < {g_farm:.4f}) "
        f"-> farm the quiet tile but reach it through the watched row "
        f"({g_farm:.4f} - {g_stealth:.4f}) -> detour through the unwatched row to get "
        f"there unseen (gamma > {g_stealth:.4f}). Only the third band is concealment."
    )

    gammas = np.linspace(0.50, 0.995, 400)
    labels_gap = np.array([solve(g)["label"] for g in gammas])
    res_nogap = [solve(g, p_unwatch=CORRIDOR_BASE["p_watch"]) for g in gammas]
    labels_nogap = np.array([r["label"] for r in res_nogap])

    log.check_control(
        "NO gap: no detour at ANY gamma in [0.50, 0.995]",
        not any(r["detour"] for r in res_nogap),
        f"{len(gammas)} gammas swept, 0 detours",
    )
    log.check_control(
        "NO gap: the farm-hidden regime never appears",
        "farm_quiet" not in set(labels_nogap),
        f"labels present without the gap: {sorted(set(map(str, labels_nogap)))}",
    )
    dv_nogap = max(
        abs(
            r["V"][state_of(F_QUIET_POS, 0)] - r["V"][state_of(F_LOUD_POS, 0)]
        )
        for r in res_nogap
    )
    log.check_control(
        "NO gap: the two loopholes are worth the same at every gamma",
        dv_nogap < 1e-9,
        f"max |V(F_QUIET) - V(F_LOUD)| over the sweep = {dv_nogap:.2e}",
    )
    g_farm_nogap = find_threshold(
        lambda g: solve(g, p_unwatch=CORRIDOR_BASE["p_watch"])["label"] == "goto_goal",
        0.6,
        0.99,
        tol=1e-7,
    )
    log.note(
        f"without the gap the task still stops getting done, but later "
        f"(gamma = {g_farm_nogap:.4f} vs {g_farm:.4f}) and in plain view"
    )

    # ---------------------------------------------------------------- #
    # 4. deterrence sweeps -- what makes the agent do the task again?
    # ---------------------------------------------------------------- #
    pens = np.linspace(0.0, -30.0, 121)
    pen_rows = [solve(GAMMA_HIGH, penalty=float(v)) for v in pens]
    v_pen = np.array([r["V"][state_of(F_QUIET_POS, 0)] for r in pen_rows])
    log.check(
        "penalty sweep: V(F_QUIET) saturates -- the correction penalty is never paid",
        np.ptp(v_pen[pens <= -12.0]) < 1e-9,
        f"V(F_QUIET) = {v_pen[pens <= -12.0][0]:.4f} for every penalty <= -12 "
        f"(spread {np.ptp(v_pen[pens <= -12.0]):.1e})",
    )
    log.check(
        "penalty sweep: no penalty, however punitive, restores doing the task",
        all(r["label"] != "goto_goal" for r in pen_rows),
        f"labels over penalty in [0, -30]: {sorted({r['label'] for r in pen_rows})}",
    )
    log.finding(
        "punishment does not deter here: once the penalty bites, the optimal policy "
        "farms hit-and-run -- one step on the loophole tile, one step off -- so the "
        "agent is never standing on a loophole when the patch lands and never pays "
        "the penalty at all. Deterrence by punishment requires detection first."
    )

    rgoals = np.linspace(5.0, 30.0, 126)
    rg_rows = [solve(GAMMA_HIGH, R_goal=float(v)) for v in rgoals]
    rg_star = find_threshold(
        lambda v: solve(GAMMA_HIGH, R_goal=float(v))["label"] != "goto_goal",
        5.0,
        30.0,
        tol=1e-5,
    )
    log.check(
        "R_goal sweep: raising the opportunity cost DOES restore doing the task",
        any(r["label"] == "goto_goal" for r in rg_rows),
        f"threshold R_goal = {rg_star:.4f} (base {CORRIDOR_BASE['R_goal']:g}), "
        f"i.e. the task must be worth ~{rg_star / CORRIDOR_BASE['R_goal']:.1f}x more",
    )

    farms = np.linspace(1.0, 0.05, 96)
    farm_rows = [solve(GAMMA_HIGH, farm=float(v)) for v in farms]
    farm_star = find_threshold(
        lambda v: solve(GAMMA_HIGH, farm=float(v))["label"] != "goto_goal",
        0.05,
        1.0,
        tol=1e-6,
    )
    log.check(
        "farm sweep: shrinking the exploit's payoff also restores doing the task",
        any(r["label"] == "goto_goal" for r in farm_rows),
        f"threshold farm = {farm_star:.4f} (base {CORRIDOR_BASE['farm']:g})",
    )

    # ---------------------------------------------------------------- #
    # 5. figures
    # ---------------------------------------------------------------- #
    log.figure(
        plot_phase_1d(
            gammas,
            [
                ("with gap\n$p_{unwatch}$=0.05", labels_gap),
                ("CONTROL: no gap\n$p_{unwatch}=p_{watch}$=0.6", labels_nogap),
            ],
            "exp1_gamma_phase.png",
            "Exp 1  ·  optimal intent from START as patience rises",
            boundaries=[
                [
                    (g_farm, f"$\\gamma$={g_farm:.3f}"),
                    (g_stealth, f"$\\gamma$={g_stealth:.3f}  stealth begins"),
                ],
                [(g_farm_nogap, f"$\\gamma$={g_farm_nogap:.3f}")],
            ],
            subtitle=(
                "close the observation gap and the hidden-farming band disappears; the "
                "agent still stops doing the task, but only in plain view"
            ),
        )
    )

    log.figure(
        plot_dumbbell(
            ["V(F_QUIET, unpatched)\nunwatched tile", "V(F_LOUD, unpatched)\nwatched tile"],
            [v_q_no, v_l_no],
            [v_q_gap, v_l_gap],
            "exp1_values_gap_vs_control.png",
            f"Exp 1  ·  what the observation gap is worth at $\\gamma$ = {GAMMA_HIGH}",
            "CONTROL: no gap ($p_{unwatch}$ = 0.6)",
            "with gap ($p_{unwatch}$ = 0.05)",
            "exact discounted value",
            subtitle=(
                "the far tile is worth more than the near one only when it is actually "
                "stealthier; with the gap closed the two are identical to 1e-12"
            ),
        )
    )

    log.figure(
        plot_grid_policy(
            None,
            None,
            meta,
            "exp1_policy_gap_vs_control.png",
            f"Exp 1  ·  greedy policy on the unpatched layer, $\\gamma$ = {GAMMA_HIGH}",
            panels=[
                (
                    f"HIDING: with the observation gap  ·  detour to the unwatched "
                    f"loophole  ·  V(START) = {gap['V'][START_POS]:.2f}",
                    gap["policy"],
                    gap["V"],
                    0,
                    gap["path"],
                ),
                (
                    f"CONTROL: gap closed  ·  no detour, farms the near watched "
                    f"loophole  ·  V(START) = {nogap['V'][START_POS]:.2f}",
                    nogap["policy"],
                    nogap["V"],
                    0,
                    nogap["path"],
                ),
            ],
            subtitle=(
                "cell numbers are exact state values; the rollout traces intent with "
                "detection switched off"
            ),
        )
    )
    log.figure(
        plot_grid_policy(
            gap["policy"],
            gap["V"],
            meta,
            "exp1_policy_patched_layer.png",
            f"Exp 1  ·  after the correction lands (patched layer), $\\gamma$ = {GAMMA_HIGH}",
            patched=1,
            subtitle=(
                "with the loophole closed the loophole tiles now cost the agent, so it "
                "leaves and completes the task -- the overseer's objective, one "
                "correction late"
            ),
        )
    )

    # 2-D phase diagram: the control as a continuum
    gs = np.linspace(0.55, 0.99, 170)
    pus = np.linspace(0.0, CORRIDOR_BASE["p_watch"], 130)
    grid = np.empty((len(pus), len(gs)), dtype=object)
    detour_grid = np.zeros((len(pus), len(gs)), dtype=bool)
    for i, pu in enumerate(pus):
        for j, g in enumerate(gs):
            r = solve(g, p_unwatch=float(pu))
            grid[i, j] = r["label"]
            detour_grid[i, j] = r["detour"]
    log.check_control(
        "hidden farming never appears along the p_unwatch = p_watch edge",
        "farm_quiet" not in set(grid[-1, :]),
        f"top-edge labels: {sorted(set(grid[-1, :]))}",
    )
    log.check(
        "the hidden-farming region shrinks monotonically as the gap closes",
        all(
            np.mean(grid[i] == "farm_quiet") >= np.mean(grid[i + 1] == "farm_quiet") - 0.02
            for i in range(len(pus) - 1)
        ),
        f"hidden farming covers {np.mean(grid == 'farm_quiet'):.1%} of the plane",
    )
    log.figure(
        plot_phase_2d(
            gs,
            pus,
            grid,
            "exp1_phase_gamma_punwatch.png",
            "Exp 1  ·  the concealment band exists only while the overseer has a blind spot",
            "discount factor  $\\gamma$",
            "detection rate on the unwatched tile  $p_{unwatch}$",
            control_line=(
                CORRIDOR_BASE["p_watch"],
                "$p_{unwatch} = p_{watch}$  ·  no blind spot  ·  CONTROL",
            ),
            subtitle=(
                f"$p_{{watch}}$ = {CORRIDOR_BASE['p_watch']:g} fixed; detection comes from "
                "the observation model and the map, never from the action label"
            ),
        )
    )

    log.figure(
        plot_sweeps(
            [
                dict(
                    x=pens,
                    xlabel="correction penalty",
                    ylabel="value of the unwatched loophole",
                    series={"V(F_QUIET, unpatched)": v_pen},
                    bands=[r["label"] for r in pen_rows],
                    vlines=[(-12.0, "saturated: penalty never paid")],
                ),
                dict(
                    x=rgoals,
                    xlabel="task reward  $R_{goal}$",
                    ylabel="",
                    series={
                        "V(F_QUIET, unpatched)": [
                            r["V"][state_of(F_QUIET_POS, 0)] for r in rg_rows
                        ]
                    },
                    bands=[r["label"] for r in rg_rows],
                    vlines=[(rg_star, f"$R_{{goal}}$ = {rg_star:.2f}")],
                ),
                dict(
                    x=farms,
                    xlabel="loophole payoff per step",
                    ylabel="",
                    series={
                        "V(F_QUIET, unpatched)": [
                            r["V"][state_of(F_QUIET_POS, 0)] for r in farm_rows
                        ]
                    },
                    bands=[r["label"] for r in farm_rows],
                    vlines=[(farm_star, f"farm = {farm_star:.3f}")],
                    invert_x=True,
                ),
            ],
            "exp1_deterrence_sweeps.png",
            f"Exp 1  ·  what restores doing the task at $\\gamma$ = {GAMMA_HIGH} (gap left open)",
            subtitle=(
                "punishing the corrected regime does nothing -- the agent farms "
                "hit-and-run and never pays it. Raising the task's reward, or lowering "
                "the loophole's, does deter."
            ),
        )
    )

    log.finding(
        f"gap regime at gamma={GAMMA_HIGH}: V(F_QUIET,0) = {v_q_gap:.4f} vs "
        f"V(F_LOUD,0) = {v_l_gap:.4f} (advantage {v_q_gap - v_l_gap:+.4f}); "
        f"control: both {v_q_no:.4f} (advantage {v_q_no - v_l_no:+.1e})"
    )
    return log.summary()


if __name__ == "__main__":
    main()
