"""
Phase 4 charts (static PNGs for the write-up), built from analysis.summaries().

Design rules used here:
  - WHOOP is the focal brand: blue. Comparison brands: one validated categorical
    palette in fixed order (WHOOP, Oura, Garmin, Apple Watch), or gray when the
    chart is about WHOOP vs the rest.
  - One axis per chart; percentages on a 0-based scale.
  - Thin bars, recessive grid, text in neutral ink (never in series colors).
  - Cells/bars with n < 30 are hatched and labeled "n<30" instead of hidden.
  - Every chart returns (fig, caption). The caption says what the chart shows;
    the insight ("so what") is written in Phase 5.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Patch

import analysis
import tagging

CHARTS = Path(__file__).resolve().parent.parent / "outputs" / "charts"

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
GRID = "#e4e3df"
MUTED = "#b9b8b2"
BRANDS = ["WHOOP", "Oura", "Garmin", "Apple Watch"]
BRAND_COLORS = {"WHOOP": "#2a78d6", "Oura": "#eb6834", "Garmin": "#1baf7a", "Apple Watch": "#eda100"}
BLUE_RAMP = ["#e6f0fd", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
SOURCE = "Source: public Reddit posts and comments, Sep 2025 to Sep 2026 (Arctic Shift archive). Independent project, not affiliated with WHOOP."

plt.rcParams.update({
    "font.family": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
    "font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": INK_2, "text.color": INK,
    "xtick.color": INK_2, "ytick.color": INK, "axes.facecolor": SURFACE, "figure.facecolor": SURFACE,
    "savefig.facecolor": SURFACE, "axes.spines.top": False, "axes.spines.right": False,
    "axes.spines.left": False, "axes.titlelocation": "left",
})


def _frame(fig, title, subtitle):
    fig.text(0.02, 0.985, title, fontsize=14, fontweight="bold", va="top", color=INK)
    fig.text(0.02, 0.935, subtitle, fontsize=10, va="top", color=INK_2)
    fig.text(0.02, 0.012, SOURCE, fontsize=7.5, color=INK_2, va="bottom")


def _pct_axis(ax, xmax):
    ax.set_xlim(0, xmax)
    ticks = [t for t in matplotlib.ticker.MaxNLocator(5, steps=[1, 2, 2.5, 5, 10]).tick_values(0, xmax) if 0 <= t < xmax - 1e-9]
    ax.set_xticks(ticks)  # drop the end tick so neighbouring small multiples don't collide
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0)


def _nice_max(values, floor=0.1):
    m = float(np.nanmax(values)) if len(values) else floor
    return max(floor, np.ceil(m * 1.15 / 0.05) * 0.05)


def _value_label(ax, x, y, text, xmax, on_dark=True, at_start=False):
    if at_start and x >= xmax * 0.09:  # inside the bar's left end: never collides with markers
        ax.text(xmax * 0.012, y, text, va="center", ha="left", fontsize=8.5,
                color="white" if on_dark else INK, fontweight="bold", zorder=5)
        return
    if at_start:
        ax.text(x + xmax * 0.012, y, text, va="center", ha="left", fontsize=8.5, color=INK_2, zorder=5,
                bbox=dict(boxstyle="square,pad=0.1", facecolor=SURFACE, edgecolor="none"))
        return
    if x >= xmax * 0.14:
        ax.text(x - xmax * 0.012, y, text, va="center", ha="right", fontsize=8.5,
                color="white" if on_dark else INK, fontweight="bold", zorder=5)
    else:
        ax.text(x + xmax * 0.012, y, text, va="center", ha="left", fontsize=8.5, color=INK_2, zorder=5)


def _whisker(ax, lo, hi, y):
    ax.plot([lo, hi], [y, y], color=INK_2, linewidth=0.8, alpha=0.55, zorder=2, solid_capstyle="butt")


def save(fig, name):
    CHARTS.mkdir(parents=True, exist_ok=True)
    path = CHARTS / f"{name}.png"
    fig.savefig(path, dpi=200, bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
    return path


# ------------------------------------------------------------- 1. WHOOP stage heatmap
def emotion_by_stage(stage_by_brand, brand="WHOOP"):
    d = stage_by_brand[stage_by_brand["brand"] == brand]
    grid = d.pivot_table(index="emotion", columns="stage", values="share", observed=True)
    grid = grid.reindex(index=analysis.GROUPS, columns=tagging.STAGE_ORDER)
    ns = d.groupby("stage", observed=True)["n"].first().reindex(tagging.STAGE_ORDER).fillna(0).astype(int)

    fig, ax = plt.subplots(figsize=(8.6, 4.6))
    fig.subplots_adjust(left=0.27, right=0.98, top=0.78, bottom=0.1)
    vmax = max(0.05, float(np.nanmax(grid.values)))
    cmap = LinearSegmentedColormap.from_list("blue", BLUE_RAMP)
    ax.imshow(grid.values, cmap=cmap, vmin=0, vmax=vmax, aspect="auto")
    for i in range(grid.shape[0]):
        for j in range(grid.shape[1]):
            v, n = grid.values[i, j], ns.iloc[j]
            if n < analysis.MIN_N or np.isnan(v):
                ax.add_patch(plt.Rectangle((j - .5, i - .5), 1, 1, facecolor=SURFACE, hatch="////",
                                           edgecolor=MUTED, linewidth=0))
                ax.text(j, i, "n<30", ha="center", va="center", fontsize=9, color=INK_2)
            else:
                dark = v / vmax > 0.55
                ax.text(j, i, f"{v:.0%}", ha="center", va="center", fontsize=11,
                        color="white" if dark else INK, fontweight="bold" if dark else "normal")
    ax.set_xticks(range(len(tagging.STAGE_ORDER)),
                  [f"{tagging.STAGE_LABELS[s]}\nn={ns[s]:,}" for s in tagging.STAGE_ORDER])
    ax.set_yticks(range(len(analysis.GROUPS)), analysis.GROUPS)
    ax.tick_params(length=0)
    ax.xaxis.tick_top()
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xticks(np.arange(-.5, grid.shape[1]), minor=True)
    ax.set_yticks(np.arange(-.5, grid.shape[0]), minor=True)
    ax.grid(which="minor", color=SURFACE, linewidth=3)
    ax.tick_params(which="minor", length=0)
    _frame(fig, f"How {brand} owners feel at each stage",
           "% of posts expressing each emotion, by ownership stage (a post can express several)")
    caption = (f"Emotion mix in r/{'whoop' if brand == 'WHOOP' else brand} posts at each ownership stage "
               f"(considering, first weeks, daily habit, cancelling); n = {ns.sum():,} stage-tagged posts.")
    return fig, caption


# ------------------------------------------------------------- 2 & 5. emotion by theme, small multiples
def emotion_by_theme(theme_by_brand, emotion, title, subtitle):
    d = theme_by_brand[theme_by_brand["emotion"] == emotion]
    order = (d[d["brand"] == "WHOOP"].set_index("theme")["share"]
             .reindex(tagging.THEMES).sort_values(ascending=True).index.tolist())
    xmax = _nice_max(d.loc[~d["small_n"], "ci_high"].values, floor=0.1)

    fig, axes = plt.subplots(1, 4, figsize=(12, 4.8), sharey=True)
    fig.subplots_adjust(left=0.15, right=0.985, top=0.80, bottom=0.12, wspace=0.12)
    y = np.arange(len(order))
    for ax, brand in zip(axes, BRANDS):
        b = d[d["brand"] == brand].set_index("theme").reindex(order)
        color = BRAND_COLORS["WHOOP"] if brand == "WHOOP" else MUTED
        for yi, (th, r) in zip(y, b.iterrows()):
            if pd.isna(r["share"]):
                continue
            small = bool(r["small_n"])
            ax.barh(yi, r["share"], height=0.62, color=SURFACE if small else color,
                    edgecolor=MUTED if small else SURFACE, hatch="////" if small else None, linewidth=1, zorder=3)
            if small:
                ax.text(r["share"] + xmax * 0.012, yi, "n<30", va="center", fontsize=8.5, color=INK_2)
                continue
            _whisker(ax, r["ci_low"], r["ci_high"], yi)
            _value_label(ax, r["share"], yi, f"{r['share']:.0%}", xmax, on_dark=(brand == "WHOOP"), at_start=True)
        _pct_axis(ax, xmax)
        ax.set_title(brand, fontsize=11, fontweight="bold", color=INK, pad=6)
    axes[0].set_yticks(y, order)
    _frame(fig, title, subtitle)
    caption = (f"Share of posts expressing {emotion.lower()} within each theme, by brand "
               "(random sample only; lines show 95% intervals).")
    return fig, caption


# ------------------------------------------------------------- 3. cancelling posts by brand
def cancelling_emotions(cancelling_by_brand):
    d = cancelling_by_brand
    ns = d.groupby("brand")["n"].first().reindex(BRANDS).fillna(0).astype(int)
    groups = analysis.GROUPS[::-1]
    fig, ax = plt.subplots(figsize=(9, 5.4))
    fig.subplots_adjust(left=0.27, right=0.97, top=0.83, bottom=0.12)
    h = 0.19
    xmax = _nice_max(d["share"].values, floor=0.1)
    for i, brand in enumerate(BRANDS):
        b = d[d["brand"] == brand].set_index("emotion").reindex(groups)
        ypos = np.arange(len(groups)) + (1.5 - i) * h
        small = ns[brand] < analysis.MIN_N
        ax.barh(ypos, b["share"].fillna(0), height=h * 0.92,
                color=SURFACE if small else BRAND_COLORS[brand],
                edgecolor=BRAND_COLORS[brand] if small else SURFACE, hatch="////" if small else None,
                linewidth=1, label=f"{brand} (n={ns[brand]:,}{', too few' if small else ''})")
    ax.set_yticks(np.arange(len(groups)), groups)
    _pct_axis(ax, xmax)
    ax.legend(loc="lower right", frameon=False, fontsize=9, reverse=True)
    _frame(fig, "What people feel when they leave",
           "% of cancelling / returning / switching posts expressing each emotion, by brand")
    caption = (f"Emotion mix in posts about cancelling, returning or switching away, by brand "
               f"(n = {ns.sum():,} posts; random and stage-boost samples).")
    return fig, caption


# ------------------------------------------------------------- 4. themes that carry pride & joy
def pride_by_theme(theme_by_brand, emotion="Pride & joy"):
    d = theme_by_brand[theme_by_brand["emotion"] == emotion]
    w = d[d["brand"] == "WHOOP"].set_index("theme")
    others = (d[d["brand"] != "WHOOP"].groupby("theme")[["k", "n"]].sum()
              .assign(share=lambda x: x.k / x.n))
    order = w["share"].reindex(tagging.THEMES).sort_values().index.tolist()
    w, others = w.reindex(order), others.reindex(order)
    xmax = _nice_max(pd.concat([w["ci_high"], others["share"]]).values, floor=0.1)

    fig, ax = plt.subplots(figsize=(9, 5.0))
    fig.subplots_adjust(left=0.24, right=0.95, top=0.82, bottom=0.12)
    y = np.arange(len(order))
    for yi, (th, r) in zip(y, w.iterrows()):
        small = bool(r["small_n"])
        ax.barh(yi, r["share"], height=0.55, color=SURFACE if small else BRAND_COLORS["WHOOP"],
                edgecolor=MUTED if small else SURFACE, hatch="////" if small else None, linewidth=1, zorder=3)
        if small:
            ax.text(r["share"] + xmax * 0.012, yi, "n<30", va="center", fontsize=9, color=INK_2)
            continue
        _whisker(ax, r["ci_low"], r["ci_high"], yi)
        _value_label(ax, r["share"], yi, f"{r['share']:.0%}", xmax, at_start=True)
    ax.scatter(others["share"], y, s=64, marker="D", color=INK, edgecolor=SURFACE, linewidth=1.8, zorder=6)
    ax.set_yticks(y, order)
    _pct_axis(ax, xmax)
    ax.legend(handles=[Patch(color=BRAND_COLORS["WHOOP"], label="WHOOP (line = 95% interval)"),
                       plt.Line2D([], [], marker="D", linestyle="", color=INK, markeredgecolor=SURFACE,
                                  markersize=8, label="Oura, Garmin, Apple Watch combined")],
              loc="lower right", frameon=False, fontsize=9)
    _frame(fig, "Where the pride lives",
           f"% of posts expressing {emotion.lower()} within each theme: WHOOP vs the other three brands")
    caption = ("Share of posts expressing pride & joy within each theme, WHOOP (bars, 95% intervals) "
               "vs the other three brands combined (diamonds); random sample only.")
    return fig, caption


def make_all(tables):
    """Builds and saves all five charts. Returns {name: (path, caption)}."""
    specs = {
        "1_whoop_emotion_by_stage": emotion_by_stage(tables["stage_by_brand"]),
        "2_anxiety_by_theme": emotion_by_theme(
            tables["theme_by_brand"], "Anxiety / worry", "Where the worry shows up",
            "% of posts expressing anxiety or worry within each theme, by brand"),
        "3_cancelling_emotions_by_brand": cancelling_emotions(tables["cancelling_by_brand"]),
        "4_pride_by_theme": pride_by_theme(tables["theme_by_brand"]),
        "5_confusion_by_theme": emotion_by_theme(
            tables["theme_by_brand"], "Confusion / doubt", "Where the confusion shows up",
            "% of posts expressing confusion or doubt within each theme, by brand"),
    }
    return {name: (save(fig, name), cap) for name, (fig, cap) in specs.items()}
