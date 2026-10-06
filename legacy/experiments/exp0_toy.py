"""Exp 0 -- toy correction MDP: existence of a hiding regime, with closed forms.

Two states (loophole open / corrected-and-absorbing), three actions (comply,
exploit openly, exploit while hiding). Exploiting openly pays more but is caught
with probability p_O; hiding pays less but is caught with probability p_H < p_O.
The whole point of the experiment is the middle band in gamma where the optimal
policy is neither honest nor brazen.

The detection gap here is handed to the agent as a per-action number. That is the
circularity Exp 1 exists to remove -- but it buys a closed form, so every number
below is checked against algebra rather than against another numerical solve.

Run:  python experiments/exp0_toy.py
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.environments import TOY_ACTIONS, TOY_BASE, build_toy_mdp, toy_closed_form
from src.plotting import plot_phase_2d, plot_value_vs_gamma
from src.report import CheckLog, approx
from src.solver import (
    check_agreement,
    find_threshold,
    policy_evaluation,
    policy_iteration,
    value_iteration,
)

# Acceptance numbers, and the algebra they come from.
#   open -> hide  : r_O (1 - g(1-p_H)) = r_H (1 - g(1-p_O))  with r_1 = 0
#                   => g = (r_O - r_H) / (r_O(1-p_H) - r_H(1-p_O)) = 1/2.2
#   hide -> comply: r_H (1 - g) = r_C (1 - g(1-p_H))
#                   => g = (r_H - r_C) / (r_H - r_C(1-p_H)) = 1/1.2
GAMMA_OPEN_TO_HIDE = 1.0 / 2.2      # 0.454545...
GAMMA_HIDE_TO_COMPLY = 1.0 / 1.2    # 0.833333...


def label_from_solve(gamma, solver=policy_iteration, **params):
    """Exact-DP label: the optimal action at the open state."""
    R, P, _ = build_toy_mdp(**params)
    _, policy, _, _ = solver(R, P, gamma)
    return TOY_ACTIONS[int(policy[0])]


def main():
    log = CheckLog("EXPERIMENT 0 -- toy correction MDP (2 states, 3 actions)")
    p = dict(TOY_BASE)
    log.note(f"base params: {p}")

    # ---------------------------------------------------------------- #
    # 1. value iteration against the closed form
    # ---------------------------------------------------------------- #
    R, P, meta = build_toy_mdp(**p)
    worst_v, worst_g = 0.0, None
    for gamma in [0.0, 0.1, 0.3, 0.4545, 0.5, 0.7, 0.8333, 0.9, 0.95, 0.99]:
        V, policy, _, info = value_iteration(R, P, gamma)
        cf = toy_closed_form(gamma, **p)
        err = abs(V[0] - cf["v_star"])
        if err > worst_v:
            worst_v, worst_g = err, gamma
        log.check(
            f"VI == closed form at gamma={gamma:<6.4g} "
            f"(V*={V[0]:.6f}, argmax={TOY_ACTIONS[int(policy[0])]})",
            err < 1e-6 and TOY_ACTIONS[int(policy[0])] == cf["label"],
            f"|VI - closed form| = {err:.2e}, residual = {info['residual']:.2e}",
        )
    log.note(f"worst closed-form error over the grid: {worst_v:.3e} at gamma={worst_g}")

    # Every one of the three closed forms, not just the max. These are the values
    # of the three *stationary* strategies, so the matching exact computation is
    # policy evaluation of the constant policy -- not Q*, which would already have
    # the optimal continuation baked into it.
    gamma = 0.9
    V, _, Q, _ = value_iteration(R, P, gamma)
    cf = toy_closed_form(gamma, **p)
    for a, name in enumerate(TOY_ACTIONS):
        v_pi = policy_evaluation(np.array([a, 0]), R, P, gamma)
        log.check(
            f"V^pi(always {name}) == closed-form V_{name} at gamma=0.9",
            approx(v_pi[0], cf[name], 1e-9),
            f"policy eval={v_pi[0]:.6f} vs closed form={cf[name]:.6f}",
        )
    log.check(
        "V*(open) == max over the three stationary strategy values at gamma=0.9",
        approx(V[0], max(cf[n] for n in TOY_ACTIONS), 1e-9),
        f"V*={V[0]:.6f}, best stationary={max(cf[n] for n in TOY_ACTIONS):.6f}",
    )
    log.check(
        "Q*(open, a*) == V*(open) at gamma=0.9 (greedy action is consistent)",
        approx(Q[0].max(), V[0], 1e-12),
        f"max_a Q = {Q[0].max():.9f}, V* = {V[0]:.9f}",
    )

    # ---------------------------------------------------------------- #
    # 2. VI vs policy iteration
    # ---------------------------------------------------------------- #
    for gamma in (0.3, 0.6, 0.9, 0.99):
        d = check_agreement(R, P, gamma)
        log.check(
            f"VI == policy iteration at gamma={gamma}",
            d["agree"],
            f"max|V_vi - V_pi| = {d['max_value_gap']:.2e}, "
            f"residuals {d['residual_vi']:.1e}/{d['residual_pi']:.1e}",
        )

    # ---------------------------------------------------------------- #
    # 3. phase boundaries in gamma
    # ---------------------------------------------------------------- #
    g_oh = find_threshold(
        lambda g: label_from_solve(g, **p) == "exploit_open", 0.05, 0.6, tol=1e-9
    )
    g_hc = find_threshold(
        lambda g: label_from_solve(g, **p) == "exploit_hide", 0.6, 0.95, tol=1e-9
    )
    log.check(
        "boundary exploit_open -> exploit_hide at gamma = 0.4545",
        approx(g_oh, GAMMA_OPEN_TO_HIDE, 1e-6),
        f"exact-DP bisection {g_oh:.9f} vs closed form {GAMMA_OPEN_TO_HIDE:.9f}",
    )
    log.check(
        "boundary exploit_hide -> comply at gamma = 0.8333",
        approx(g_hc, GAMMA_HIDE_TO_COMPLY, 1e-6),
        f"exact-DP bisection {g_hc:.9f} vs closed form {GAMMA_HIDE_TO_COMPLY:.9f}",
    )
    log.check(
        "all three regimes exist and are ordered open < hide < comply",
        label_from_solve(0.3, **p) == "exploit_open"
        and label_from_solve(0.6, **p) == "exploit_hide"
        and label_from_solve(0.95, **p) == "comply",
        "sampled at gamma = 0.3 / 0.6 / 0.95",
    )

    # ---------------------------------------------------------------- #
    # 4. CONTROL: close the detection gap
    # ---------------------------------------------------------------- #
    p_nogap = dict(p, p_H=p["p_O"])
    gammas_fine = np.linspace(0.01, 0.995, 400)
    labels_nogap = [label_from_solve(g, **p_nogap) for g in gammas_fine]
    log.check_control(
        "p_H = p_O (no detection gap) => the hide band vanishes entirely",
        "exploit_hide" not in labels_nogap,
        f"labels present: {sorted(set(labels_nogap))}",
    )
    g_oc = find_threshold(
        lambda g: label_from_solve(g, **p_nogap) == "exploit_open", 0.05, 0.95, tol=1e-9
    )
    # (r_O - r_C) / (r_O - r_C(1 - p_O)) with r_1 = 0
    g_oc_closed = (p["r_O"] - p["r_C"]) / (p["r_O"] - p["r_C"] * (1 - p["p_O"]))
    log.check_control(
        "no-gap control keeps a clean open -> comply transition",
        approx(g_oc, g_oc_closed, 1e-6),
        f"bisection {g_oc:.6f} vs closed form {g_oc_closed:.6f}",
    )

    # ---------------------------------------------------------------- #
    # 5. CONTROL: non-punitive correction
    # ---------------------------------------------------------------- #
    p_soft = dict(p, r_1=p["r_C"])
    labels_soft = [label_from_solve(g, **p_soft) for g in gammas_fine]
    log.check_control(
        "r_1 = r_C (correction merely closes the loophole) => the comply band vanishes",
        "comply" not in labels_soft,
        f"labels present: {sorted(set(labels_soft))}",
    )
    # V_hide - V_comply = (1 - gamma) / [(1 - gamma(1-p_H))(1 - gamma)] > 0 for all gamma
    diffs = [
        toy_closed_form(g, **p_soft)["exploit_hide"] - toy_closed_form(g, **p_soft)["comply"]
        for g in gammas_fine
    ]
    log.check_control(
        "and hiding strictly dominates complying at every gamma when r_1 = r_C",
        min(diffs) > 0,
        f"min(V_hide - V_comply) = {min(diffs):.4f}",
    )

    # ---------------------------------------------------------------- #
    # 6. figures
    # ---------------------------------------------------------------- #
    gammas = np.linspace(0.001, 0.985, 900)

    def curves(params):
        cf = [toy_closed_form(g, **params) for g in gammas]
        return {k: np.array([c[k] for c in cf]) for k in TOY_ACTIONS}

    log.figure(
        plot_value_vs_gamma(
            gammas,
            curves(p),
            "exp0_value_vs_gamma.png",
            "Exp 0  ·  value of each strategy at the open state",
            boundaries=[
                (GAMMA_OPEN_TO_HIDE, f"$\\gamma$ = {GAMMA_OPEN_TO_HIDE:.3f}"),
                (GAMMA_HIDE_TO_COMPLY, f"$\\gamma$ = {GAMMA_HIDE_TO_COMPLY:.3f}"),
            ],
            ylim=(0, 22),
            subtitle=(
                f"closed form, verified against value iteration to {worst_v:.0e}   ·   "
                f"r_C={p['r_C']:g}, r_O={p['r_O']:g}, r_H={p['r_H']:g}, "
                f"p_O={p['p_O']:g}, p_H={p['p_H']:g}, r_1={p['r_1']:g}"
            ),
        )
    )
    log.figure(
        plot_value_vs_gamma(
            gammas,
            curves(p_nogap),
            "exp0_control_no_gap.png",
            "Exp 0 CONTROL  ·  no detection gap ($p_H = p_O$): the hide band is gone",
            boundaries=[(g_oc, f"$\\gamma$ = {g_oc:.3f}")],
            ylim=(0, 22),
            subtitle=(
                "hiding is now strictly dominated by exploiting openly at every "
                "$\\gamma$ -- only deterrence remains"
            ),
        )
    )

    # phase diagram over (gamma, p_H), p_O fixed: the detection-gap sweep
    gs = np.linspace(0.02, 0.98, 240)
    phs = np.linspace(0.0, p["p_O"], 190)
    grid = np.empty((len(phs), len(gs)), dtype=object)
    cf_mismatch = 0
    for i, ph in enumerate(phs):
        params = dict(p, p_H=ph)
        for j, g in enumerate(gs):
            grid[i, j] = label_from_solve(g, **params)
            if grid[i, j] != toy_closed_form(g, **params)["label"]:
                cf_mismatch += 1
    log.check(
        "exact DP agrees with the closed form on every cell of the (gamma, p_H) grid",
        cf_mismatch == 0,
        f"{grid.size} cells, {cf_mismatch} mismatches",
    )
    log.check_control(
        "hide never wins anywhere along the p_H = p_O edge of the phase diagram",
        "exploit_hide" not in set(grid[-1, :]),
        f"top-edge labels: {sorted(set(grid[-1, :]))}",
    )
    hide_frac = float(np.mean(grid == "exploit_hide"))
    log.note(f"hide occupies {hide_frac:.1%} of the (gamma, p_H) plane")
    log.figure(
        plot_phase_2d(
            gs,
            phs,
            grid,
            "exp0_phase_gamma_pH.png",
            "Exp 0  ·  detection-gap sweep: the hide band closes as $p_H \\to p_O$",
            "discount factor  $\\gamma$",
            "hidden-exploit detection probability  $p_H$",
            control_line=(p["p_O"], "$p_H = p_O$  ·  no gap  ·  CONTROL: no hide region"),
            subtitle=f"$p_O$ = {p['p_O']:g} fixed; every cell solved by exact policy iteration",
        )
    )

    # phase diagram over (gamma, r_1), gap fixed: the correction-penalty sweep
    r1s = np.linspace(-3.0, 1.5, 190)
    grid2 = np.empty((len(r1s), len(gs)), dtype=object)
    for i, r1 in enumerate(r1s):
        params = dict(p, r_1=r1)
        for j, g in enumerate(gs):
            grid2[i, j] = label_from_solve(g, **params)
    soft_rows = r1s >= p["r_C"]
    log.check_control(
        "comply never wins anywhere on the r_1 >= r_C side of the phase diagram",
        "comply" not in set(grid2[soft_rows, :].ravel()),
        f"labels for r_1 >= r_C: {sorted(set(grid2[soft_rows, :].ravel()))}",
    )
    log.figure(
        plot_phase_2d(
            gs,
            r1s,
            grid2,
            "exp0_phase_gamma_r1.png",
            "Exp 0  ·  correction-penalty sweep: deterrence needs a punitive correction",
            "discount factor  $\\gamma$",
            "corrected-regime reward  $r_1$",
            control_line=(
                p["r_C"],
                "$r_1 = r_C$  ·  non-punitive  ·  CONTROL: no comply region above here",
            ),
            subtitle=(
                f"detection gap held at $p_O$={p['p_O']:g}, $p_H$={p['p_H']:g}; "
                "exact policy iteration per cell"
            ),
        )
    )

    log.finding(
        f"thresholds: exploit_open -> exploit_hide at gamma = {g_oh:.6f}; "
        f"exploit_hide -> comply at gamma = {g_hc:.6f}"
    )
    return log.summary()


if __name__ == "__main__":
    main()
