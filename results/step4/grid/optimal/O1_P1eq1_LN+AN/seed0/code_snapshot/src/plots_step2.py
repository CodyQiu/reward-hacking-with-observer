"""Step 2 figures: the training dashboard against the PBRR overseer.

Conventions as in src/plots_step1.py (reward per sub-episode, never accumulated;
received reward = original proxy + the PBRR correction in force; true reward on its
own row where its variation matters).
"""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

from .plots_step1 import (INK, INK_2, MUTED, PROXY_COLOR, TRUE_COLOR, _col_title, _ramp, _shades,
                          _thousands, add_subtitle, save_figure, style_axes, tint)

__all__ = ["plot_step2_dashboard"]


def plot_step2_dashboard(runs, n_sub, filename, title, subtitle=None, refs=()):
    """``runs``: list of dicts (one per seed) with
         received, true:  (n_ep, K) per-sub-episode returns, mean over envs
         rounds_per_ep:   (n_ep,)   PBRR rounds (corrections) per env per episode
         win_0_3, win_final, off_0_3: (n_ep,) exploitation fractions
         pbrr_steps, pbrr_gE: PBRR round training steps and g at the exploit tile
         ep_steps: (n_ep,) training step at each episode start
    """
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
            ax.plot(x, m[:, k], color=c, lw=1.2, zorder=3 + k, label=f"sub-episode {k}"
                    + (" (last)" if k == n_sub - 1 else ""))
        _thousands(ax)
        ax.set_ylabel(f"{label}\nreturn in the sub-episode")
        ax.legend(frameon=False, fontsize=7.5, labelcolor=INK_2, loc="center left", bbox_to_anchor=(1.01, 0.5))

    ax = style_axes(axes[2], grid_axis="y")
    for r in runs:
        ax.plot(x, r["rounds_per_ep"][:n], color=tint(INK_2, 0.3), lw=0.7)
    ax.plot(x, mean("rounds_per_ep"), color=INK_2, lw=1.5)
    ax.set_ylabel("PBRR rounds\nper episode")

    ax = style_axes(axes[3], grid_axis="y")
    for key, c, lab in (("off_0_3", PROXY_COLOR, "on the exploit off-window (sub-episodes 0-3)"),
                        ("win_0_3", INK, "on the exploit in an audit window (sub-episodes 0-3)"),
                        ("win_final", TRUE_COLOR, "on the exploit in the final window (sub-episode 4)")):
        ax.plot(x, mean(key), color=c, lw=1.4, label=lab)
    ax.set_ylim(-0.03, 1.03)
    ax.set_ylabel("fraction")
    ax.legend(frameon=False, fontsize=7.5, labelcolor=INK_2, loc="center left", bbox_to_anchor=(1.01, 0.5))

    ax = style_axes(axes[4], grid_axis="y")
    for r in runs:
        ax.scatter(np.asarray(r["pbrr_steps"]) / 1e6, r["pbrr_gE"], s=6, color=PROXY_COLOR, linewidths=0,
                   alpha=0.6, rasterized=True)
    ax.axhline(0, color=MUTED, lw=0.8)
    ax.set_ylabel("learned g on dwelling\nat the exploit, per round")
    ax.set_xlabel("training steps (millions)")
    ax.set_xlim(0, x[-1] if len(x) else 1)
    fig.suptitle(title, x=0.02, ha="left", va="bottom", color=INK, fontsize=11, y=0.995)
    fig.subplots_adjust(hspace=0.15, top=0.97)
    add_subtitle(axes[-1], subtitle, dy=-42, width=150)
    return save_figure(fig, filename)
