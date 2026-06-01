"""
plotter.py
----------
DataAnalysis layer:  aggregates and visualises results stored in a DataStore
run directory produced by SnapshotAnalyzer or HistoryAnalyzer.

Usage
-----
  python3 plotter.py --data-dir DataStore/<run_id>

Generates the following outputs inside ``<run_dir>/plots/``:

History mode
  ├── smells_over_time.png        – introduced/removed per commit (all authors)
  ├── smells_by_author_type.png   – bar chart: AI vs Human totals
  ├── cumulative_smells.png       – cumulative introduced/removed over time
  ├── smell_breakdown.png         – top-N smell names by frequency (from DPy CSVs)
  └── summary_table.csv           – aggregated numbers as a flat CSV

Snapshot mode
  └── snapshot_summary.png        – single-commit comparison bar chart
"""

from __future__ import annotations

import csv
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Try to import plotting libraries; give a clear error if missing
# ---------------------------------------------------------------------------
try:
    import matplotlib
    matplotlib.use("Agg")  # headless backend – safe for all environments
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker
    _MATPLOTLIB_OK = True
except ImportError:
    _MATPLOTLIB_OK = False

try:
    import pandas as pd
    _PANDAS_OK = True
except ImportError:
    _PANDAS_OK = False

# ---------------------------------------------------------------------------
# Colour palette (colour-blind friendly)
# ---------------------------------------------------------------------------
_COLOURS = {
    "Human":      "#4C72B0",   # muted blue
    "AI":         "#DD8452",   # muted orange
    "introduced": "#55A868",   # muted green
    "removed":    "#C44E52",   # muted red
    "neutral":    "#8172B2",   # purple
}
_FIG_DPI = 150
_FIG_SIZE = (12, 5)


# ===========================================================================
# Helpers
# ===========================================================================

def _load_manifest(run_dir: Path) -> dict:
    p = run_dir / "manifest.json"
    if p.exists():
        with open(p) as fh:
            return json.load(fh)
    return {}


def _load_commit_log(run_dir: Path) -> list[dict]:
    p = run_dir / "commit_log.json"
    if not p.exists():
        return []
    with open(p) as fh:
        return json.load(fh)


def _load_unified_csvs(run_dir: Path) -> list[dict]:
    """Read all unified smell CSV rows from after_smells files."""
    rows = []
    csv_dir = run_dir / "unified_csvs"
    if not csv_dir.exists():
        return rows
    for f in sorted(csv_dir.glob("*_after.csv")):
        try:
            with open(f, "r", encoding="utf-8", errors="replace") as fh:
                for row in csv.DictReader(fh):
                    rows.append(row)
        except Exception:
            pass
    return rows


def _save_fig(fig: "plt.Figure", plots_dir: Path, filename: str) -> None:
    plots_dir.mkdir(parents=True, exist_ok=True)
    out = plots_dir / filename
    fig.savefig(out, dpi=_FIG_DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  [Plot] Saved → {out}")


# ===========================================================================
# History plots
# ===========================================================================

def plot_smells_over_time(commit_log: list[dict], plots_dir: Path) -> None:
    """Line chart: introduced and removed smells per commit."""
    if not _MATPLOTLIB_OK:
        return
    x      = list(range(len(commit_log)))
    intro  = [e.get("introduced", 0) for e in commit_log]
    rem    = [e.get("removed",    0) for e in commit_log]
    labels = [e.get("sha", "")[:7]   for e in commit_log]

    fig, ax = plt.subplots(figsize=_FIG_SIZE)
    ax.plot(x, intro, color=_COLOURS["introduced"], label="Introduced", linewidth=1.5, marker="o", markersize=3)
    ax.plot(x, rem,   color=_COLOURS["removed"],    label="Removed",    linewidth=1.5, marker="s", markersize=3)
    ax.set_title("Smells Introduced and Removed per Commit", fontsize=13, fontweight="bold")
    ax.set_xlabel("Commit index (newest → oldest)", fontsize=10)
    ax.set_ylabel("Smell count", fontsize=10)
    ax.legend()
    ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    fig.tight_layout()
    _save_fig(fig, plots_dir, "smells_over_time.png")


def plot_smells_by_author_type(manifest: dict, plots_dir: Path) -> None:
    """Grouped bar chart: AI vs Human introduced/removed totals."""
    if not _MATPLOTLIB_OK:
        return
    agg = manifest.get("aggregated", {})
    tags = ["Human", "AI"]
    intro_vals = [agg.get(t, {}).get("introduced", 0) for t in tags]
    rem_vals   = [agg.get(t, {}).get("removed",    0) for t in tags]

    x = [0, 1]
    width = 0.3
    fig, ax = plt.subplots(figsize=(7, 5))
    b1 = ax.bar([v - width/2 for v in x], intro_vals, width, label="Introduced",
                color=[_COLOURS["introduced"]] * 2)
    b2 = ax.bar([v + width/2 for v in x], rem_vals,   width, label="Removed",
                color=[_COLOURS["removed"]] * 2)

    # Hatch bars for AI
    for bar in [b1[1], b2[1]]:
        bar.set_hatch("//")
        bar.set_edgecolor("white")

    ax.set_xticks(x)
    ax.set_xticklabels(["Human", "AI"], fontsize=11)
    ax.set_title("Smells Introduced vs Removed by Author Type", fontsize=13, fontweight="bold")
    ax.set_ylabel("Total smell count", fontsize=10)
    ax.legend()
    ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))

    for bars in (b1, b2):
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, h + 0.5, str(int(h)),
                    ha="center", va="bottom", fontsize=9)
    fig.tight_layout()
    _save_fig(fig, plots_dir, "smells_by_author_type.png")


def plot_cumulative_smells(commit_log: list[dict], plots_dir: Path) -> None:
    """Cumulative introduced and removed smells over the commit timeline."""
    if not _MATPLOTLIB_OK:
        return
    x = list(range(len(commit_log)))

    cum_intro_h, cum_rem_h = 0, 0
    cum_intro_ai, cum_rem_ai = 0, 0
    ci_h, cr_h, ci_ai, cr_ai = [], [], [], []

    for e in commit_log:
        tag = e.get("tag", "Human")
        if tag == "AI":
            cum_intro_ai += e.get("introduced", 0)
            cum_rem_ai   += e.get("removed",    0)
        else:
            cum_intro_h  += e.get("introduced", 0)
            cum_rem_h    += e.get("removed",    0)
        ci_h.append(cum_intro_h);  cr_h.append(cum_rem_h)
        ci_ai.append(cum_intro_ai); cr_ai.append(cum_rem_ai)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=True)
    for ax, ci, cr, tag in zip(axes, [ci_h, ci_ai], [cr_h, cr_ai], ["Human", "AI"]):
        ax.fill_between(x, ci, alpha=0.35, color=_COLOURS["introduced"], label="Introduced")
        ax.fill_between(x, cr, alpha=0.35, color=_COLOURS["removed"],    label="Removed")
        ax.plot(x, ci, color=_COLOURS["introduced"], linewidth=1.5)
        ax.plot(x, cr, color=_COLOURS["removed"],    linewidth=1.5)
        ax.set_title(f"Cumulative Smells — {tag}", fontsize=12, fontweight="bold")
        ax.set_xlabel("Commit index", fontsize=10)
        ax.set_ylabel("Cumulative count", fontsize=10)
        ax.legend()
    fig.suptitle("Cumulative Smell Trends by Author Type", fontsize=13, fontweight="bold", y=1.01)
    fig.tight_layout()
    _save_fig(fig, plots_dir, "cumulative_smells.png")


def plot_smell_breakdown(smell_rows: list[dict], plots_dir: Path, top_n: int = 15) -> None:
    """Horizontal bar chart: top-N smell names by frequency."""
    if not _MATPLOTLIB_OK or not smell_rows:
        return
    counts: defaultdict[str, int] = defaultdict(int)
    for row in smell_rows:
        name = row.get("smell_name", "Unknown").strip() or "Unknown"
        counts[name] += 1

    sorted_items = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:top_n]
    names  = [item[0] for item in reversed(sorted_items)]
    values = [item[1] for item in reversed(sorted_items)]

    fig, ax = plt.subplots(figsize=(10, max(4, len(names) * 0.4 + 1)))
    colours = [_COLOURS["neutral"]] * len(names)
    bars = ax.barh(names, values, color=colours, edgecolor="white")
    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
                str(val), va="center", fontsize=8)
    ax.set_title(f"Top {top_n} Smell Types (by frequency)", fontsize=13, fontweight="bold")
    ax.set_xlabel("Occurrences", fontsize=10)
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    fig.tight_layout()
    _save_fig(fig, plots_dir, "smell_breakdown.png")


def write_summary_table(manifest: dict, commit_log: list[dict], plots_dir: Path) -> None:
    """Write a flat CSV summary table."""
    plots_dir.mkdir(parents=True, exist_ok=True)
    out = plots_dir / "summary_table.csv"
    agg = manifest.get("aggregated", {})
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Author Type", "Commits Analysed", "Smells Introduced", "Smells Removed"])
        for tag in ("Human", "AI"):
            d = agg.get(tag, {})
            w.writerow([tag, d.get("commits_analysed", 0),
                        d.get("introduced", 0), d.get("removed", 0)])
    print(f"  [Plot] Summary table → {out}")


# ===========================================================================
# Snapshot plot
# ===========================================================================

def plot_snapshot_summary(manifest: dict, plots_dir: Path) -> None:
    """Single bar chart for a snapshot analysis result."""
    if not _MATPLOTLIB_OK:
        return
    intro = manifest.get("introduced", 0)
    rem   = manifest.get("removed",    0)
    child = manifest.get("child_commit", "")[:12]

    fig, ax = plt.subplots(figsize=(6, 4))
    bars = ax.bar(["Introduced", "Removed"],
                  [intro, rem],
                  color=[_COLOURS["introduced"], _COLOURS["removed"]],
                  edgecolor="white", width=0.5)
    for bar, val in zip(bars, [intro, rem]):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                str(val), ha="center", va="bottom", fontsize=11, fontweight="bold")
    ax.set_title(f"Snapshot: Smells at commit {child}", fontsize=12, fontweight="bold")
    ax.set_ylabel("Smell count", fontsize=10)
    ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    fig.tight_layout()
    _save_fig(fig, plots_dir, "snapshot_summary.png")


# ===========================================================================
# Main dispatcher
# ===========================================================================

def analyse_run(run_dir_path: str, top_n: int = 15) -> None:
    """
    Load a DataStore run directory and produce all applicable plots.

    Parameters
    ----------
    run_dir_path : str
        Path to the run directory (e.g. ``DataStore/my_project_abc12345``).
    top_n : int
        Number of top smell names to show in the breakdown chart.
    """
    if not _MATPLOTLIB_OK:
        print("[Plotter] ERROR: matplotlib is not installed. "
              "Run: pip install matplotlib")
        return

    run_dir   = Path(run_dir_path).resolve()
    plots_dir = run_dir / "plots"
    manifest  = _load_manifest(run_dir)
    mode      = manifest.get("mode", "unknown")

    print(f"\n[Plotter] Analysing run: {run_dir.name}  (mode={mode})")

    if mode == "history":
        commit_log = _load_commit_log(run_dir)
        smell_rows = _load_unified_csvs(run_dir)
        if commit_log:
            plot_smells_over_time(commit_log, plots_dir)
            plot_cumulative_smells(commit_log, plots_dir)
        plot_smells_by_author_type(manifest, plots_dir)
        plot_smell_breakdown(smell_rows, plots_dir, top_n=top_n)
        write_summary_table(manifest, commit_log, plots_dir)

    elif mode == "snapshot":
        plot_snapshot_summary(manifest, plots_dir)

    else:
        print(f"[Plotter] Unknown mode '{mode}'. Attempting best-effort snapshot plot.")
        plot_snapshot_summary(manifest, plots_dir)

    print(f"[Plotter] Done. All plots in: {plots_dir}/")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Plot DataStore analysis results")
    parser.add_argument("--data-dir", required=True,
                        help="Path to a DataStore run directory")
    parser.add_argument("--top-n", type=int, default=15,
                        help="Top N smell types to show in breakdown chart")
    args = parser.parse_args()
    analyse_run(args.data_dir, top_n=args.top_n)
