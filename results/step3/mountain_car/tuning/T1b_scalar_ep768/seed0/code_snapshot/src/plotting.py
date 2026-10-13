"""Shared plotting harness. Every experiment draws through these functions.

Figure conventions (fixed here so all figures read as one set):

* Phase labels get a fixed colour for the whole repo, assigned by *meaning* --
  slot 1 = oversight works, slot 2 = exploitation in plain view, slot 3 =
  concealment -- so Exp 0's ``exploit_hide`` and Exp 1's ``farm_quiet`` are the
  same colour. Colour follows the entity, never its rank in a given plot.
* Region fills are tints of those hues (mixed toward the surface, not alpha), with
  the full hue on the legend swatch and on boundary lines. Every region also
  carries a direct text label, so identity is never colour-alone.
* Recessive chrome: hairline grid, muted ticks, no top/right spines. Text wears
  ink tokens, never a series colour.
* Never two y-scales on one axes. Two measures of different scale become two
  stacked panels sharing the x axis.
"""

import os
import textwrap

import matplotlib

matplotlib.use("Agg")

import matplotlib.patheffects
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, FancyArrow, Patch, Rectangle

__all__ = [
    "SERIES",
    "LABEL_COLORS",
    "figure_dir",
    "style_axes",
    "save_figure",
    "tint",
    "plot_value_vs_gamma",
    "plot_phase_1d",
    "plot_phase_2d",
    "plot_grid_policy",
    "plot_lines",
    "plot_dumbbell",
]

# --- palette (validated: node scripts/validate_palette.js "#2a78d6,#eb6834,#1baf7a"
# --- --mode light --pairs all -> all checks pass; aqua is sub-3:1 on the light
# --- surface, which is why every region carries a direct label) -----------------
SERIES = ("#2a78d6", "#eb6834", "#1baf7a")
SEQ_BLUE = ("#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b")

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"

# Fixed label -> hue map, shared by Exp 0 and Exp 1.
LABEL_COLORS = {
    # Exp 0
    "comply": SERIES[0],
    "exploit_open": SERIES[1],
    "exploit_hide": SERIES[2],
    # Exp 1 (same meanings, same colours)
    "goto_goal": SERIES[0],
    "farm_loud": SERIES[1],
    "farm_quiet": SERIES[2],
}

LABEL_TEXT = {
    "comply": "comply",
    "exploit_open": "exploit openly",
    "exploit_hide": "hide",
    "goto_goal": "do the task",
    "farm_loud": "farm in plain view",
    "farm_quiet": "farm hidden",
}

plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
        "font.size": 9.5,
        "axes.titlesize": 11,
        "axes.titleweight": "medium",
        "axes.labelsize": 9.5,
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "figure.dpi": 120,
        "savefig.dpi": 170,
        "lines.linewidth": 2.0,
        "lines.solid_capstyle": "round",
    }
)


def figure_dir():
    """<repo root>/figures, created on demand."""
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(os.path.dirname(here), "figures")
    os.makedirs(path, exist_ok=True)
    return path


def tint(hex_color, weight, base=SURFACE):
    """Mix ``hex_color`` toward ``base``. weight=1 -> the hue, 0 -> the surface."""

    def to_rgb(h):
        h = h.lstrip("#")
        return np.array([int(h[i : i + 2], 16) for i in (0, 2, 4)], dtype=float)

    mixed = weight * to_rgb(hex_color) + (1.0 - weight) * to_rgb(base)
    return "#" + "".join(f"{int(round(v)):02x}" for v in mixed)


def style_axes(ax, grid_axis="both"):
    """Recessive chrome: hairline grid behind the marks, muted ticks, 2 spines."""
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(AXIS)
        ax.spines[side].set_linewidth(1.0)
    ax.tick_params(colors=MUTED, labelcolor=INK_2, length=3, width=1.0)
    if grid_axis != "none":
        ax.grid(True, axis=grid_axis, color=GRID, linewidth=0.8, alpha=1.0)
    ax.set_axisbelow(True)
    ax.title.set_color(INK)
    ax.xaxis.label.set_color(INK_2)
    ax.yaxis.label.set_color(INK_2)
    return ax


def _legend(ax, handles, **kw):
    leg = ax.legend(
        handles=handles,
        frameon=False,
        fontsize=8.5,
        labelcolor=INK_2,
        handlelength=1.6,
        **kw,
    )
    return leg


def add_subtitle(ax, text, dy=-46, width=112):
    """Caption below ``ax``, offset a fixed number of points from its bottom edge.

    Offset points rather than figure coordinates: that way the caption cannot land
    on top of the x-axis label whatever the panel layout turns out to be. The text
    is hard-wrapped because ``bbox_inches="tight"`` grows the canvas to fit a long
    single line, which otherwise leaves the plot stranded in a sea of white.
    """
    if not text:
        return
    ax.annotate(
        textwrap.fill(text, width=width),
        xy=(0.0, 0.0),
        xycoords="axes fraction",
        xytext=(0, dy),
        textcoords="offset points",
        ha="left",
        va="top",
        fontsize=8,
        color=MUTED,
        linespacing=1.5,
    )


def halo(artist, width=2.8):
    """Surface-coloured outline so a label stays readable over a filled region."""
    artist.set_path_effects(
        [matplotlib.patheffects.withStroke(linewidth=width, foreground=SURFACE)]
    )
    return artist


def save_figure(fig, filename, subtitle=None):
    """Write to figures/<filename> and return the absolute path."""
    path = os.path.join(figure_dir(), filename)
    if subtitle:
        add_subtitle(fig.axes[-1], subtitle)
    fig.savefig(path, bbox_inches="tight", pad_inches=0.28)
    plt.close(fig)
    return path


# --------------------------------------------------------------------------- #
# 1. value-vs-gamma envelope
# --------------------------------------------------------------------------- #

def plot_value_vs_gamma(
    gammas,
    curves,
    filename,
    title,
    boundaries=None,
    ylabel="value at the open state",
    subtitle=None,
    ylim=None,
):
    """Closed-form strategy values, their upper envelope, and the optimal regions.

    ``curves`` maps a phase label -> array over ``gammas``. The envelope is drawn
    in ink over the top; the region that owns each stretch of gamma is shaded in
    that strategy's tint and directly labelled.
    """
    gammas = np.asarray(gammas, dtype=float)
    labels = list(curves)
    stacked = np.vstack([np.asarray(curves[k], dtype=float) for k in labels])
    winner = stacked.argmax(axis=0)
    envelope = stacked.max(axis=0)

    fig, ax = plt.subplots(figsize=(7.4, 4.5))
    style_axes(ax)

    # shade optimal regions
    seen = set()
    edges = np.flatnonzero(np.diff(winner)) + 1
    for lo, hi in zip(np.r_[0, edges], np.r_[edges, len(gammas)]):
        lab = labels[winner[lo]]
        ax.axvspan(
            gammas[lo],
            gammas[min(hi, len(gammas) - 1)],
            color=tint(LABEL_COLORS[lab], 0.16),
            lw=0,
            zorder=0,
        )
        if hi - lo > 0.06 * len(gammas) and lab not in seen:
            seen.add(lab)
            mid = 0.5 * (gammas[lo] + gammas[min(hi, len(gammas) - 1)])
            halo(
                ax.text(
                    mid,
                    0.965,
                    LABEL_TEXT.get(lab, lab),
                    transform=ax.get_xaxis_transform(),
                    ha="center",
                    va="top",
                    fontsize=8.5,
                    color=INK,
                    zorder=6,
                )
            )

    for i, lab in enumerate(labels):
        ax.plot(gammas, stacked[i], color=LABEL_COLORS[lab], lw=2.0, zorder=3)
    ax.plot(
        gammas, envelope, color=INK, lw=1.2, ls=(0, (1.6, 1.8)), zorder=5,
    )

    if boundaries:
        for g_star, note in boundaries:
            ax.axvline(g_star, color=AXIS, lw=1.0, zorder=2)
            ax.text(
                g_star,
                0.02,
                f"  {note}",
                transform=ax.get_xaxis_transform(),
                rotation=90,
                ha="left",
                va="bottom",
                fontsize=8,
                color=INK_2,
                zorder=6,
            )

    handles = [
        Line2D([], [], color=LABEL_COLORS[k], lw=2.0, label=LABEL_TEXT.get(k, k))
        for k in labels
    ] + [Line2D([], [], color=INK, lw=1.2, ls=(0, (1.6, 1.8)), label="optimal (envelope)")]
    _legend(ax, handles, loc="lower left", bbox_to_anchor=(0.0, 1.0), ncol=4)

    ax.set_xlabel("discount factor  $\\gamma$")
    ax.set_ylabel(ylabel)
    ax.set_title(title, loc="left", pad=30)
    ax.set_xlim(gammas.min(), gammas.max())
    if ylim:
        ax.set_ylim(*ylim)
    return save_figure(fig, filename, subtitle)


# --------------------------------------------------------------------------- #
# 2. one-dimensional phase strip (optionally several stacked panels)
# --------------------------------------------------------------------------- #

def plot_phase_1d(
    x,
    panels,
    filename,
    title,
    xlabel="discount factor  $\\gamma$",
    subtitle=None,
    boundaries=None,
):
    """Stacked categorical bands over one swept parameter.

    ``panels`` is a list of (panel_title, labels_array). ``boundaries`` is a
    matching list of lists of (x, note) to annotate per panel.
    """
    x = np.asarray(x, dtype=float)
    n = len(panels)
    fig, axes = plt.subplots(
        n, 1, figsize=(7.4, 1.35 * n + 1.5), sharex=True, squeeze=False
    )
    axes = axes[:, 0]

    all_labels = []
    for _, labs in panels:
        for l in labs:
            if l not in all_labels:
                all_labels.append(l)
    order = [l for l in ("goto_goal", "farm_loud", "farm_quiet", "comply", "exploit_open", "exploit_hide") if l in all_labels]
    order += [l for l in all_labels if l not in order]

    for k, (panel_title, labs) in enumerate(panels):
        ax = axes[k]
        style_axes(ax, grid_axis="none")
        ax.set_yticks([])
        ax.spines["left"].set_visible(False)
        labs = np.asarray(labs)
        edges = np.flatnonzero(labs[1:] != labs[:-1]) + 1
        for lo, hi in zip(np.r_[0, edges], np.r_[edges, len(x)]):
            lab = labs[lo]
            hi_x = x[min(hi, len(x) - 1)]
            ax.axvspan(x[lo], hi_x, color=tint(LABEL_COLORS[lab], 0.30), lw=0)
            if hi - lo > 0.055 * len(x):
                ax.text(
                    0.5 * (x[lo] + hi_x),
                    0.5,
                    LABEL_TEXT.get(lab, lab),
                    ha="center",
                    va="center",
                    fontsize=8.5,
                    color=INK,
                )
            if lo > 0:
                ax.axvline(x[lo], color=SURFACE, lw=2.0)
        if boundaries and boundaries[k]:
            # Stagger successive callouts vertically: adjacent phase boundaries can
            # sit close enough in x that their labels would overprint.
            for i, (xv, note) in enumerate(boundaries[k]):
                ax.annotate(
                    note,
                    xy=(xv, 1.0),
                    xycoords=("data", "axes fraction"),
                    xytext=(0, 5 + 12 * (i % 2)),
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                    fontsize=8,
                    color=INK_2,
                )
        ax.set_ylabel(
            panel_title, rotation=0, ha="right", va="center", fontsize=9, color=INK
        )
        ax.set_ylim(0, 1)

    axes[-1].set_xlabel(xlabel)
    axes[-1].set_xlim(x.min(), x.max())
    handles = [
        Patch(facecolor=tint(LABEL_COLORS[l], 0.30), edgecolor=LABEL_COLORS[l], label=LABEL_TEXT.get(l, l))
        for l in order
    ]
    # Legend and title both in figure coordinates so their stacking order does not
    # depend on how many panels there are.
    fig.legend(
        handles=handles,
        loc="lower center",
        bbox_to_anchor=(0.5, 1.0),
        frameon=False,
        fontsize=8.5,
        labelcolor=INK_2,
        handlelength=1.6,
        ncol=len(order),
    )
    fig.suptitle(title, x=0.02, ha="left", color=INK, fontsize=11, y=1.11)
    fig.subplots_adjust(hspace=0.35)
    return save_figure(fig, filename, subtitle)


# --------------------------------------------------------------------------- #
# 3. two-dimensional phase diagram
# --------------------------------------------------------------------------- #

def plot_phase_2d(
    xs,
    ys,
    label_grid,
    filename,
    title,
    xlabel,
    ylabel,
    subtitle=None,
    control_line=None,
    annotate=None,
):
    """Categorical phase diagram over two swept parameters.

    ``label_grid`` has shape (len(ys), len(xs)) and holds label strings. Regions
    are tinted, separated by a full-hue boundary contour, and directly labelled at
    their centroid. ``control_line`` draws (value, text) as a horizontal rule --
    used to mark the "gap switched off" edge of the sweep.
    """
    xs = np.asarray(xs, dtype=float)
    ys = np.asarray(ys, dtype=float)
    label_grid = np.asarray(label_grid)

    present = [
        l
        for l in ("goto_goal", "farm_loud", "farm_quiet", "comply", "exploit_open", "exploit_hide")
        if l in set(label_grid.ravel())
    ]
    present += [l for l in sorted(set(label_grid.ravel())) if l not in present]
    idx = {l: i for i, l in enumerate(present)}
    grid = np.vectorize(idx.get)(label_grid).astype(float)

    fig, ax = plt.subplots(figsize=(6.8, 4.8))
    style_axes(ax, grid_axis="none")
    cmap = ListedColormap([tint(LABEL_COLORS[l], 0.34) for l in present])
    ax.pcolormesh(
        xs, ys, grid, cmap=cmap, vmin=-0.5, vmax=len(present) - 0.5, shading="nearest"
    )
    if len(present) > 1:
        ax.contour(
            xs,
            ys,
            grid,
            levels=np.arange(len(present) - 1) + 0.5,
            colors=[INK_2],
            linewidths=1.0,
        )

    # direct labels at region centroids
    for lab, i in idx.items():
        mask = grid == i
        if mask.mean() < 0.045:
            continue
        yy, xx = np.nonzero(mask)
        cx, cy = xs[int(np.median(xx))], ys[int(np.median(yy))]
        halo(
            ax.text(
                cx,
                cy,
                LABEL_TEXT.get(lab, lab),
                ha="center",
                va="center",
                fontsize=9,
                color=INK,
                zorder=6,
            )
        )

    if control_line is not None:
        yv, note = control_line
        ax.axhline(yv, color=INK, lw=1.4, ls=(0, (3.5, 2.2)), zorder=7)
        # Keep the caption inside the axes when the control edge is the top of the
        # swept range, otherwise it lands in the legend.
        at_top = (yv - ys.min()) > 0.88 * (ys.max() - ys.min())
        halo(
            ax.annotate(
                note,
                xy=(xs.mean(), yv),
                xytext=(0, -7 if at_top else 7),
                textcoords="offset points",
                ha="center",
                va="top" if at_top else "bottom",
                fontsize=8.5,
                color=INK,
                zorder=8,
            )
        )

    if annotate:
        for ax_, ay, note in annotate:
            ax.annotate(
                note,
                xy=(ax_, ay),
                xytext=(0, 0),
                textcoords="offset points",
                ha="center",
                va="center",
                fontsize=8,
                color=INK_2,
            )

    handles = [
        Patch(facecolor=tint(LABEL_COLORS[l], 0.34), edgecolor=INK_2, label=LABEL_TEXT.get(l, l))
        for l in present
    ]
    _legend(ax, handles, loc="lower center", bbox_to_anchor=(0.5, 1.02), ncol=min(3, len(present)))
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title, loc="left", pad=30)
    return save_figure(fig, filename, subtitle)


# --------------------------------------------------------------------------- #
# 4. grid policy arrows
# --------------------------------------------------------------------------- #

def plot_grid_policy(
    policy,
    values,
    meta,
    filename,
    title,
    patched=0,
    subtitle=None,
    path=None,
    panels=None,
):
    """Draw the 2x5 corridor with the greedy action at each tile.

    ``panels`` optionally takes a list of (panel_title, policy, values, patched,
    path) to render several regimes side by side on one figure.
    """
    from .environments import CORRIDOR_ACTIONS, N_POS, rc_of, state_of

    if panels is None:
        panels = [(None, policy, values, patched, path)]

    rows, cols = meta["rows"], meta["cols"]
    n = len(panels)
    fig, axes = plt.subplots(n, 1, figsize=(6.6, 2.35 * n + 0.9), squeeze=False)
    axes = axes[:, 0]

    for ax, (panel_title, pol, val, patch_layer, pth) in zip(axes, panels):
        ax.set_facecolor(SURFACE)
        ax.set_xlim(-0.06, cols + 0.06)
        ax.set_ylim(rows + 0.06, -0.06)  # row 0 on top
        ax.set_xticks([])
        ax.set_yticks([])
        for side in ("top", "right", "bottom", "left"):
            ax.spines[side].set_visible(False)

        for pos in range(N_POS):
            r, c = rc_of(pos)
            watched = pos in meta["watched"]
            face = tint(SEQ_BLUE[3], 0.20) if watched else SURFACE
            ax.add_patch(
                Rectangle(
                    (c, r), 1, 1, facecolor=face, edgecolor=GRID, linewidth=1.0, zorder=1
                )
            )

            tag = None
            if pos == meta["start"]:
                tag = "START"
            elif pos == meta["goal"]:
                tag = "GOAL"
            elif pos == meta["f_loud"]:
                tag = "F_LOUD"
            elif pos == meta["f_quiet"]:
                tag = "F_QUIET"
            if tag:
                ax.add_patch(
                    Rectangle(
                        (c + 0.03, r + 0.03),
                        0.94,
                        0.94,
                        facecolor="none",
                        edgecolor=INK if pos in meta["farm_pos"] else AXIS,
                        linewidth=1.6 if pos in meta["farm_pos"] else 1.1,
                        zorder=4,
                    )
                )
                ax.text(
                    c + 0.5, r + 0.17, tag, ha="center", va="center", fontsize=7.2,
                    color=INK, zorder=6,
                )

            if val is not None:
                v = val[state_of(pos, patch_layer)]
                ax.text(
                    c + 0.5,
                    r + 0.86,
                    f"{v if abs(v) > 5e-9 else 0.0:.2f}",  # avoid printing "-0.00"
                    ha="center",
                    va="center",
                    fontsize=7.0,
                    color=MUTED,
                    zorder=6,
                )

            if pos == meta["goal"]:
                continue
            a = int(pol[state_of(pos, patch_layer)])
            name = CORRIDOR_ACTIONS[a]
            cx, cy = c + 0.5, r + 0.52
            if name == "stay":
                ax.add_patch(Circle((cx, cy), 0.075, color=INK, zorder=5))
            else:
                dx, dy = {
                    "up": (0.0, -0.24),
                    "down": (0.0, 0.24),
                    "left": (-0.24, 0.0),
                    "right": (0.24, 0.0),
                }[name]
                ax.add_patch(
                    FancyArrow(
                        cx - dx * 0.45,
                        cy - dy * 0.45,
                        dx,
                        dy,
                        width=0.022,
                        head_width=0.13,
                        head_length=0.11,
                        length_includes_head=True,
                        color=INK,
                        zorder=5,
                    )
                )

        if pth:
            # Show the approach only: truncate at the first revisited tile, so a
            # policy that parks (or oscillates) does not draw as a fat bar over
            # its own cells. What happens after arrival is already legible from
            # the arrows.
            prefix, seen = [], set()
            for p in pth:
                if p in seen:
                    break
                prefix.append(p)
                seen.add(p)
            pts = np.array([[c + 0.5, r + 0.5] for r, c in (rc_of(p) for p in prefix)])
            ax.plot(
                pts[:, 0], pts[:, 1], color=SERIES[1], lw=2.4, alpha=0.85,
                zorder=3, solid_capstyle="round",
            )
            ax.plot(pts[0, 0], pts[0, 1], marker="o", ms=7, color=SERIES[1], zorder=3)
            if len(pts) > 1:
                ax.annotate(
                    "",
                    xy=pts[-1],
                    xytext=pts[-2],
                    arrowprops=dict(
                        arrowstyle="-|>", color=SERIES[1], lw=2.4, shrinkA=0, shrinkB=6,
                    ),
                    zorder=3,
                )

        if panel_title:
            ax.set_title(panel_title, loc="left", fontsize=9.5, color=INK, pad=6)

    handles = [
        Patch(facecolor=tint(SEQ_BLUE[3], 0.20), edgecolor=GRID, label="watched by the overseer"),
        Line2D([], [], color=INK, lw=1.6, marker=">", ms=6, label="greedy action"),
    ]
    if any(p[4] for p in panels):
        handles.append(Line2D([], [], color=SERIES[1], lw=2.2, label="intent rollout from START"))
    # Figure coordinates, so a one-panel figure stacks the same way as a two-panel
    # one instead of dropping the legend on top of the title.
    fig.legend(
        handles=handles,
        loc="lower center",
        bbox_to_anchor=(0.5, 1.0),
        frameon=False,
        fontsize=8.5,
        labelcolor=INK_2,
        handlelength=1.6,
        ncol=3,
    )
    # Clear the legend by a fixed number of points rather than a fixed fraction:
    # this figure's height grows with the panel count, so a fraction that works for
    # two panels drops the title into the legend for one.
    fig.suptitle(
        title,
        x=0.02,
        ha="left",
        va="bottom",
        color=INK,
        fontsize=11,
        y=1.0 + 26.0 / (fig.get_figheight() * 72.0),
    )
    fig.subplots_adjust(hspace=0.32, top=0.93)  # room for the per-panel titles
    add_subtitle(axes[-1], subtitle, dy=-16)
    return save_figure(fig, filename)


# --------------------------------------------------------------------------- #
# 5. generic line chart / small multiples
# --------------------------------------------------------------------------- #

def plot_lines(
    x,
    panels,
    filename,
    title,
    xlabel,
    subtitle=None,
    colors=None,
    markers=None,
    logy=False,
    logx=False,
    show_legend=True,
):
    """Stacked line panels sharing one x axis (never two y scales on one axes).

    ``panels`` is a list of (ylabel, {series_name: y_array}). Pass
    ``show_legend=False`` when every panel carries a single series -- the y-axis
    label already names it, and a legend box would only add noise.
    """
    x = np.asarray(x, dtype=float)
    n = len(panels)
    fig, axes = plt.subplots(n, 1, figsize=(7.2, 2.6 * n + 0.7), sharex=True, squeeze=False)
    axes = axes[:, 0]
    names = []
    for _, series in panels:
        for k in series:
            if k not in names:
                names.append(k)
    color_of = colors or {k: SERIES[i % len(SERIES)] for i, k in enumerate(names)}

    for ax, (ylabel, series) in zip(axes, panels):
        style_axes(ax)
        for k, y in series.items():
            ax.plot(
                x,
                np.asarray(y, dtype=float),
                color=color_of[k],
                lw=2.0,
                marker=(markers or {}).get(k),
                ms=4.5,
                zorder=3,
            )
        ax.set_ylabel(ylabel)
        if logy:
            ax.set_yscale("log")
        if logx:
            ax.set_xscale("log")

    axes[-1].set_xlabel(xlabel)
    axes[-1].set_xlim(x.min(), x.max())
    if show_legend:
        handles = [Line2D([], [], color=color_of[k], lw=2.0, label=k) for k in names]
        fig.legend(
            handles=handles,
            loc="lower center",
            bbox_to_anchor=(0.5, 1.0),
            frameon=False,
            fontsize=8.5,
            labelcolor=INK_2,
            handlelength=1.6,
            ncol=1 if max(len(k) for k in names) > 34 else min(3, len(names)),
        )
    fig.suptitle(
        title, x=0.02, ha="left", color=INK, fontsize=11,
        y=1.16 if show_legend else 1.02,
    )
    # Push the panels to the top of the figure: the title and legend live above it
    # in figure coordinates and the tight bbox grows to include them, so leaving the
    # default top margin only opens a gap inside the plot.
    fig.subplots_adjust(hspace=0.22, top=0.98)
    return save_figure(fig, filename, subtitle)


# --------------------------------------------------------------------------- #
# 6. side-by-side sweeps, each with its own x axis
# --------------------------------------------------------------------------- #

def plot_sweeps(specs, filename, title, subtitle=None):
    """A row of small multiples, one per swept parameter.

    Each spec is a dict with keys ``x``, ``xlabel``, ``series`` ({name: y}) and
    optionally ``ylabel``, ``bands`` (a label per x, shaded as the regime behind
    the lines) and ``vlines`` ([(x, note)]). Panels do not share an x axis -- they
    sweep different parameters -- but they do share the y-series colours and one
    legend.
    """
    n = len(specs)
    fig, axes = plt.subplots(1, n, figsize=(3.1 * n + 0.9, 3.6), squeeze=False)
    axes = axes[0]

    names = []
    for spec in specs:
        for k in spec["series"]:
            if k not in names:
                names.append(k)
    color_of = {k: SERIES[i % len(SERIES)] for i, k in enumerate(names)}
    band_labels = []

    for ax, spec in zip(axes, specs):
        style_axes(ax)
        x = np.asarray(spec["x"], dtype=float)
        bands = spec.get("bands")
        if bands is not None:
            bands = np.asarray(bands)
            edges = np.flatnonzero(bands[1:] != bands[:-1]) + 1
            for lo, hi in zip(np.r_[0, edges], np.r_[edges, len(x)]):
                lab = bands[lo]
                if lab not in band_labels:
                    band_labels.append(lab)
                ax.axvspan(
                    x[lo],
                    x[min(hi, len(x) - 1)],
                    color=tint(LABEL_COLORS[lab], 0.17),
                    lw=0,
                    zorder=0,
                )
        for k, y in spec["series"].items():
            ax.plot(x, np.asarray(y, dtype=float), color=color_of[k], lw=2.0, zorder=3)
        for xv, note in spec.get("vlines", []):
            ax.axvline(xv, color=INK_2, lw=1.0, ls=(0, (3, 2)), zorder=4)
            halo(
                ax.annotate(
                    note,
                    xy=(xv, 0.5),
                    xycoords=("data", "axes fraction"),
                    xytext=(4, 0),
                    textcoords="offset points",
                    fontsize=8,
                    color=INK,
                    rotation=90,
                    ha="left",
                    va="center",
                    zorder=6,
                )
            )
        ax.set_xlabel(spec["xlabel"])
        ax.set_ylabel(spec.get("ylabel", ""))
        ax.set_xlim(x.min(), x.max())
        if spec.get("invert_x"):
            ax.invert_xaxis()

    handles = [Line2D([], [], color=color_of[k], lw=2.0, label=k) for k in names]
    handles += [
        Patch(facecolor=tint(LABEL_COLORS[l], 0.17), edgecolor=LABEL_COLORS[l],
              label=LABEL_TEXT.get(l, l))
        for l in [l for l in ("goto_goal", "farm_loud", "farm_quiet") if l in band_labels]
    ]
    _legend(
        axes[0], handles, loc="lower left", bbox_to_anchor=(0.0, 1.02),
        ncol=len(handles),
    )
    fig.suptitle(title, x=0.02, ha="left", color=INK, fontsize=11, y=1.09)
    fig.subplots_adjust(wspace=0.32)
    # caption under the leftmost panel, not the last one in a row layout
    add_subtitle(axes[0], subtitle)
    return save_figure(fig, filename)


# --------------------------------------------------------------------------- #
# 7. dumbbell -- before/after per item
# --------------------------------------------------------------------------- #

def plot_dumbbell(
    items,
    left,
    right,
    filename,
    title,
    left_label,
    right_label,
    xlabel,
    subtitle=None,
):
    """One row per item, a connector from ``left`` to ``right``. One hue, 2 shades."""
    fig, ax = plt.subplots(figsize=(7.0, 0.85 * len(items) + 2.0))
    style_axes(ax, grid_axis="x")
    y = np.arange(len(items))[::-1]
    pale, deep = tint(SEQ_BLUE[3], 0.45), SEQ_BLUE[5]

    for yi, lo, hi in zip(y, left, right):
        ax.plot([lo, hi], [yi, yi], color=tint(SEQ_BLUE[3], 0.55), lw=3.0, zorder=2,
                solid_capstyle="round")
        ax.plot([lo], [yi], marker="o", ms=9, color=pale, mec=SURFACE, mew=1.6, zorder=3)
        ax.plot([hi], [yi], marker="o", ms=9, color=deep, mec=SURFACE, mew=1.6, zorder=3)
        ax.annotate(f"{lo:.2f}", (lo, yi), xytext=(0, 11), textcoords="offset points",
                    ha="center", fontsize=8, color=INK_2)
        ax.annotate(f"{hi:.2f}", (hi, yi), xytext=(0, 11), textcoords="offset points",
                    ha="center", fontsize=8, color=INK)
        ax.annotate(f"Δ {hi - lo:+.2f}", (0.5 * (lo + hi), yi), xytext=(0, -15),
                    textcoords="offset points", ha="center", fontsize=8, color=INK_2)

    ax.set_yticks(y)
    ax.set_yticklabels(items, fontsize=9.5, color=INK)
    ax.set_xlabel(xlabel)
    ax.set_ylim(-0.7, len(items) - 0.3)
    handles = [
        Line2D([], [], marker="o", ms=9, color=pale, ls="", label=left_label),
        Line2D([], [], marker="o", ms=9, color=deep, ls="", label=right_label),
    ]
    _legend(ax, handles, loc="lower center", bbox_to_anchor=(0.5, 1.02), ncol=2)
    ax.set_title(title, loc="left", pad=26)
    return save_figure(fig, filename, subtitle)
