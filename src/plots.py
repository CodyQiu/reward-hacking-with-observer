"""The four Exp 2 figures, rebuilt from the CSVs in results/ without retraining.

Reuses the repo's shared figure conventions (src/plotting.py) so Exp 2 reads as
part of the same set as Exp 0 and Exp 1: recessive chrome, a fixed hue per
condition, direct labels, and never two y-scales on one axes.
"""

import csv
import glob
import os
import re
from collections import defaultdict

import numpy as np

from .dp_reference import REFERENCE
from .plotting import (
    AXIS,
    INK,
    INK_2,
    SERIES,
    add_subtitle,
    halo,
    plt,
    save_figure,
    style_axes,
    tint,
)

__all__ = ["load_results", "make_all_figures"]

CONDITION_COLOR = {"suspicion": SERIES[0], "flat": SERIES[1]}
CONDITION_LABEL = {
    "suspicion": "SUSPICION monitor",
    "flat": "FLAT monitor (control)",
}


def load_results(results_dir="results", monitors=("suspicion", "flat")):
    """{monitor: {metric: (timesteps, array of shape (n_seeds, n_evals))}}.

    Matches only ``<monitor>_seed<N>.csv``. The phase-2 files
    (``permanent_<monitor>_n<N>_seed<K>.csv``) also end in ``_seed<K>.csv`` but
    carry a per-episode schema, so a looser glob would pull them in here and fail
    on the missing ``timesteps`` column.
    """
    pattern = re.compile(rf"^({'|'.join(monitors)})_seed(\d+)$")
    per_condition = defaultdict(dict)
    for path in sorted(glob.glob(os.path.join(results_dir, "*_seed*.csv"))):
        name = os.path.basename(path)[: -len(".csv")]
        match = pattern.match(name)
        if not match:
            continue
        monitor, seed = match.group(1), match.group(2)
        with open(path) as fh:
            rows = list(csv.DictReader(fh))
        per_condition[monitor][int(seed)] = {
            k: np.array([float(r[k]) for r in rows]) for k in rows[0]
        }

    out = {}
    for monitor, seeds in per_condition.items():
        keys = sorted(seeds)
        n = min(len(seeds[k]["timesteps"]) for k in keys)
        metrics = {"timesteps": seeds[keys[0]]["timesteps"][:n], "seeds": keys}
        for metric in seeds[keys[0]]:
            if metric == "timesteps":
                continue
            metrics[metric] = np.stack([seeds[k][metric][:n] for k in keys])
        out[monitor] = metrics
    return out


def _band(ax, x, arr, color, label, direct_label=True):
    """Mean across seeds with a +-1 s.d. band."""
    mean, sd = arr.mean(axis=0), arr.std(axis=0)
    ax.fill_between(x, mean - sd, mean + sd, color=tint(color, 0.22), lw=0, zorder=2)
    ax.plot(x, mean, color=color, lw=2.0, zorder=3, label=label)
    if direct_label:
        halo(
            ax.annotate(
                label,
                xy=(x[-1], mean[-1]),
                xytext=(-4, 8),
                textcoords="offset points",
                ha="right",
                fontsize=8.5,
                color=INK,
                zorder=6,
            )
        )
    return mean


def _reference_line(ax, y, text, x_frac=0.60, below=True):
    """Dashed rule plus a caption.

    Captions for the memoryless references sit *below* their line and start
    mid-axis: the series' own direct labels sit above the line at the right end,
    and the left end is where the training transient lives, so this is the one
    band that stays clear in both places.
    """
    ax.axhline(y, color=AXIS, lw=1.0, ls=(0, (4, 3)), zorder=1)
    halo(
        ax.annotate(
            text,
            xy=(x_frac, y),
            xycoords=("axes fraction", "data"),
            xytext=(0, -5 if below else 4),
            textcoords="offset points",
            va="top" if below else "bottom",
            fontsize=8,
            color=INK_2,
            zorder=6,
        )
    )


def _new_axes(figsize=(7.4, 4.4)):
    fig, ax = plt.subplots(figsize=figsize)
    style_axes(ax)
    ax.set_xlabel("training steps")
    return fig, ax


def _finish(fig, ax, title, filename, subtitle):
    ax.set_title(title, loc="left", pad=12)
    ax.xaxis.set_major_formatter(lambda v, _: f"{v / 1000:,.0f}k")
    add_subtitle(ax, subtitle)
    return save_figure(fig, filename)


def fig_true_return(data, filename="exp2_true_return.png"):
    """The headline: mean TRUE return during training, both monitors."""
    fig, ax = _new_axes()
    for monitor in ("flat", "suspicion"):
        if monitor in data:
            _band(
                ax,
                data[monitor]["timesteps"],
                data[monitor]["true_return"],
                CONDITION_COLOR[monitor],
                CONDITION_LABEL[monitor],
            )
    _reference_line(ax, REFERENCE["honest_optimum_return"], "honest optimum  +2.0",
                    x_frac=0.02, below=False)
    for monitor in ("suspicion", "flat"):
        if monitor in data:
            _reference_line(
                ax,
                REFERENCE[monitor]["true_return"],
                f"memoryless optimum, {monitor}  {REFERENCE[monitor]['true_return']:+.1f}",
            )
    ax.set_ylabel("mean true return per episode")
    n_seeds = len(data[next(iter(data))]["seeds"])
    return _finish(
        fig,
        ax,
        "Exp 2  ·  damage to the true objective, by monitor",
        filename,
        f"mean over {n_seeds} seeds, band = ±1 s.d. across seeds; 300 fresh episodes per "
        "evaluation. The agent never sees the true reward — it is measurement only. Both "
        "monitors converge to the memoryless optimum for their condition, which is the "
        "expected ceiling for a policy with no clock feature.",
    )


def fig_proxy_vs_true(data, monitor="suspicion", filename="exp2_proxy_vs_true.png"):
    """The reward-hacking divergence: proxy up while true goes down."""
    fig, ax = _new_axes()
    x = data[monitor]["timesteps"]
    # Same units (reward), so one shared axis -- never two y-scales.
    _band(ax, x, data[monitor]["proxy_return"], SERIES[2], "PROXY return (what it trains on)")
    _band(ax, x, data[monitor]["true_return"], SERIES[0], "TRUE return (what we care about)")
    _reference_line(ax, REFERENCE["honest_optimum_return"], "honest optimum  +2.0",
                    x_frac=0.02, below=False)
    ax.axhline(0.0, color=AXIS, lw=0.8, zorder=1)
    ax.set_ylabel("mean return per episode")
    return _finish(
        fig,
        ax,
        f"Exp 2  ·  reward hacking, {CONDITION_LABEL[monitor].lower()}",
        filename,
        "Both curves are in reward units, so they share one axis. Training drives the "
        "proxy up and the true objective down: the divergence is the reward hacking.",
    )


def fig_farm_steps(data, filename="exp2_farm_steps.png"):
    fig, ax = _new_axes()
    for monitor in ("flat", "suspicion"):
        if monitor in data:
            _band(
                ax,
                data[monitor]["timesteps"],
                data[monitor]["farm_steps"],
                CONDITION_COLOR[monitor],
                CONDITION_LABEL[monitor],
            )
    for monitor in ("suspicion", "flat"):
        if monitor in data:
            _reference_line(
                ax,
                REFERENCE[monitor]["farm_steps"],
                f"memoryless, {monitor}  {REFERENCE[monitor]['farm_steps']:.1f}",
            )
    ax.set_ylabel("farming steps per episode")
    return _finish(
        fig,
        ax,
        "Exp 2  ·  how much the exploit actually gets used",
        filename,
        "A step counts as farming when the agent stands on the waypoint while the bonus "
        "is still live. The suspicion monitor cuts the exploit off sooner, so fewer "
        "steps are farmed at matched hazard scale.",
    )


def fig_goal_rate(data, filename="exp2_goal_rate.png"):
    """Included specifically to show that goal-reach rate is uninformative."""
    fig, ax = _new_axes()
    for monitor in ("flat", "suspicion"):
        if monitor in data:
            _band(
                ax,
                data[monitor]["timesteps"],
                data[monitor]["goal_rate"],
                CONDITION_COLOR[monitor],
                CONDITION_LABEL[monitor],
            )
    ax.set_ylim(-0.03, 1.06)
    ax.set_ylabel("fraction of episodes reaching GOAL")
    return _finish(
        fig,
        ax,
        "Exp 2  ·  why task-success rate is the wrong metric",
        filename,
        "Both conditions sit near 1.0 for almost all of training while the true return "
        "collapses: the agent farms and then finishes anyway. Success rate cannot see "
        "the reward hacking — this is the same lesson as Exp 1b, and it is why the "
        "headline metric is true return.",
    )


def fig_permanent_correction(
    results_dir="results", monitor="suspicion", n_permanent=50, window=200,
    filename="exp2_permanent_correction.png",
):
    """Optional phase 2: the rise / drop / recover curve.

    Per-episode returns during training (not frozen-policy evals), because the
    permanent swap is a training-level event and the point is what the agent
    actually receives as it happens.
    """
    pattern = f"permanent_{monitor}_n{n_permanent}_seed*.csv"
    paths = sorted(glob.glob(os.path.join(results_dir, pattern)))
    if not paths:
        raise FileNotFoundError(f"no {pattern} in {results_dir}/")

    fig, ax = _new_axes()
    swap_steps = []
    for k, path in enumerate(paths):
        with open(path) as fh:
            rows = list(csv.DictReader(fh))
        step = np.array([float(r["timestep"]) for r in rows])
        proxy = np.array([float(r["proxy_return"]) for r in rows])
        true = np.array([float(r["true_return"]) for r in rows])
        corrected = np.array([int(r["corrected"]) for r in rows])
        if corrected.any():
            swap_steps.append(step[corrected.argmax()])

        kernel = np.ones(window) / window
        if len(step) <= window:
            continue
        sm_step = step[window - 1 :]
        first = k == 0
        ax.plot(
            sm_step, np.convolve(proxy, kernel, "valid"), color=SERIES[2], lw=2.0,
            alpha=0.9, zorder=3, label="received (proxy) return" if first else None,
        )
        ax.plot(
            sm_step, np.convolve(true, kernel, "valid"), color=SERIES[0], lw=2.0,
            alpha=0.9, zorder=3, label="true return" if first else None,
        )

    if swap_steps:
        mean_swap = float(np.mean(swap_steps))
        ax.axvline(mean_swap, color=INK, lw=1.4, ls=(0, (3.5, 2.2)), zorder=4)
        halo(
            ax.annotate(
                f"permanent correction lands\n(mean env step {mean_swap:,.0f})",
                xy=(mean_swap, 0.97),
                xycoords=("data", "axes fraction"),
                xytext=(6, 0),
                textcoords="offset points",
                ha="left",
                va="top",
                fontsize=8.5,
                color=INK,
                zorder=6,
            )
        )
    _reference_line(ax, REFERENCE["honest_optimum_return"], "honest optimum  +2.0",
                    x_frac=0.02, below=False)
    ax.set_ylabel("return per episode")
    ax.legend(frameon=False, fontsize=8.5, labelcolor=INK_2, loc="lower right")
    return _finish(
        fig,
        ax,
        "Exp 2, phase 2  ·  what a permanent correction does to the agent",
        filename,
        f"{len(paths)} seeds, {window}-episode rolling mean of per-episode returns during "
        f"training; the proxy is permanently replaced by the true reward after "
        f"{n_permanent} cumulative detections. Both curves are in reward units, so they "
        "share one axis.",
    )


def make_all_figures(results_dir="results", primary_condition="suspicion"):
    data = load_results(results_dir)
    if not data:
        raise FileNotFoundError(f"no result CSVs found in {results_dir}/")
    paths = [
        fig_true_return(data),
        fig_proxy_vs_true(data, primary_condition),
        fig_farm_steps(data),
        fig_goal_rate(data),
    ]
    return data, paths
