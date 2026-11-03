"""Step 3 figures: the per-environment training dashboard and the suite summary.

Conventions as in src/plots_step1.py / plots_step2.py: reward per sub-episode, never
accumulated; received reward = original proxy + the PBRR correction in force; true
reward on its own row; "exploits" = a step where proxy != true (the suite-wide rule).
"""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

from .plots_step1 import (INK, INK_2, MUTED, PROXY_COLOR, TRUE_COLOR, _ramp, _shades, _thousands,
                          add_subtitle, save_figure, style_axes, tint)

__all__ = ["plot_step3_dashboard", "plot_suite"]

FRACTIONS = (("off_0_3", PROXY_COLOR, "exploit steps off-window, sub-episodes 0-3 (relative to the idealised optimum)"),
             ("win_0_3", INK, "audit windows exploited, sub-episodes 0-3"),
             ("win_final", TRUE_COLOR, "final audit window exploited (sub-episode 4)"))


def plot_step3_dashboard(runs, n_sub, filename, title, subtitle=None, refs=()):
    """``runs``: one dict per seed with received / true (n_ep, K) per-sub-episode
    returns, rounds_per_ep, win_0_3, win_final, off_0_3 (n_ep,), ep_steps, and the PBRR
    rounds' timesteps and g on the agent's exploit transitions (pbrr_steps, pbrr_gx)."""
    fig, axes = plt.subplots(5, 1, figsize=(10.5, 13.0), sharex=True,
                             gridspec_kw=dict(height_ratios=[1.2, 0.9, 0.7, 0.9, 0.8]))
    n = min(len(r["received"]) for r in runs)
    x = runs[0]["ep_steps"][:n] / 1e6
    mean = lambda key: np.mean([r[key][:n] for r in runs], axis=0)
    for ax, key, color, label in ((axes[0], "received", PROXY_COLOR, "received reward\n(proxy + correction)"),
                                  (axes[1], "true", TRUE_COLOR, "true reward")):
        style_axes(ax, grid_axis="y")
        for (value, _), ls in zip(refs if key == "received" else (), ((0, (1.2, 1.6)), (0, (5, 2)))):
            ax.axhline(value, color=INK, lw=1.0, ls=ls, zorder=5)
        m = mean(key)
        for k, c in enumerate(_shades(_ramp(color), n_sub)):
            ax.plot(x, m[:, k], color=c, lw=1.2, zorder=3 + k,
                    label=f"sub-episode {k}" + (" (last)" if k == n_sub - 1 else ""))
        _thousands(ax)
        ax.set_ylabel(f"{label}\nreturn in the sub-episode")
        ax.legend(frameon=False, fontsize=7.5, labelcolor=INK_2, loc="center left", bbox_to_anchor=(1.01, 0.5))
    ax = style_axes(axes[2], grid_axis="y")
    for r in runs:
        ax.plot(x, r["rounds_per_ep"][:n], color=tint(INK_2, 0.3), lw=0.7)
    ax.plot(x, mean("rounds_per_ep"), color=INK_2, lw=1.5)
    ax.set_ylabel("PBRR rounds\nper episode")
    ax = style_axes(axes[3], grid_axis="y")
    for key, c, lab in FRACTIONS:
        ax.plot(x, mean(key), color=c, lw=1.4, label=lab)
    ax.set_ylim(-0.03, 1.13)
    ax.set_ylabel("fraction")
    ax.legend(frameon=False, fontsize=7.5, labelcolor=INK_2, loc="center left", bbox_to_anchor=(1.01, 0.5))
    ax = style_axes(axes[4], grid_axis="y")
    for r in runs:
        ax.scatter(np.asarray(r["pbrr_steps"]) / 1e6, r["pbrr_gx"], s=6, color=PROXY_COLOR, linewidths=0,
                   alpha=0.6, rasterized=True)
    ax.axhline(0, color=MUTED, lw=0.8)
    ax.set_ylabel("learned g on the agent's\nexploit steps, per round")
    ax.set_xlabel("training steps (millions)")
    ax.set_xlim(0, x[-1] if len(x) else 1)
    fig.suptitle(title, x=0.02, ha="left", va="bottom", color=INK, fontsize=11, y=0.995)
    fig.subplots_adjust(hspace=0.15, top=0.97)
    add_subtitle(axes[-1], subtitle, dy=-42, width=150)
    return save_figure(fig, filename)


def plot_suite(rows, filename, title, subtitle=None):
    """One row per environment: the three exploitation fractions and PBRR rounds per
    episode over training (seed mean, light lines per seed). ``rows``: list of
    (label, runs) with runs as for ``plot_step3_dashboard``."""
    fig, axes = plt.subplots(len(rows), 2, figsize=(12.5, 2.3 * len(rows) + 0.6), squeeze=False,
                             gridspec_kw=dict(width_ratios=[2.2, 1.0]))
    for i, (label, runs) in enumerate(rows):
        n = min(len(r["received"]) for r in runs)
        x = runs[0]["ep_steps"][:n] / 1e6
        ax, ax2 = style_axes(axes[i, 0], grid_axis="y"), style_axes(axes[i, 1], grid_axis="y")
        for key, c, _ in FRACTIONS:
            for r in runs:
                ax.plot(x, r[key][:n], color=tint(c, 0.25), lw=0.6, zorder=2)
            ax.plot(x, np.mean([r[key][:n] for r in runs], axis=0), color=c, lw=1.5, zorder=3)
        ax.set_ylim(-0.03, 1.13)
        ax.set_ylabel(label, fontsize=9.5, color=INK)
        for r in runs:
            ax2.plot(x, r["rounds_per_ep"][:n], color=tint(INK_2, 0.3), lw=0.6)
        ax2.plot(x, np.mean([r["rounds_per_ep"][:n] for r in runs], axis=0), color=INK_2, lw=1.4)
        ax2.set_ylim(-0.1, 4.2)
        if i == 0:
            ax.set_title("exploitation over training", fontsize=9.5, color=INK_2, loc="left")
            ax2.set_title("PBRR rounds (corrections) per episode", fontsize=9.5, color=INK_2, loc="left")
        if i == len(rows) - 1:
            ax.set_xlabel("training steps (millions)")
            ax2.set_xlabel("training steps (millions)")
    handles = [Line2D([], [], color=c, lw=1.5, label=lab) for _, c, lab in FRACTIONS]
    fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.06, 1.0), frameon=False, fontsize=8.5,
               labelcolor=INK_2, ncol=1)
    fig.suptitle(title, x=0.02, ha="left", va="bottom", color=INK, fontsize=11, y=1.07)
    fig.subplots_adjust(hspace=0.25, wspace=0.18)
    add_subtitle(axes[-1, 0], subtitle, dy=-40, width=170)
    return save_figure(fig, filename)
