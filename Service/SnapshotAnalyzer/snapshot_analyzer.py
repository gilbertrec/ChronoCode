"""
snapshot_analyzer.py
---------------------
Performs a **snapshot analysis** of a Python project:

1.  Identify the project's current HEAD commit and its first parent.
2.  Determine which Python files changed between parent → HEAD.
3.  Checkout those files at both revisions into isolated staging directories
    (inside DataStore) so we never corrupt the active working tree.
4.  Run DPy on both staging directories.
5.  Convert DPy outputs to the unified smell CSV schema.
6.  Run StaticTracker to find newly-introduced and removed smells.
7.  Persist a summary to DataStore and print a brief report.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

# --- Resolve project root and add ManagerService to sys.path -----------------
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_MANAGER_DIR  = _PROJECT_ROOT / "Service" / "ManagerService"
if str(_MANAGER_DIR) not in sys.path:
    sys.path.insert(0, str(_MANAGER_DIR))

from analyzer_manager import (
    build_run_id,
    build_tracker_config,
    checkout_files_to_dir,
    collect_tracker_results,
    convert_dpy_outputs_to_unified_csv,
    copy_local_repository,
    count_smells_in_csv,
    create_run_directory,
    get_changed_python_files,
    get_commit_log,
    get_project_name_from_path,
    run_dpy,
    run_static_tracker,
    write_manifest,
    DATASTORE_ROOT,
)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_snapshot(
    project_path: str,
    dpy_cmd: str,
    python_executable: str = sys.executable,
    java_home: Optional[str] = None,
    verbose: bool = True,
) -> dict:
    """
    Execute a full snapshot analysis.

    Parameters
    ----------
    project_path : str
        Absolute path to a local Git repository (must already be cloned).
    dpy_cmd : str
        Path to the DPy executable.
    python_executable : str
        Python interpreter that has JPype + GitPython installed.
    java_home : str, optional
        Custom JAVA_HOME for RefactoringMiner.
    verbose : bool

    Returns
    -------
    dict
        Summary dict with counts of introduced and removed smells.
    """
    project_path_obj = Path(project_path).resolve()
    project_name = get_project_name_from_path(str(project_path_obj))

    # ── Step 1: Setup run directory ─────────────────────────────────────────
    run_id  = build_run_id(project_name)
    run_dir = create_run_directory(run_id)
    if verbose:
        print(f"\n[Snapshot] Run ID  : {run_id}")
        print(f"[Snapshot] Run dir : {run_dir}")

    # ── Step 2: Clone repo into DataStore (safe workspace) ──────────────────
    repo_dest = run_dir / "cloned_repo"
    repo_path = copy_local_repository(project_path_obj, repo_dest, verbose=verbose)

    # ── Step 3: Identify HEAD and parent commits ─────────────────────────────
    commits = get_commit_log(repo_path, max_count=2)
    if len(commits) < 2:
        print("[Snapshot] ERROR: Repository must have at least 2 commits for snapshot analysis.")
        return {}

    child_commit  = commits[0]["sha"]
    parent_commit = commits[1]["sha"]
    if verbose:
        print(f"[Snapshot] HEAD   (child)  : {child_commit[:12]}  {commits[0]['subject']}")
        print(f"[Snapshot] HEAD~1 (parent) : {parent_commit[:12]}  {commits[1]['subject']}")

    # ── Step 4: Identify changed Python files ────────────────────────────────
    changed_files = get_changed_python_files(repo_path, parent_commit, child_commit)
    if not changed_files:
        print("[Snapshot] No Python files changed between HEAD and HEAD~1. Nothing to analyse.")
        return {"introduced": 0, "removed": 0, "changed_files": 0}
    if verbose:
        print(f"[Snapshot] Changed .py files : {len(changed_files)}")
        for f in changed_files[:10]:
            print(f"           • {f}")
        if len(changed_files) > 10:
            print(f"           … and {len(changed_files) - 10} more")

    # ── Step 5: Checkout file snapshots ─────────────────────────────────────
    before_src = run_dir / "before_src"
    after_src  = run_dir / "after_src"
    if verbose:
        print(f"\n[Snapshot] Checking out parent files → {before_src}")
    checkout_files_to_dir(repo_path, parent_commit, changed_files, before_src)
    if verbose:
        print(f"[Snapshot] Checking out child  files → {after_src}")
    checkout_files_to_dir(repo_path, child_commit,  changed_files, after_src)

    # ── Step 6: Run DPy on both snapshots ───────────────────────────────────
    dpy_before_dir = run_dir / "dpy_before"
    dpy_after_dir  = run_dir / "dpy_after"
    if verbose:
        print(f"\n[Snapshot] Running DPy on parent snapshot …")
    run_dpy(dpy_cmd, before_src, dpy_before_dir, verbose=verbose)
    if verbose:
        print(f"[Snapshot] Running DPy on child  snapshot …")
    run_dpy(dpy_cmd, after_src,  dpy_after_dir,  verbose=verbose)

    # ── Step 7: Convert DPy outputs to unified CSV ───────────────────────────
    before_csv = run_dir / "before_smells.csv"
    after_csv  = run_dir / "after_smells.csv"
    n_before = convert_dpy_outputs_to_unified_csv(
        dpy_before_dir, before_csv,
        author=commits[1].get("author_name", ""),
        repo=project_name, commit_sha=parent_commit,
        src_dir=before_src,
    )
    n_after = convert_dpy_outputs_to_unified_csv(
        dpy_after_dir, after_csv,
        author=commits[0].get("author_name", ""),
        repo=project_name, commit_sha=child_commit,
        src_dir=after_src,
    )
    if verbose:
        print(f"\n[Snapshot] Smell rows — before: {n_before}  |  after: {n_after}")

    # ── Step 8: Run StaticTracker ────────────────────────────────────────────
    tracker_result_dir = str(run_dir / "tracker_results" / child_commit[:12])
    tracker_cfg = build_tracker_config(
        loc_repo_path=str(repo_path),
        remote_repo_path=f"file://{repo_path}",
        save_result_path=tracker_result_dir,
        parent_commit=parent_commit,
        parent_report_path=str(before_csv),
        child_commit=child_commit,
        child_report_path=str(after_csv),
    )
    config_yaml = run_dir / "tracker_configs" / f"{child_commit[:12]}.yaml"
    if verbose:
        print(f"\n[Snapshot] Running StaticTracker …")
    tracker_ok = run_static_tracker(
        tracker_cfg, config_yaml,
        python_executable=python_executable,
        java_home=java_home,
        verbose=verbose,
    )

    # ── Step 9: Collect and summarise results ────────────────────────────────
    summary = {
        "run_id": run_id,
        "project": project_name,
        "mode": "snapshot",
        "child_commit": child_commit,
        "parent_commit": parent_commit,
        "changed_py_files": len(changed_files),
        "dpy_smells_before": n_before,
        "dpy_smells_after": n_after,
        "tracker_success": tracker_ok,
        "introduced": 0,
        "removed": 0,
    }

    if tracker_ok:
        results = collect_tracker_results(tracker_result_dir)
        introduced = sum(count_smells_in_csv(p) for p in results["introduced"])
        removed    = sum(count_smells_in_csv(p) for p in results["removed"])
        summary["introduced"] = introduced
        summary["removed"]    = removed

    write_manifest(run_dir, summary)

    # ── Step 10: Print report ────────────────────────────────────────────────
    _print_snapshot_report(summary)
    return summary


# ---------------------------------------------------------------------------
# Pretty print
# ---------------------------------------------------------------------------

def _print_snapshot_report(summary: dict) -> None:
    sep = "=" * 60
    print(f"\n{sep}")
    print(f" SNAPSHOT ANALYSIS REPORT")
    print(sep)
    print(f" Project          : {summary.get('project')}")
    print(f" Run ID           : {summary.get('run_id')}")
    print(f" Child  commit    : {summary.get('child_commit', '')[:12]}")
    print(f" Parent commit    : {summary.get('parent_commit', '')[:12]}")
    print(f" Changed .py files: {summary.get('changed_py_files', 0)}")
    print(f" DPy smells (before/after): "
          f"{summary.get('dpy_smells_before', 0)} / {summary.get('dpy_smells_after', 0)}")
    print(f" StaticTracker OK : {summary.get('tracker_success')}")
    print(f" Smells INTRODUCED: {summary.get('introduced', 0)}")
    print(f" Smells REMOVED   : {summary.get('removed', 0)}")
    print(sep)
    print(f" Results stored in: DataStore/{summary.get('run_id')}/")
    print(sep)


# ---------------------------------------------------------------------------
# CLI usage
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Snapshot smell analysis")
    parser.add_argument("--project-path", required=True,
                        help="Path to local Python git repository")
    parser.add_argument("--dpy-path", required=True,
                        help="Path to DPy executable")
    parser.add_argument("--python", default=sys.executable,
                        help="Python interpreter with JPype installed")
    parser.add_argument("--java-home", default=None,
                        help="Override JAVA_HOME for StaticTracker")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    run_snapshot(
        project_path=args.project_path,
        dpy_cmd=args.dpy_path,
        python_executable=args.python,
        java_home=args.java_home,
        verbose=not args.quiet,
    )
