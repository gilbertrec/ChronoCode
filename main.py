#!/usr/bin/env python3
"""
main.py  –  CodeQualityInspector  CLI
======================================
Static analysis tool for Python projects that tracks code-smell introductions
and removals using DesignitePy (DPy) and StaticCodeTracker.

Commands
--------
  snapshot        Analyse the latest commit vs its parent.
  history         Walk the full (or bounded) commit history.
  analyze-data    Plot / aggregate results from a prior run directory.

Examples
--------
  # Snapshot of the current HEAD
  python3 main.py snapshot \\
      --project-path /path/to/my_python_project \\
      --dpy-path     /path/to/DPy

  # History over the last 50 commits (skip tracker for speed)
  python3 main.py history \\
      --project-path /path/to/my_python_project \\
      --dpy-path     /path/to/DPy \\
      --commits 50   \\
      --skip-tracker

  # Plot a previously computed run
  python3 main.py analyze-data \\
      --data-dir DataStore/my_project_abc12345
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Resolve project root and add sub-packages to sys.path
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent

def _add_to_path(rel: str) -> None:
    p = str(_PROJECT_ROOT / rel)
    if p not in sys.path:
        sys.path.insert(0, p)

_add_to_path("Service/ManagerService")
_add_to_path("Service/SnapshotAnalyzer")
_add_to_path("Service/HistoryAnalyzer")
_add_to_path("Service/Taggers/HeuristicTagger")
_add_to_path("DataAnalysis")


# ===========================================================================
# Shared option helpers
# ===========================================================================

def _add_common_args(parser: argparse.ArgumentParser) -> None:
    """Add arguments shared by snapshot and history sub-commands."""
    parser.add_argument(
        "--config", "-c",
        help="Path to a YAML configuration file. Overrides CLI arguments.",
    )
    parser.add_argument(
        "--project-path",
        help="Absolute (or relative) path to the local Python git repository to analyse.",
    )
    parser.add_argument(
        "--dpy-path",
        help=(
            "Path to the DPy (DesignitePy) executable.  "
            "On macOS you must provide a macOS-native build; "
            "the bundled Linux ELF binary will not run directly."
        ),
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help=(
            "Python interpreter that has JPype and GitPython installed "
            "(used to launch StaticCodeTracker).  "
            "Defaults to the current interpreter."
        ),
    )
    parser.add_argument(
        "--java-home",
        default=None,
        help=(
            "Override JAVA_HOME used by StaticCodeTracker / RefactoringMiner.  "
            "If not set, the environment variable JAVA_HOME is used."
        ),
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress progress output.",
    )


# ===========================================================================
# Sub-command handlers
# ===========================================================================

def _cmd_snapshot(args: argparse.Namespace) -> None:
    from snapshot_analyzer import run_snapshot

    project_path = str(Path(args.project_path).resolve())
    dpy_cmd      = str(Path(args.dpy_path).resolve())

    _validate_paths(project_path=project_path, dpy_cmd=dpy_cmd)

    run_snapshot(
        project_path=project_path,
        dpy_cmd=dpy_cmd,
        python_executable=args.python,
        java_home=args.java_home or os.environ.get("JAVA_HOME"),
        verbose=not args.quiet,
    )


def _cmd_history(args: argparse.Namespace) -> None:
    from history_analyzer import run_history

    project_path = str(Path(args.project_path).resolve())
    dpy_cmd      = str(Path(args.dpy_path).resolve())

    _validate_paths(project_path=project_path, dpy_cmd=dpy_cmd)

    run_history(
        project_path=project_path,
        dpy_cmd=dpy_cmd,
        python_executable=args.python,
        java_home=args.java_home or os.environ.get("JAVA_HOME"),
        max_commits=args.commits,
        since=args.since,
        skip_tracker=args.skip_tracker,
        verbose=not args.quiet,
        workers=getattr(args, "workers", 1),
    )


def _cmd_analyze_data(args: argparse.Namespace) -> None:
    from plotter import analyse_run

    data_dir = str(Path(args.data_dir).resolve())
    if not Path(data_dir).is_dir():
        _die(f"Data directory not found: {data_dir}")

    analyse_run(data_dir, top_n=args.top_n)


# ===========================================================================
# Validation helpers
# ===========================================================================

def _validate_paths(project_path: str, dpy_cmd: str) -> None:
    if not Path(project_path).is_dir():
        _die(f"Project path does not exist or is not a directory: {project_path}")
    git_dir = Path(project_path) / ".git"
    if not git_dir.exists():
        _die(
            f"No .git directory found in '{project_path}'.  "
            "The project must be a git repository."
        )
    if not Path(dpy_cmd).is_file():
        _die(
            f"DPy executable not found at '{dpy_cmd}'.  "
            "Please provide the correct path with --dpy-path."
        )


def _die(message: str) -> None:
    print(f"\n[ERROR] {message}\n", file=sys.stderr)
    sys.exit(1)


# ===========================================================================
# Argument parser
# ===========================================================================

import yaml

def _merge_config(args: argparse.Namespace) -> None:
    if not hasattr(args, "config") or not args.config:
        return
        
    config_path = Path(args.config)
    if not config_path.exists():
        _die(f"Config file not found: {args.config}")
        
    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f)
        
    if not cfg:
        return
        
    # Override missing args with config values
    for k, v in cfg.items():
        k_args = k.replace("-", "_")
        if hasattr(args, k_args):
            # Only override if the current value is the default (or None)
            # Actually, let's just override if it's None or False (for booleans)
            current = getattr(args, k_args)
            if current is None or current is False or current == sys.executable:
                setattr(args, k_args, v)

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 main.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    # ── snapshot ─────────────────────────────────────────────────────────────
    snap_p = sub.add_parser(
        "snapshot",
        help="Analyse HEAD vs HEAD~1 of a Python repository.",
        description=(
            "Snapshot mode: analyses only the most recent commit against its parent.  "
            "Useful for CI integration or quick checks."
        ),
    )
    _add_common_args(snap_p)
    snap_p.set_defaults(func=_cmd_snapshot)

    # ── history ──────────────────────────────────────────────────────────────
    hist_p = sub.add_parser(
        "history",
        help="Walk the commit history and track smell trends (AI vs Human).",
        description=(
            "History mode: iterates every commit (or a bounded window) and computes "
            "smell introductions and removals per commit, categorised by whether the "
            "commit is AI-generated or Human-authored."
        ),
    )
    _add_common_args(hist_p)
    hist_p.add_argument(
        "--commits", type=int, default=None, metavar="N",
        help="Maximum number of commits to analyse (newest first).  Default: all.",
    )
    hist_p.add_argument(
        "--since", default=None, metavar="DATE_OR_SHA",
        help="Analyse only commits after this date/SHA (passed to git log --since).",
    )
    hist_p.add_argument(
        "--skip-tracker", action="store_true",
        help=(
            "Skip StaticCodeTracker and approximate introduced/removed counts from "
            "raw DPy deltas.  Much faster but less accurate."
        ),
    )
    hist_p.add_argument(
        "--workers", type=int, default=1, metavar="N",
        help="Number of concurrent workers for commit analysis. Default: 1.",
    )
    hist_p.set_defaults(func=_cmd_history)

    # ── analyze-data ─────────────────────────────────────────────────────────
    plot_p = sub.add_parser(
        "analyze-data",
        help="Generate plots and aggregation from a previously saved DataStore run.",
        description=(
            "analyze-data mode: reads a run directory inside DataStore/ and "
            "generates matplotlib charts (smells over time, AI vs Human totals, "
            "cumulative trends, top smell breakdown) and a summary CSV."
        ),
    )
    plot_p.add_argument(
        "--config", "-c",
        help="Path to a YAML configuration file. Overrides CLI arguments.",
    )
    plot_p.add_argument(
        "--data-dir", metavar="PATH",
        help="Path to a DataStore run directory (e.g. DataStore/my_project_abc12345).",
    )
    plot_p.add_argument(
        "--top-n", type=int, default=15, metavar="N",
        help="Number of top smell types to show in the breakdown chart.  Default: 15.",
    )
    plot_p.set_defaults(func=_cmd_analyze_data)

    return parser


# ===========================================================================
# Entry point
# ===========================================================================

def main(argv: list[str] | None = None) -> None:
    # If the user runs `python3 main.py --config config.yaml`, there's no subcommand!
    # So we should intercept it or parse config first.
    if argv is None:
        argv = sys.argv[1:]
        
    config_file = None
    if "--config" in argv:
        config_file = argv[argv.index("--config") + 1]
    elif "-c" in argv:
        config_file = argv[argv.index("-c") + 1]
    else:
        default_settings = _PROJECT_ROOT / "settings.yaml"
        if default_settings.exists():
            config_file = str(default_settings)
            argv.extend(["-c", config_file])
        
    # Pre-parse config to inject command and args if provided
    if config_file:
        config_path = Path(config_file)
        if config_path.exists():
            with open(config_path, "r") as f:
                cfg = yaml.safe_load(f)
            if cfg and "command" in cfg:
                # Inject the command if the user didn't type it (e.g. "python3 main.py -c conf.yml")
                if not any(arg in ["snapshot", "history", "analyze-data"] for arg in argv):
                    argv.insert(0, cfg["command"])

    parser = build_parser()
    args   = parser.parse_args(argv)
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
        
    _merge_config(args)
    
    if args.command in ["snapshot", "history"]:
        if not args.project_path or not args.dpy_path:
            _die("Missing --project-path or --dpy-path. Provide via CLI or config file.")
    elif args.command == "analyze-data":
        if not args.data_dir:
            _die("Missing --data-dir. Provide via CLI or config file.")
            
    args.func(args)


if __name__ == "__main__":
    main()
