"""Step 1 figures. Conventions come from src/plotting.py (palette, recessive chrome,
one y-scale per axes). Reward is always reported **per round** (sub-episode): the
round return starts again from 0 at every boundary, never accumulated over an
episode or over training. Proxy is the exploitation hue (orange), true reward the
oversight hue (blue), everywhere in the Step 1 figures.

* ``plot_training_curves``    training curves over every episode: proxy / true return
                              per round, corrections, and when the agent leaves the tile;
* ``plot_within_episode``     cumulative reward within each round of one episode,
                              dropping back to 0 at each boundary;
* ``plot_training_heatmap``   when in each round the agent exploits, over training;
* ``plot_occupancy_panels`` / ``plot_by_k``  bonus occupancy and per-k sweeps.
"""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from .plotting import AXIS as AXIS_LINE
from .plotting import GRID, INK, INK_2, MUTED, SEQ_BLUE, SERIES, add_subtitle, save_figure, style_axes, tint
from .plotting import SURFACE as SURFACE_C

__all__ = ["plot_episode_max", "plot_proxy_ceiling", "plot_training_timeline", "plot_training_curves", "plot_within_episode", "plot_occupancy_panels", "plot_by_k",
           "plot_training_heatmap", "K_COLORS", "PROXY_COLOR", "TRUE_COLOR"]

# k = 0..4 on one blue ramp, light -> dark (darkest = final sub-episode).
K_COLORS = SEQ_BLUE[2:7]
PROXY_COLOR, TRUE_COLOR = SERIES[1], SERIES[0]
WINDOW_FILL = tint(MUTED, 0.16)   # neutral, so it never reads as the proxy hue


def _shade_windows(ax, cfg, ymax=1.0):
    for k in range(cfg.n_sub):
        lo = k * cfg.t_sub + cfg.t_sub - cfg.window
        ax.axvspan(lo, (k + 1) * cfg.t_sub, color=WINDOW_FILL, lw=0, zorder=0)
    for k in range(1, cfg.n_sub):
        ax.axvline(k * cfg.t_sub, color=GRID, lw=1.0, zorder=1)


def plot_occupancy_panels(cfg, panels, filename, title, subtitle=None, ylabel="P(bonus)"):
    """``panels``: list of (panel title, cfg_for_panel, y over t, optional reference y).

    The reference (e.g. the exact DP optimum, drawn under a learned policy) is a
    thin muted line, so the learned curve stays the primary mark.
    """
    n = len(panels)
    fig, axes = plt.subplots(n, 1, figsize=(8.4, 1.55 * n + 0.8), sharex=True, squeeze=False)
    axes = axes[:, 0]
    has_ref = any(len(p) > 3 and p[3] is not None for p in panels)
    for ax, panel in zip(axes, panels):
        name, pcfg, y = panel[:3]
        ref = panel[3] if len(panel) > 3 else None
        style_axes(ax, grid_axis="y")
        _shade_windows(ax, pcfg)
        t = np.arange(len(y))
        if ref is not None:
            ax.plot(t, ref, color=MUTED, lw=1.2, ls=(0, (3, 2)), zorder=2)
        ax.plot(t, y, color=SERIES[0], lw=1.6, zorder=3, drawstyle="steps-post")
        ax.set_ylim(-0.05, 1.08)
        ax.set_yticks([0, 1])
        ax.set_ylabel(ylabel)
        ax.text(0.005, 1.02, name, transform=ax.transAxes, ha="left", va="bottom",
                fontsize=9, color=INK)
    axes[-1].set_xlabel("step t within the 500-step episode (sub-episode boundaries every 100)")
    axes[-1].set_xlim(0, len(panels[0][2]))
    handles = [Patch(color=WINDOW_FILL, label="audit window (last W steps)")]
    handles.append(Line2D([], [], color=SERIES[0], lw=1.6, label="policy"))
    if has_ref:
        handles.append(Line2D([], [], color=MUTED, lw=1.2, ls=(0, (3, 2)), label="exact DP optimum"))
    fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.1, 0.985), frameon=False,
               fontsize=8.5, labelcolor=INK_2, ncol=len(handles))
    fig.suptitle(title, x=0.02, ha="left", va="bottom", color=INK, fontsize=11, y=1.025)
    fig.subplots_adjust(hspace=0.45, top=0.97)
    return save_figure(fig, filename, subtitle)


def plot_by_k(x, series_by_k, filename, title, xlabel, ylabel, subtitle=None, ylim=None,
              extra_panels=()):
    """One line per sub-episode k (sequential ramp), plus optional single-series panels
    ``extra_panels`` = [(ylabel, y)] stacked below on the shared x axis."""
    n = 1 + len(extra_panels)
    fig, axes = plt.subplots(n, 1, figsize=(7.2, 2.7 * n + 0.6), sharex=True, squeeze=False)
    axes = axes[:, 0]
    ax = style_axes(axes[0])
    for k, y in enumerate(series_by_k):
        ax.plot(x, y, color=K_COLORS[k], lw=2.0, zorder=3, drawstyle="steps-mid",
                label=f"k = {k}" + (" (final)" if k == len(series_by_k) - 1 else ""))
    ax.set_ylabel(ylabel)
    if ylim:
        ax.set_ylim(*ylim)
    ax.legend(frameon=False, fontsize=8.5, labelcolor=INK_2, loc="best")
    for ax2, (yl, y) in zip(axes[1:], extra_panels):
        style_axes(ax2)
        ax2.plot(x, y, color=SERIES[0], lw=2.0, zorder=3)
        ax2.set_ylabel(yl)
    axes[-1].set_xlabel(xlabel)
    fig.suptitle(title, x=0.02, ha="left", color=INK, fontsize=11, y=1.01)
    fig.subplots_adjust(hspace=0.25, top=0.95)
    return save_figure(fig, filename, subtitle)


def plot_training_heatmap(cfg, timesteps, occupancy, filename, title, subtitle=None):
    """occupancy: (n_evals, t_ep) P(bonus | unpatched). One small multiple per k,
    tau on x, training progress on y, a single-hue sequential colormap."""
    from matplotlib.colors import LinearSegmentedColormap

    cmap = LinearSegmentedColormap.from_list("seq", ["#fcfcfb", *SEQ_BLUE])
    fig, axes = plt.subplots(1, cfg.n_sub, figsize=(2.2 * cfg.n_sub + 1.0, 3.4), sharey=True)
    occ = np.asarray(occupancy).reshape(len(timesteps), cfg.n_sub, cfg.t_sub)
    ts = np.asarray(timesteps) / 1e6
    for k, ax in enumerate(axes):
        im = ax.imshow(occ[:, k, :], aspect="auto", origin="lower", cmap=cmap, vmin=0, vmax=1,
                       extent=(0, cfg.t_sub, ts[0], ts[-1]), interpolation="nearest")
        ax.axvline(cfg.t_sub - cfg.window, color=SERIES[1], lw=1.2)
        ax.set_title(f"k = {k}" + (" (final)" if k == cfg.n_sub - 1 else ""), fontsize=9, color=INK)
        ax.set_xlabel("τ (step in sub-episode)")
        ax.tick_params(colors=MUTED, labelcolor=INK_2, length=3)
        for s in ax.spines.values():
            s.set_visible(False)
    axes[0].set_ylabel("training steps (M)")
    cb = fig.colorbar(im, ax=axes, fraction=0.02, pad=0.01)
    cb.set_label("P(bonus | loophole open)", color=INK_2)
    cb.outline.set_visible(False)
    fig.suptitle(title, x=0.02, ha="left", color=INK, fontsize=11, y=1.03)
    return save_figure(fig, filename, subtitle)


# Proxy and true live on scales ~80x apart (a round pays up to 8,700 proxy but only
# -100..+22 true), so they always get their own rows -- never one shared y axis.
ROWS = (("proxy", "proxy reward", PROXY_COLOR), ("true", "true reward", TRUE_COLOR))


def _ramp(hex_color):
    """Sequential ramp of one hue, light -> full -> dark (for 'training progress')."""
    from matplotlib.colors import LinearSegmentedColormap

    return LinearSegmentedColormap.from_list(
        hex_color, [tint(hex_color, 0.22), hex_color, tint(hex_color, 0.55, base=INK)])


def _col_title(ax, text):
    ax.text(0.0, 1.06, text, transform=ax.transAxes, ha="left", va="bottom", fontsize=9.5, color=INK)


def _thousands(ax):
    from matplotlib.ticker import FuncFormatter

    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))


def _shades(cmap, n):
    return [cmap(v) for v in np.linspace(0.3, 1.0, n)]


def plot_training_curves(columns, n_sub, filename, title, subtitle=None):
    """Training curves over every episode, one column per condition.

    Rows: (1) proxy return in round k, (2) true return in round k -- one line per
    round k = 0..K-1, light -> dark, own y scales; (3) fraction of runs corrected by
    the overseer before the final round; (4) the step within the round at which the
    agent leaves the exploit tile (exact evaluation; the audit window shaded).

    ``columns``: list of dicts with keys name, proxy (n_ep, K), true (n_ep, K),
    corrected (n_seeds, n_ep), eval_ep (n_eval,), leave (n_eval, K), and DP
    references dp_proxy (K,), dp_true (K,), dp_corrected (scalar), dp_leave (K,).
    """
    n = len(columns)
    fig, axes = plt.subplots(4, n, figsize=(6.0 * n + 1.6, 10.2), squeeze=False, sharex="col",
                             sharey="row", gridspec_kw=dict(height_ratios=[1.2, 1.0, 0.7, 0.9]))
    grey = _ramp(INK_2)
    for j, col in enumerate(columns):
        ep = np.arange(1, len(col["proxy"]) + 1)
        for i, (key, label, color) in enumerate(ROWS):
            ax = style_axes(axes[i, j], grid_axis="y")
            for v in np.unique(np.round(col[f"dp_{key}"], 6)):
                ax.axhline(v, color=MUTED, lw=1.0, ls=(0, (3, 2)), zorder=2)
            for k, c in enumerate(_shades(_ramp(color), n_sub)):
                ax.plot(ep, col[key][:, k], color=c, lw=1.3, zorder=3 + k,
                        label=f"round {k}" + (" (last)" if k == n_sub - 1 else ""))
            _thousands(ax)
            if j == 0:
                ax.set_ylabel(f"{label}\nreturn in the round")
            if j == n - 1:
                ax.legend(frameon=False, fontsize=8, labelcolor=INK_2, loc="center left",
                          bbox_to_anchor=(1.01, 0.5))
        ax = style_axes(axes[2, j], grid_axis="y")
        ax.axhline(col["dp_corrected"], color=MUTED, lw=1.0, ls=(0, (3, 2)), zorder=2)
        for row in col["corrected"]:
            ax.plot(ep, row, color=tint(INK_2, 0.3), lw=0.8, zorder=3)
        ax.plot(ep, np.mean(col["corrected"], axis=0), color=INK_2, lw=1.6, zorder=4)
        ax.set_ylim(-0.05, 1.05)
        if j == 0:
            ax.set_ylabel("fraction of runs\ncorrected")
        if j == n - 1:
            ax.legend(handles=[Line2D([], [], color=INK_2, lw=1.6, label="seed mean"),
                               Line2D([], [], color=tint(INK_2, 0.3), lw=0.8, label="each seed")],
                      frameon=False, fontsize=8, labelcolor=INK_2, loc="center left",
                      bbox_to_anchor=(1.01, 0.5))
        ax = style_axes(axes[3, j], grid_axis="y")
        T = 100
        ax.axhspan(col["window_start"], T, color=WINDOW_FILL, lw=0, zorder=0)
        for v in np.unique(col["dp_leave"][~np.isnan(col["dp_leave"])]):
            ax.axhline(v, color=MUTED, lw=1.0, ls=(0, (3, 2)), zorder=2)
        for k, c in enumerate(_shades(grey, n_sub)):
            ax.plot(col["eval_ep"], col["leave"][:, k], color=c, lw=1.3, marker="o", ms=3, zorder=3 + k,
                    label=f"round {k}")
        ax.set_ylim(0, 104)
        if j == 0:
            ax.set_ylabel("step the agent\nleaves the exploit")
        if j == n - 1:
            ax.legend(handles=ax.get_legend_handles_labels()[0]
                      + [Patch(color=WINDOW_FILL, label="audit window")],
                      frameon=False, fontsize=8, labelcolor=INK_2, loc="center left",
                      bbox_to_anchor=(1.01, 0.5))
        axes[3, j].set_xlabel("training episode (5 rounds = 5 PPO updates each)")
        axes[3, j].set_xlim(0, len(ep))
        _col_title(axes[0, j], col["name"])
    fig.legend(handles=[Line2D([], [], color=MUTED, lw=1.0, ls=(0, (3, 2)), label="exact DP optimum")],
               loc="lower left", bbox_to_anchor=(0.06, 0.985), frameon=False, fontsize=8.5,
               labelcolor=INK_2)
    fig.suptitle(title, x=0.02, ha="left", va="bottom", color=INK, fontsize=11, y=1.01)
    fig.subplots_adjust(hspace=0.16, wspace=0.06, top=0.95)
    add_subtitle(axes[3, 0], subtitle, dy=-44, width=165)
    return save_figure(fig, filename)


def _round_cumulative(cfg, r_t):
    """Per-step rewards (..., t_ep) -> x (n,), y (..., n): cumulative reward within each
    round, restarting at 0 at every boundary (a vertical drop at each boundary)."""
    r = np.asarray(r_t, float)
    lead = r.shape[:-1]
    r = r.reshape(lead + (cfg.n_sub, cfg.t_sub))
    zeros = np.zeros(lead + (cfg.n_sub, 1))
    y = np.concatenate([zeros, np.cumsum(r, axis=-1)], axis=-1).reshape(lead + (-1,))
    x = (np.arange(cfg.n_sub)[:, None] * cfg.t_sub + np.arange(cfg.t_sub + 1)[None, :]).ravel()
    return x, y


def plot_within_episode(cfg, columns, filename, title, subtitle=None, ep_label="training episode"):
    """Reward within each round of an episode, restarting at 0 every round. One column
    per condition; proxy top row, true bottom row (own scales).

    ``columns``: list of (name, proxy, true, ref_proxy_t, ref_true_t). ``proxy`` and
    ``true`` are either one curve (t_ep,) or a stack of episodes (n_ep, t_ep); a stack
    is drawn as one line per episode, coloured light -> dark by episode index on a
    one-hue ramp, with a colour bar. Refs (exact DP, per-step) may be None.
    """
    from matplotlib.colors import Normalize
    from matplotlib.cm import ScalarMappable

    n = len(columns)
    fig, axes = plt.subplots(2, n, figsize=(5.6 * n + 1.2, 5.8), squeeze=False, sharex=True,
                             sharey="row", gridspec_kw=dict(height_ratios=[1.25, 1.0]))
    has_ref, mappables = False, {}
    for j, (name, proxy, true, rp, rt) in enumerate(columns):
        for i, ((key, label, color), y, ref) in enumerate(zip(ROWS, (proxy, true), (rp, rt))):
            ax = style_axes(axes[i, j], grid_axis="y")
            _shade_windows(ax, cfg)
            ax.axhline(0, color=AXIS_LINE, lw=0.8, zorder=1)
            x, yy = _round_cumulative(cfg, y)
            if yy.ndim == 1:
                ax.plot(x, yy, color=color, lw=1.8, zorder=3)
            else:
                # One Line2D per episode, NaN-broken between rounds (no connectors).
                # A LineCollection here renders stray segments under the tight-bbox save.
                cmap, norm = _ramp(color), Normalize(0, len(yy) - 1)
                L = cfg.t_sub + 1
                xb = np.concatenate([np.append(x[k * L:(k + 1) * L], np.nan) for k in range(cfg.n_sub)])
                for e, row in enumerate(yy):
                    yb = np.concatenate([np.append(row[k * L:(k + 1) * L], np.nan) for k in range(cfg.n_sub)])
                    ax.plot(xb, yb, color=cmap(norm(e)), lw=0.7, zorder=3)
                mappables[i] = ScalarMappable(norm=Normalize(1, len(yy)), cmap=cmap)
            if ref is not None:
                has_ref = True
                ax.plot(*_round_cumulative(cfg, ref), color=INK, lw=1.0, ls=(0, (3, 2)), zorder=4)
            _thousands(ax)
            if j == 0:
                ax.set_ylabel(f"{label}\ncumulative in the round")
        _col_title(axes[0, j], name)
    for ax in axes[1]:
        ax.set_xticks(np.arange(cfg.n_sub + 1) * cfg.t_sub)
        ax.set_xticks((np.arange(cfg.n_sub) + 0.5) * cfg.t_sub, minor=True)
        ax.set_xticklabels([f"round {k}" for k in range(cfg.n_sub)], minor=True)
        ax.tick_params(axis="x", which="minor", length=0, pad=14, labelcolor=MUTED, labelsize=8)
        ax.set_xlabel("step within the 500-step episode")
    axes[0, 0].set_xlim(0, cfg.t_ep)
    fig.subplots_adjust(hspace=0.22, wspace=0.06, top=0.92)
    for i, m in mappables.items():
        cb = fig.colorbar(m, ax=axes[i, :].tolist(), fraction=0.025, pad=0.012)
        cb.set_label(ep_label, color=INK_2, fontsize=8.5)
        cb.outline.set_visible(False)
        cb.ax.tick_params(colors=MUTED, labelcolor=INK_2, labelsize=8)
    handles = [Patch(color=WINDOW_FILL, label="audit window (last 10 steps of a round)")]
    if has_ref:
        handles.append(Line2D([], [], color=INK, lw=1.0, ls=(0, (3, 2)), label="exact DP optimum"))
    fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.06, 0.975), frameon=False,
               fontsize=8.5, labelcolor=INK_2, ncol=len(handles))
    fig.suptitle(title, x=0.02, ha="left", va="bottom", color=INK, fontsize=11, y=1.015)
    add_subtitle(axes[1, 0], subtitle, dy=-52, width=150)
    return save_figure(fig, filename)


REF_STYLES = ((0, (1.2, 1.6)), (0, (5, 2)))   # dotted = ceiling, dashed = monitor-avoiding


def _draw_refs(ax, refs):
    for (value, _), ls in zip(refs, REF_STYLES):
        ax.axhline(value, color=INK, lw=1.0, ls=ls, zorder=5)


def _draw_overview(cfg, ax0, sp, st, edges, windows, per_round, refs=()):
    """Row 0 of ``plot_training_timeline``: the whole run, one flat segment per round."""
    from matplotlib.patches import Rectangle

    K = cfg.n_sub
    ax0 = style_axes(ax0, grid_axis="y")
    _draw_refs(ax0, refs)
    ax0.stairs(sp.sum(axis=1), edges / 1e6, color=PROXY_COLOR, lw=0.9, zorder=3, rasterized=True)
    ax0.stairs(st.sum(axis=1), edges / 1e6, color=TRUE_COLOR, lw=0.9, zorder=4, rasterized=True)
    ax0.axhline(0, color=AXIS_LINE, lw=0.8, zorder=1)
    ax0.set_xlim(0, edges[-1] / 1e6)
    ax0.set_xlabel("training steps (millions)")
    ax0.set_ylabel("return in the\nsub-episode")
    _thousands(ax0)
    _col_title(ax0, "Whole training run: each sub-episode drawn at its return")
    ylo, yhi = ax0.get_ylim()
    for i, (e0, n, label) in enumerate(windows):
        x0, x1 = e0 * K * per_round / 1e6, (e0 + n) * K * per_round / 1e6
        ax0.add_patch(Rectangle((x0, ylo), x1 - x0, yhi - ylo, facecolor="none", edgecolor=INK_2,
                                lw=1.0, zorder=5))
        ax0.text((x0 + x1) / 2, yhi, "ABCDEFG"[i], ha="center", va="bottom", fontsize=9, color=INK)

    return ylo, yhi


def plot_training_timeline(cfg, step_proxy, step_true, windows, filename, title, subtitle=None,
                           steps_per_tick=1, overview=True, refs=(),
                           received_label="proxy reward (what the agent receives)"):
    """The training run on its real time axis: x = training steps, y = reward
    accumulated within the current sub-episode (round), back to 0 at each boundary.
    Proxy and true share the y axis so their divergence is read directly.

    ``step_proxy`` / ``step_true``: (n_rounds, t_sub) reward received at every step of
    every round (mean over the parallel envs). ``steps_per_tick``: training steps per
    env step (= number of parallel envs, so x counts PPO samples).
    ``windows``: list of (first_episode, n_episodes, label) for the zoomed rows.

    Row 0: the whole run, each round drawn as a flat segment at its return (the top
    of its tooth). Rows 1..: zooms in which every round is the full tooth, with the
    audit windows shaded and every episode boundary (reward reset) marked.
    ``overview=False`` drops row 0 and draws only the zooms (full width each).
    ``refs``: up to two (value, label) horizontal reference returns per sub-episode,
    drawn dotted then dashed in every row (e.g. the proxy ceiling and the best
    monitor-avoiding return).
    """
    K, T = cfg.n_sub, cfg.t_sub
    sp, st = np.asarray(step_proxy, float), np.asarray(step_true, float)
    n_rounds = len(sp)
    per_round = T * steps_per_tick
    edges = np.arange(n_rounds + 1) * per_round
    nz = len(windows)
    top = 1 if overview else 0
    fig, axes = plt.subplots(top + nz, 1, figsize=(11.5, (2.9 if overview else 1.0) + 2.35 * nz),
                             gridspec_kw=dict(height_ratios=[1.25] * top + [1.0] * nz), squeeze=False)
    axes = axes[:, 0]
    if not overview:  # shared y range for the zooms, from the data they show
        tops = np.concatenate([np.cumsum(sp[e0 * K:(e0 + n) * K], axis=1).ravel() for e0, n, _ in windows])
        ylo, yhi = -300.0, max(9200.0, float(tops.max()) * 1.05)
    else:
        ylo, yhi = _draw_overview(cfg, axes[0], sp, st, edges, windows, per_round, refs)

    L = T + 1
    for i, (e0, n, label) in enumerate(windows):
        ax = style_axes(axes[top + i], grid_axis="y")

        r0, r1 = e0 * K, min((e0 + n) * K, n_rounds)
        xs, yp, yt = [], [], []
        for r in range(r0, r1):
            x = (r * T + np.arange(L)) * steps_per_tick / 1e3
            xs.append(np.append(x, np.nan))
            yp.append(np.append(np.concatenate([[0.0], np.cumsum(sp[r])]), np.nan))
            yt.append(np.append(np.concatenate([[0.0], np.cumsum(st[r])]), np.nan))
            ax.axvspan((r * T + T - cfg.window) * steps_per_tick / 1e3, (r + 1) * T * steps_per_tick / 1e3,
                       color=WINDOW_FILL, lw=0, zorder=0)
        ax.plot(np.concatenate(xs), np.concatenate(yp), color=PROXY_COLOR, lw=1.3, zorder=3)
        ax.plot(np.concatenate(xs), np.concatenate(yt), color=TRUE_COLOR, lw=1.3, zorder=4)
        ax.axhline(0, color=AXIS_LINE, lw=0.8, zorder=1)
        _draw_refs(ax, refs)
        for e in range(e0, e0 + n + 1):
            xe = e * K * T * steps_per_tick / 1e3
            ax.axvline(xe, color=INK_2, lw=0.9, ls=(0, (4, 3)), zorder=2)
            if e < e0 + n:
                ax.text(xe + 0.5 * K * T * steps_per_tick / 1e3, 1.0, f"episode {e}",
                        transform=ax.get_xaxis_transform(), ha="center", va="bottom", fontsize=8,
                        color=INK_2)
        ax.set_xlim(r0 * T * steps_per_tick / 1e3, r1 * T * steps_per_tick / 1e3)
        ax.set_ylim(min(-300, ylo), max(9200, yhi))
        _thousands(ax)
        ax.set_ylabel("reward so far in\nthe sub-episode")
        ax.set_xlabel("training steps (thousands)")
        ax.text(0.0, 1.13, f"{'ABCDEFG'[i]}. {label}" if overview else label, transform=ax.transAxes,
                ha="left", va="bottom", fontsize=9.5, color=INK)
    handles = [Line2D([], [], color=PROXY_COLOR, lw=1.6, label=received_label),
               Line2D([], [], color=TRUE_COLOR, lw=1.6, label="true reward"),
               Patch(color=WINDOW_FILL, label="audit window (last 10 steps of each sub-episode)"),
               Line2D([], [], color=INK_2, lw=0.9, ls=(0, (4, 3)), label="episode boundary: reward function reset")]
    handles += [Line2D([], [], color=INK, lw=1.0, ls=ls, label=label) for (_, label), ls in zip(refs, REF_STYLES)]
    # place legend and title a fixed distance (inches) above the axes, whatever the height
    h = fig.get_figheight()
    top_ax = 1.0 - 0.9 / h          # room for the panel label (~0.35 in) above the top axes
    fig.subplots_adjust(hspace=0.75, top=top_ax)
    fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.06, top_ax + 0.42 / h), frameon=False,
               fontsize=8.5, labelcolor=INK_2, ncol=2)
    rows = -(-len(handles) // 2)    # legend rows (2 columns)
    fig.suptitle(title, x=0.02, ha="left", va="bottom", color=INK, fontsize=11,
                 y=top_ax + (0.5 + 0.25 * rows) / h)
    add_subtitle(axes[-1], subtitle, dy=-40, width=165)
    return save_figure(fig, filename)


def plot_proxy_ceiling(steps, proxy0, true0, eval_steps, window0, ceiling, avoid, filename, title,
                       subtitle=None):
    """Sub-episode 0 of every episode -- the one that always runs under the original,
    not-yet-updated proxy -- against the maximum proxy return achievable in it.

    ``steps``: (n_ep,) training step of each episode's sub-episode 0; ``proxy0`` /
    ``true0``: (n_seeds, n_ep) its received return; ``eval_steps`` / ``window0``:
    (n_eval,), (n_seeds, n_eval) exact-eval P(agent is on the exploit in the audit
    window of sub-episode 0). ``ceiling``: max proxy return (dwell all 100 steps);
    ``avoid``: best return that avoids the monitor (step off before the audit).
    """
    fig, (ax, ax2) = plt.subplots(2, 1, figsize=(10.5, 6.6), sharex=True,
                                  gridspec_kw=dict(height_ratios=[1.6, 1.0]))
    style_axes(ax, grid_axis="y")
    x = np.asarray(steps) / 1e6
    ax.axhline(ceiling, color=INK, lw=1.1, ls=REF_STYLES[0], zorder=5)
    ax.axhline(avoid, color=INK, lw=1.1, ls=REF_STYLES[1], zorder=5)
    for y in proxy0:
        ax.plot(x, y, color=tint(PROXY_COLOR, 0.35), lw=0.7, zorder=2)
    ax.plot(x, np.mean(proxy0, axis=0), color=PROXY_COLOR, lw=1.6, zorder=3)
    ax.plot(x, np.mean(true0, axis=0), color=TRUE_COLOR, lw=1.6, zorder=3)
    ax.axhline(0, color=AXIS_LINE, lw=0.8, zorder=1)
    _thousands(ax)
    ax.set_ylabel("return in sub-episode 0\n(reward not yet updated)")
    ax.text(x[-1], ceiling, f"max proxy return {ceiling:,.0f}  ", ha="right", va="bottom", fontsize=8.5, color=INK)
    ax.text(x[-1], avoid, f"best monitor-avoiding return {avoid:,.0f}  ", ha="right", va="top", fontsize=8.5,
            color=INK)

    style_axes(ax2, grid_axis="y")
    ex = np.asarray(eval_steps) / 1e6
    for y in window0:
        ax2.plot(ex, y, color=tint(INK_2, 0.35), lw=0.7, zorder=2)
    ax2.plot(ex, np.mean(window0, axis=0), color=INK_2, lw=1.6, marker="o", ms=3, zorder=3)
    ax2.set_ylim(-0.03, 1.03)
    ax2.set_ylabel("P(on the exploit during\nthe audit of sub-episode 0)")
    ax2.set_xlabel("training steps (millions)")
    ax2.set_xlim(0, x[-1])
    handles = [Line2D([], [], color=PROXY_COLOR, lw=1.6, label="proxy return (seed mean)"),
               Line2D([], [], color=tint(PROXY_COLOR, 0.35), lw=0.7, label="proxy return (each seed)"),
               Line2D([], [], color=TRUE_COLOR, lw=1.6, label="true return (seed mean)"),
               Line2D([], [], color=INK, lw=1.1, ls=REF_STYLES[0], label="max proxy return: exploit all 100 steps"),
               Line2D([], [], color=INK, lw=1.1, ls=REF_STYLES[1], label="best return that avoids the monitor"),
               Line2D([], [], color=INK_2, lw=1.6, marker="o", ms=3, label="audit-window exploitation (exact eval)")]
    fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.07, 0.965), frameon=False, fontsize=8.5,
               labelcolor=INK_2, ncol=3)
    fig.suptitle(title, x=0.02, ha="left", va="bottom", color=INK, fontsize=11, y=1.03)
    fig.subplots_adjust(hspace=0.12, top=0.93)
    add_subtitle(ax2, subtitle, dy=-42, width=150)
    return save_figure(fig, filename)


def plot_episode_max(steps, env_proxy, ceiling, avoid, filename, title, subtitle=None, hit_tol=1.0):
    """Max proxy return over the sub-episodes of each episode, for every trial.

    ``env_proxy``: (n_trials, n_ep, K) proxy return of every sub-episode of every
    episode of every trial (trial = one parallel env of one seed). Top: across trials,
    the median and 10-90% band of (a) the max over all K sub-episodes and (b) the max
    over sub-episodes 0..K-2, whose audits can still change the reward. Bottom: the
    fraction of trials whose episode reaches the proxy ceiling in each group.
    """
    x = np.asarray(steps) / 1e6
    E = np.asarray(env_proxy, float)
    max_all, max_early = E.max(axis=2), E[:, :, :-1].max(axis=2)
    fig, (ax, ax2) = plt.subplots(2, 1, figsize=(10.5, 6.8), sharex=True,
                                  gridspec_kw=dict(height_ratios=[1.6, 1.0]))
    style_axes(ax, grid_axis="y")
    ax.axhline(ceiling, color=INK, lw=1.1, ls=REF_STYLES[0], zorder=5)
    ax.axhline(avoid, color=INK, lw=1.1, ls=REF_STYLES[1], zorder=5)
    early_c, all_c = PROXY_COLOR, tint(PROXY_COLOR, 0.55, base=INK)
    for m, c in ((max_all, all_c), (max_early, early_c)):
        lo, med, hi = np.percentile(m, [0, 50, 100] if len(m) < 10 else [10, 50, 90], axis=0)
        ax.fill_between(x, lo, hi, color=tint(c, 0.22), lw=0, zorder=2)
        ax.plot(x, med, color=c, lw=1.5, zorder=3)
    ax.text(x[-1], ceiling, f"max proxy return {ceiling:,.0f}  ", ha="right", va="bottom", fontsize=8.5, color=INK)
    ax.text(x[-1], avoid, f"best monitor-avoiding return {avoid:,.0f}  ", ha="right", va="top", fontsize=8.5, color=INK)
    _thousands(ax)
    ax.set_ylabel("max proxy return over the\nsub-episodes of an episode")

    style_axes(ax2, grid_axis="y")
    for m, c in ((max_all, all_c), (max_early, early_c)):
        ax2.plot(x, (m >= ceiling - hit_tol).mean(axis=0), color=c, lw=1.3, zorder=3)
    ax2.set_ylim(-0.03, 1.03)
    ax2.set_ylabel(f"fraction of trials\nwithin {hit_tol:,.0f} of the max")
    ax2.set_xlabel("training steps (millions)")
    ax2.set_xlim(0, x[-1])
    handles = [Line2D([], [], color=all_c, lw=1.5, label="max over all 5 sub-episodes"),
               Line2D([], [], color=early_c, lw=1.5, label="max over sub-episodes 0-3, whose audits matter"),
               Line2D([], [], color=INK, lw=1.1, ls=REF_STYLES[0], label="max proxy return: exploit all 100 steps"),
               Line2D([], [], color=INK, lw=1.1, ls=REF_STYLES[1], label="best return that avoids the monitor")]
    fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.07, 0.965), frameon=False, fontsize=8.5,
               labelcolor=INK_2, ncol=2)
    fig.suptitle(title, x=0.02, ha="left", va="bottom", color=INK, fontsize=11, y=1.03)
    fig.subplots_adjust(hspace=0.12, top=0.93)
    add_subtitle(ax2, subtitle, dy=-42, width=150)
    return save_figure(fig, filename)


TRIGGER_COLOR = "#cf3a3a"


def plot_timeline_split(cfg, step_received, step_true, caught, windows, filename, title, subtitle=None,
                        steps_per_tick=1, refs=(), received_label="proxy reward (what the agent receives)"):
    """Variant of ``plot_training_timeline`` (mentor's request): received and true
    reward on SEPARATE rows with their own y scales, and every audit window marked
    by whether the reward-correcting monitor triggered there.

    ``caught``: (n_rounds,) fraction of the parallel envs whose audit at the end of
    that sub-episode triggered a correction. The final sub-episode's audit never
    corrects (the reward resets), so it is always drawn as not triggering.
    """
    from matplotlib.gridspec import GridSpec, GridSpecFromSubplotSpec
    from matplotlib.transforms import blended_transform_factory

    K, T = cfg.n_sub, cfg.t_sub
    sp, st = np.asarray(step_received, float), np.asarray(step_true, float)
    caught = np.asarray(caught, float).copy()
    caught[np.arange(len(caught)) % K == K - 1] = 0.0      # last audit: no correction
    n_rounds = len(sp)
    per_round = T * steps_per_tick
    edges = np.arange(n_rounds + 1) * per_round
    panels = [None] + list(windows)
    fig = plt.figure(figsize=(11.5, 3.3 * len(panels) + 0.6))
    outer = GridSpec(len(panels), 1, figure=fig, hspace=0.62)
    pairs = []
    for i in range(len(panels)):
        inner = GridSpecFromSubplotSpec(2, 1, subplot_spec=outer[i], height_ratios=[1.0, 0.5], hspace=0.08)
        a = fig.add_subplot(inner[0])
        b = fig.add_subplot(inner[1], sharex=a)
        a.tick_params(labelbottom=False)
        pairs.append((style_axes(a, grid_axis="y"), style_axes(b, grid_axis="y")))

    # whole run: one flat segment per sub-episode, triggered audits as a red rug
    a, b = pairs[0]
    a.stairs(sp.sum(axis=1), edges / 1e6, color=PROXY_COLOR, lw=0.9, rasterized=True)
    b.stairs(st.sum(axis=1), edges / 1e6, color=TRUE_COLOR, lw=0.9, rasterized=True)
    _draw_refs(a, refs)
    trans = blended_transform_factory(a.transData, a.transAxes)
    for r in np.flatnonzero(caught > 0):
        a.plot([edges[r + 1] / 1e6] * 2, [0.9, 1.0], transform=trans, color=TRIGGER_COLOR,
               lw=0.6, alpha=0.25 + 0.75 * caught[r], solid_capstyle="butt")
    a.set_xlim(0, edges[-1] / 1e6)
    b.set_xlabel("training steps (millions)")
    _col_title(a, "Whole training run: each sub-episode drawn at its return (red ticks: monitor triggered)")
    for ax, lab in ((a, "received return\nin the sub-episode"), (b, "true return")):
        ax.set_ylabel(lab)
        _thousands(ax)

    L = T + 1
    for i, (e0, n, label) in enumerate(windows):
        a, b = pairs[i + 1]
        r0, r1 = e0 * K, min((e0 + n) * K, n_rounds)
        xs, yp, yt = [], [], []
        for r in range(r0, r1):
            x = (r * T + np.arange(L)) * steps_per_tick / 1e3
            xs.append(np.append(x, np.nan))
            yp.append(np.append(np.concatenate([[0.0], np.cumsum(sp[r])]), np.nan))
            yt.append(np.append(np.concatenate([[0.0], np.cumsum(st[r])]), np.nan))
            w0, w1 = (r * T + T - cfg.window) * steps_per_tick / 1e3, (r + 1) * T * steps_per_tick / 1e3
            fc = tint(TRIGGER_COLOR, 0.2 + 0.6 * caught[r]) if caught[r] > 0 else WINDOW_FILL
            for ax in (a, b):
                ax.axvspan(w0, w1, color=fc, lw=0, zorder=0)
        a.plot(np.concatenate(xs), np.concatenate(yp), color=PROXY_COLOR, lw=1.3, zorder=3)
        b.plot(np.concatenate(xs), np.concatenate(yt), color=TRUE_COLOR, lw=1.3, zorder=3)
        _draw_refs(a, refs)
        for e in range(e0, e0 + n + 1):
            xe = e * K * T * steps_per_tick / 1e3
            for ax in (a, b):
                ax.axvline(xe, color=INK_2, lw=0.9, ls=(0, (4, 3)), zorder=2)
            if e < e0 + n:
                a.text(xe + 0.5 * K * T * steps_per_tick / 1e3, 1.0, f"episode {e}",
                       transform=a.get_xaxis_transform(), ha="center", va="bottom", fontsize=8, color=INK_2)
        a.set_xlim(r0 * T * steps_per_tick / 1e3, r1 * T * steps_per_tick / 1e3)
        b.set_xlabel("training steps (thousands)")
        for ax, lab in ((a, "received reward so\nfar in the sub-episode"), (b, "true reward\nso far")):
            ax.set_ylabel(lab)
            _thousands(ax)
        a.text(0.0, 1.16, f"{'ABCDEFG'[i]}. {label}", transform=a.transAxes, ha="left", va="bottom",
               fontsize=9.5, color=INK)

    handles = [Line2D([], [], color=PROXY_COLOR, lw=1.6, label=received_label),
               Line2D([], [], color=TRUE_COLOR, lw=1.6, label="true reward (own scale, lower rows)"),
               Patch(color=tint(TRIGGER_COLOR, 0.7), label="audit window: monitor TRIGGERED a correction "
                                                           "(shade = fraction of the 16 envs caught)"),
               Patch(color=WINDOW_FILL, label="audit window: monitor did not trigger"),
               Line2D([], [], color=INK_2, lw=0.9, ls=(0, (4, 3)), label="episode boundary: reward function reset")]
    handles += [Line2D([], [], color=INK, lw=1.0, ls=ls, label=lab) for (_, lab), ls in zip(refs, REF_STYLES)]
    h = fig.get_figheight()
    top_ax = 1.0 - 0.9 / h
    fig.subplots_adjust(top=top_ax)
    fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.06, top_ax + 0.42 / h), frameon=False,
               fontsize=8.5, labelcolor=INK_2, ncol=2)
    rows = -(-len(handles) // 2)
    fig.suptitle(title, x=0.02, ha="left", va="bottom", color=INK, fontsize=11,
                 y=top_ax + (0.5 + 0.25 * rows) / h)
    add_subtitle(pairs[-1][1], subtitle, dy=-40, width=165)
    return save_figure(fig, filename)
