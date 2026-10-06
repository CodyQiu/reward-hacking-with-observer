"""Exp 3 (PBRR) figures. Reuses the repo's shared figure conventions."""

import numpy as np

from .plotting import (
    AXIS,
    GRID,
    INK,
    INK_2,
    MUTED,
    SEQ_BLUE,
    SERIES,
    SURFACE,
    add_subtitle,
    halo,
    plt,
    save_figure,
    style_axes,
    tint,
)
from .waypoint_env import FREE_CELLS, GOAL, GRID as GRID_N, START, WALLS, WAYPOINT

__all__ = [
    "fig_pbrr_curves",
    "fig_g_grid",
    "fig_minimal_mdps",
    "fig_training_divergence",
    "fig_sawtooth",
    "fig_clean_split",
    "fig_clean_repair_summary",
]


def fig_pbrr_curves(
    series, filename, title, subtitle, honest=2.0, ref_return=None, ylabel=None
):
    """True return vs number of preferences, one band per condition.

    ``series`` maps a label -> (n_preferences array, (n_seeds, n_iters) true returns).
    """
    fig, ax = plt.subplots(figsize=(7.8, 4.6))
    style_axes(ax)
    colors = [SERIES[0], SERIES[1], SERIES[2], "#eda100", "#4a3aa7"]

    # Per-seed traces, not a mean +- s.d. band: the outcome here is essentially
    # bimodal (a seed either repairs the reward to the honest optimum or stays at the
    # farming value), so a mean sits in a gap where no individual seed ever is, and a
    # standard deviation implies a spread that does not exist.
    # Distinct dash patterns as well as hues: several conditions end up with exactly
    # coincident medians (all repaired, or all not), and a solid line would simply be
    # hidden under the one drawn after it.
    dashes = [(0, ()), (0, (5, 1.6)), (0, (1.6, 1.6)), (0, (6, 1.6, 1.6, 1.6)), (0, (3, 1.4))]
    for idx, (label, (x, arr)) in enumerate(series.items()):
        arr = np.atleast_2d(np.asarray(arr, dtype=float))
        color = colors[idx % len(colors)]
        for row in arr:
            ax.plot(x, row, color=color, lw=0.9, alpha=0.30, zorder=2)
        ax.plot(
            x, np.median(arr, axis=0), color=color, lw=2.2, ls=dashes[idx % len(dashes)],
            marker="o", ms=4.5, zorder=3 + idx * 0.1, label=label,
        )

    for y, text in ((honest, f"honest optimum  {honest:+.1f}"),) + (
        ((ref_return, f"$\\pi_{{ref}}$  {ref_return:+.2f}"),) if ref_return is not None else ()
    ):
        ax.axhline(y, color=AXIS, lw=1.0, ls=(0, (4, 3)), zorder=1)
        halo(
            ax.annotate(
                text, xy=(0.015, y), xycoords=("axes fraction", "data"),
                xytext=(0, 4), textcoords="offset points",
                fontsize=8, color=INK_2, zorder=6,
            )
        )

    ax.set_xlabel("number of preferences elicited")
    ax.set_ylabel(ylabel or "true return of $\\pi^*_{\\hat r}$")
    # Legend and title both in figure coordinates, stacked by a point offset, so a
    # three-row legend cannot land on the title.
    fig.legend(
        frameon=False, fontsize=8.5, labelcolor=INK_2, loc="lower center",
        bbox_to_anchor=(0.5, 1.0), ncol=3, handlelength=1.6,
    )
    fig.suptitle(
        title, x=0.02, ha="left", va="bottom", color=INK, fontsize=11,
        y=1.0 + 34.0 / (fig.get_figheight() * 72.0),
    )
    fig.subplots_adjust(top=0.97)
    add_subtitle(ax, subtitle)
    return save_figure(fig, filename)


def fig_training_divergence(panels, filename, title, subtitle, honest=2.0):
    """The Exp-2-style split: received (training) return vs TRUE return, per episode.

    ``panels`` is a list of (panel_title, timesteps, received (n_seeds,T), true
    (n_seeds,T)). Both quantities are in reward units so they share one y axis --
    never two scales on one axes. One panel per reward function, because the
    *presence or absence of the split* is the comparison.
    """
    n = len(panels)
    fig, axes = plt.subplots(1, n, figsize=(4.6 * n + 0.6, 4.3), sharey=True, squeeze=False)
    axes = axes[0]

    for ax, (ptitle, x, received, true) in zip(axes, panels):
        style_axes(ax)
        for arr, color, label in (
            (received, SERIES[2], "received (training) return"),
            (true, SERIES[0], "TRUE return"),
        ):
            arr = np.atleast_2d(np.asarray(arr, dtype=float))
            mean, sd = arr.mean(axis=0), arr.std(axis=0)
            ax.fill_between(x, mean - sd, mean + sd, color=tint(color, 0.20), lw=0, zorder=2)
            ax.plot(x, mean, color=color, lw=2.0, zorder=3, label=label)
        ax.axhline(honest, color=AXIS, lw=1.0, ls=(0, (4, 3)), zorder=1)
        ax.axhline(0.0, color=AXIS, lw=0.8, zorder=1)
        halo(
            ax.annotate(
                f"honest optimum {honest:+.1f}",
                xy=(0.03, honest), xycoords=("axes fraction", "data"),
                xytext=(0, 4), textcoords="offset points",
                fontsize=8, color=INK_2, zorder=6,
            )
        )
        ax.set_xlabel("training steps")
        ax.xaxis.set_major_formatter(lambda v, _: f"{v / 1000:,.0f}k")
        ax.set_title(ptitle, loc="left", fontsize=9.5, color=INK, pad=6)
    axes[0].set_ylabel("mean return per episode")

    fig.legend(
        handles=[
            plt.Line2D([], [], color=SERIES[2], lw=2.0, label="received (training) return"),
            plt.Line2D([], [], color=SERIES[0], lw=2.0, label="TRUE return (measurement only)"),
        ],
        frameon=False, fontsize=8.5, labelcolor=INK_2, loc="lower center",
        bbox_to_anchor=(0.5, 1.0), ncol=2, handlelength=1.6,
    )
    fig.suptitle(
        title, x=0.02, ha="left", va="bottom", color=INK, fontsize=11,
        y=1.0 + 26.0 / (fig.get_figheight() * 72.0),
    )
    fig.subplots_adjust(top=0.9, wspace=0.08)
    add_subtitle(axes[0], subtitle)
    return save_figure(fig, filename)


def _draw_grid(ax, values, title, vmin, vmax):
    ax.set_facecolor(SURFACE)
    ax.set_xlim(-0.06, GRID_N + 0.06)
    ax.set_ylim(GRID_N + 0.06, -0.06)
    ax.set_xticks([])
    ax.set_yticks([])
    for side in ("top", "right", "bottom", "left"):
        ax.spines[side].set_visible(False)

    span = max(abs(vmin), abs(vmax), 1e-9)
    for r in range(GRID_N):
        for c in range(GRID_N):
            if (r, c) in WALLS:
                ax.add_patch(
                    plt.Rectangle((c, r), 1, 1, facecolor="#dedcd4", edgecolor=GRID, lw=1.0)
                )
                continue
            v = values.get((r, c), 0.0)
            # one hue, more-negative = darker: this is a magnitude scale
            weight = min(1.0, abs(v) / span)
            face = tint(SEQ_BLUE[5], 0.06 + 0.84 * weight)
            ax.add_patch(
                plt.Rectangle((c, r), 1, 1, facecolor=face, edgecolor=GRID, lw=1.0)
            )
            ax.text(
                c + 0.5, r + 0.55, f"{v:+.2f}", ha="center", va="center", fontsize=7.5,
                color="#ffffff" if weight > 0.55 else INK,
            )
            tag = {START: "START", GOAL: "GOAL", WAYPOINT: "WAYPOINT"}.get((r, c))
            if tag:
                ax.text(
                    c + 0.5, r + 0.2, tag, ha="center", va="center", fontsize=6.5,
                    color="#ffffff" if weight > 0.55 else INK,
                )
    ax.set_title(title, loc="left", fontsize=9.5, color=INK, pad=6)


def fig_g_grid(learned, ideal, filename, title, subtitle):
    """Side-by-side grids of min-over-actions g per cell: learned vs the analytic ideal."""
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 4.3))
    vmin = min(min(learned.values(), default=0.0), min(ideal.values(), default=0.0))
    vmax = max(max(learned.values(), default=0.0), max(ideal.values(), default=0.0))
    _draw_grid(axes[0], learned, "learned by PBRR", vmin, vmax)
    _draw_grid(axes[1], ideal, "analytic ideal  $g^* = -2\\cdot 1[s = $WAYPOINT$]$", vmin, vmax)
    fig.suptitle(title, x=0.02, ha="left", va="bottom", color=INK, fontsize=11,
                 y=1.0 + 12.0 / (fig.get_figheight() * 72.0))
    fig.subplots_adjust(top=0.9, wspace=0.08)
    add_subtitle(axes[0], subtitle, dy=-14)
    return save_figure(fig, filename)


def fig_minimal_mdps(rows, filename, title, subtitle):
    """Grouped bars: final true return per (MDP, C_1, lambda) cell, vs the optimum.

    ``rows`` is a list of dicts with keys mdp, c1, lam, final, optimum, first_optimal.
    """
    labels, finals, optima, colors = [], [], [], []
    for r in rows:
        labels.append(f"{r['mdp']}\n$C_1$={r['c1']:g}, $\\lambda$={r['lam']:g}")
        finals.append(r["final"])
        optima.append(r["optimum"])
        colors.append(SERIES[2] if r["first_optimal"] else SERIES[1])

    fig, ax = plt.subplots(figsize=(1.05 * len(rows) + 2.4, 4.2))
    style_axes(ax, grid_axis="y")
    x = np.arange(len(rows))
    ax.bar(x, finals, width=0.62, color=[tint(c, 0.85) for c in colors], zorder=3)
    for xi, opt in zip(x, optima):
        ax.plot([xi - 0.34, xi + 0.34], [opt, opt], color=INK, lw=1.6, zorder=4)
    for xi, (f, r) in enumerate(zip(finals, rows)):
        ax.annotate(
            f"{f:+.0f}" + (f"\nopt@{r['first_optimal']}" if r["first_optimal"] else "\nstalls"),
            xy=(xi, f), xytext=(0, 5), textcoords="offset points",
            ha="center", fontsize=8, color=INK_2,
        )
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8, color=INK_2)
    ax.set_ylabel("true return of the induced policy")
    ax.set_ylim(0, max(max(optima), max(finals)) * 1.28)
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch

    ax.legend(
        handles=[
            Line2D([], [], color=INK, lw=1.6, label="ground-truth optimum"),
            Patch(facecolor=tint(SERIES[2], 0.85), label="reaches the optimum"),
            Patch(facecolor=tint(SERIES[1], 0.85), label="stalls below it"),
        ],
        frameon=False, fontsize=8.5, labelcolor=INK_2, loc="lower left",
        bbox_to_anchor=(0.0, 1.0), ncol=3, handlelength=1.6,
    )
    ax.set_title(title, loc="left", pad=30)
    add_subtitle(ax, subtitle)
    return save_figure(fig, filename)


def fig_sawtooth(
    rows, refits, filename, honest=12.0, title=None, subtitle=None,
    peak_annotation="learned_g",
):
    """Exp 4: received vs true return across PBRR repair rounds, one tooth per round.

    Two panels sharing the x axis: the top is clipped so the teeth are readable, the
    bottom shows the full range, because PPO's exploitation of the learned correction
    puts the received return an order of magnitude above the teeth and would otherwise
    flatten them into the axis.
    """
    import numpy as np

    x = np.array([r["cumulative_steps"] for r in rows])
    recv = np.array([r["recv"] for r in rows])
    true = np.array([r["true"] for r in rows])

    fig, axes = plt.subplots(2, 1, figsize=(8.6, 6.4), sharex=True)
    for ax, clip in ((axes[0], True), (axes[1], False)):
        style_axes(ax)
        for rf in refits:
            ax.axvline(rf["cumulative_steps"], color=INK_2, lw=0.8, ls=(0, (2.5, 2)), zorder=1)
        ax.plot(x, recv, color=SERIES[2], lw=1.9, zorder=3)
        ax.plot(x, true, color=SERIES[0], lw=1.9, zorder=3)
        ax.axhline(honest, color=AXIS, lw=1.0, ls=(0, (4, 3)), zorder=1)
        if clip:
            lo = min(true.min(), 0.0) - 15
            ax.set_ylim(lo, max(honest + 20, np.percentile(recv, 90) + 25))
    axes[0].set_ylabel("return per episode  (clipped)")
    axes[1].set_ylabel("return per episode  (full range)")
    axes[1].set_xlabel("cumulative training steps   (dashed = PBRR refit / fresh policy)")
    axes[1].xaxis.set_major_formatter(lambda v, _: f"{v/1000:,.0f}k")
    halo(axes[0].annotate(f"honest optimum {honest:+.0f}", xy=(0.01, honest),
                          xycoords=("axes fraction", "data"), xytext=(0, 4),
                          textcoords="offset points", fontsize=8, color=INK_2, zorder=6))
    i = int(np.argmax(recv))
    if peak_annotation is not None:
        note = (
            f"PPO exploits the LEARNED g:\nreceived {recv[i]:+.0f}, true still {true[i]:+.0f}"
            if peak_annotation == "learned_g"
            else str(peak_annotation).format(received=recv[i], true=true[i])
        )
        halo(axes[1].annotate(
            note, xy=(x[i], recv[i]), xytext=(-165, -34), textcoords="offset points",
            fontsize=8.5, color=INK, zorder=7,
            arrowprops=dict(arrowstyle="->", color=INK_2, lw=1)))
    axes[0].legend(
        handles=[
            plt.Line2D([], [], color=SERIES[2], lw=1.9, label="received (training) return"),
            plt.Line2D([], [], color=SERIES[0], lw=1.9, label="TRUE return (unshaped)"),
        ],
        frameon=False, fontsize=8.5, labelcolor=INK_2, loc="upper right", ncol=2)
    fig.suptitle(
        title or "Exp 4  ·  six staircase exploits, a fresh policy each repair round",
        x=0.02, ha="left", va="bottom", color=INK, fontsize=11,
        y=1.0 + 16.0 / (fig.get_figheight() * 72.0))
    fig.subplots_adjust(top=0.93, hspace=0.12)
    add_subtitle(
        axes[1],
        subtitle or (
            "One fresh PPO per repair round (Algorithm 1 line 4); the correction is refit at "
            "each dashed line. The received return forks away from the true return in every "
            "round -- that is the sawtooth. Two caveats shown rather than hidden: the true "
            "return is back at its floor at the END of every round (the peaks are fresh agents "
            "passing through good behaviour before finding a tile, not repair), and PPO "
            "eventually abandons the bonus tiles to exploit the learned correction itself. "
            "Exact-DP PBRR repairs this same environment at refit 23, so this is a failure of "
            "the learner rather than of the method."
        ),
    )
    return save_figure(fig, filename)


def fig_clean_split(rows, filename, honest=12.0):
    """Independent PPO panels under fixed rewards: before, intermediate, and final.

    The plotted proxy return has only the known potential-based shaping contribution
    removed. PPO was trained on the raw received reward; this display transformation
    isolates the part of the proxy/true gap that can reflect the repeatable bonus or g.
    """
    by_round = {}
    for row in rows:
        by_round.setdefault(int(row["round"]), []).append(row)
    rounds = sorted(by_round)
    selected = list(dict.fromkeys([rounds[0], rounds[min(1, len(rounds) - 1)], rounds[-1]]))
    labels = {
        selected[0]: "before repair  ($g_0=0$)",
        selected[-1]: f"final trained reward  ($g_{{{selected[-1]-1}}}$)",
    }
    if len(selected) == 3:
        labels[selected[1]] = "after one PBRR refit  ($g_1$)"

    fig, axes = plt.subplots(1, len(selected), figsize=(4.2 * len(selected), 4.2),
                             sharex=True, sharey=True, squeeze=False)
    axes = axes[0]
    for ax, rnd in zip(axes, selected):
        style_axes(ax)
        data = by_round[rnd]
        x = np.asarray([r["step_in_round"] for r in data], dtype=float)
        proxy = np.asarray([r["recv_unshaped"] for r in data], dtype=float)
        true = np.asarray([r["true"] for r in data], dtype=float)
        ax.plot(x, proxy, color=SERIES[2], lw=2.1, label="proxy return − shaping")
        ax.plot(x, true, color=SERIES[0], lw=2.1, label="true return")
        ax.axhline(honest, color=AXIS, lw=1.0, ls=(0, (4, 3)))
        ax.set_title(
            f"{labels[rnd]}\nfinal exploit gap {proxy[-1] - true[-1]:+.1f}",
            loc="left", fontsize=9.5, color=INK, pad=7,
        )
        ax.set_xlabel("steps in this PPO run")
        ax.xaxis.set_major_formatter(lambda v, _: f"{v/1000:,.0f}k")
    axes[0].set_ylabel("mean return per evaluation episode")
    axes[0].legend(frameon=False, fontsize=8.5, labelcolor=INK_2, loc="upper left")
    fig.suptitle(
        "Exp 4  ·  the reward-hacking split closes after preference-based repair",
        x=0.02, ha="left", va="bottom", color=INK, fontsize=11,
        y=1.0 + 18.0 / (fig.get_figheight() * 72.0),
    )
    fig.subplots_adjust(top=0.86, wspace=0.08)
    add_subtitle(
        axes[0],
        "Each panel is a separate fresh PPO trained for 100k steps under one fixed reward. "
        "The known potential-shaping return is removed only for display; training used raw "
        "received reward. Thus the green–blue separation isolates bonus/g exploitation, "
        "without concatenating policy restarts into a misleading oscillation.",
        dy=-52,
    )
    return save_figure(fig, filename)


def fig_clean_repair_summary(conditions, filename, honest=12.0):
    """One endpoint per independent PPO run, plus exact post-refit exploit audits."""
    fig, axes = plt.subplots(1, 3, figsize=(12.2, 3.9))
    colors = [SERIES[1], SERIES[0], SERIES[2]]
    markers = ["o", "s", "^"]
    for idx, (label, out) in enumerate(conditions.items()):
        rows, refits = out["rows"], out["refits"]
        by_round = {}
        for row in rows:
            by_round.setdefault(int(row["round"]), []).append(row)
        rounds = sorted(by_round)
        end_true = [by_round[r][-1]["true"] for r in rounds]
        end_gap = [by_round[r][-1]["recv_unshaped"] - by_round[r][-1]["true"] for r in rounds]
        after_refit = [int(r["round"]) for r in refits]
        live = [int(r["n_live"]) for r in refits]
        style = dict(color=colors[idx % len(colors)], marker=markers[idx % len(markers)],
                     lw=2.0, ms=5.0, label=label)
        axes[0].plot(rounds, end_true, **style)
        axes[1].plot(rounds, end_gap, **style)
        axes[2].plot(after_refit, live, **style)

    for ax in axes:
        style_axes(ax)
        ax.set_xlabel("repair round")
        ax.set_xticks(range(1, max(len(v["refits"]) for v in conditions.values()) + 1))
    axes[0].axhline(honest, color=AXIS, lw=1.0, ls=(0, (4, 3)))
    axes[1].axhline(0.0, color=AXIS, lw=1.0, ls=(0, (4, 3)))
    axes[2].axhline(0.0, color=AXIS, lw=1.0, ls=(0, (4, 3)))
    axes[0].set_title("trained policy", loc="left", fontsize=9.5, color=INK)
    axes[0].set_ylabel("end-of-run true return")
    axes[1].set_title("proxy/true separation", loc="left", fontsize=9.5, color=INK)
    axes[1].set_ylabel("end exploit gap\n(proxy − shaping − true)")
    axes[2].set_title("exact reward audit", loc="left", fontsize=9.5, color=INK)
    axes[2].set_ylabel("profitable exploits after refit")
    axes[2].set_ylim(-0.25, 6.35)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(
        handles=handles,
        labels=labels,
        frameon=False,
        fontsize=8.5,
        labelcolor=INK_2,
        loc="upper right",
        bbox_to_anchor=(0.98, 0.995),
        ncol=max(1, len(conditions)),
    )
    fig.suptitle(
        "Exp 4  ·  endpoint summaries separate repair from PPO restarts",
        x=0.02, ha="left", va="top", color=INK, fontsize=11, y=0.995,
    )
    fig.subplots_adjust(top=0.78, wspace=0.34)
    return save_figure(fig, filename)
