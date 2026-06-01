"""
history_analyzer.py
--------------------
Performs a **history analysis** of a Python project by walking the commit log
and, for every commit that changes at least one Python file:

1.  Tag the commit as AI-generated or Human-authored (HeuristicTagger).
2.  Checkout the changed files at the parent and child revisions into
    isolated staging directories (no active-tree checkouts).
3.  Run DPy on both staging sets.
4.  Convert DPy outputs to the unified smell CSV schema.
5.  Run StaticTracker to find newly-introduced and removed smells.
6.  Accumulate results grouped by author tag.

Outputs stored under ``DataStore/{run_id}/``:
  - per-commit tracker results under ``tracker_results/{sha[:12]}/``
  - a ``summary.json`` with aggregated counts
  - a ``commit_log.json`` with per-commit detail
"""

from __future__ import annotations

import csv
import json
import sys
import concurrent.futures
from pathlib import Path
from typing import Optional

# --- Resolve paths -----------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_MANAGER_DIR  = _PROJECT_ROOT / "Service" / "ManagerService"
_TAGGER_DIR   = _PROJECT_ROOT / "Service" / "Taggers" / "HeuristicTagger"
for _p in (_MANAGER_DIR, _TAGGER_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

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
    parse_tracker_csv,
    DATASTORE_ROOT,
)
from heuristic_tagger import tag_commit, TAG_AI, TAG_HUMAN


# ===========================================================================
# History analysis
# ===========================================================================

def _process_single_commit(
    idx: int,
    total_commits: int,
    commit_info: dict,
    parent_sha: str,
    project_name: str,
    repo_path: Path,
    run_dir: Path,
    dpy_cmd: str,
    skip_tracker: bool,
    python_executable: str,
    java_home: Optional[str],
    verbose: bool
) -> dict:
    """Helper to process a single commit pair, isolated for parallel execution."""
    child_sha = commit_info["sha"]

    # Tag commit
    tag_result = tag_commit(
        message=commit_info.get("message", ""),
        author_name=commit_info.get("author_name", ""),
        author_email=commit_info.get("author_email", ""),
        committer_name=commit_info.get("committer_name", ""),
        committer_email=commit_info.get("committer_email", ""),
    )
    tag = tag_result.tag

    if verbose:
        print(
            f"[History] [{idx+1:>4}/{total_commits}] {child_sha[:10]}  "
            f"[{tag}]  {commit_info['subject'][:60]}"
        )

    # Find changed Python files
    changed_py = get_changed_python_files(repo_path, parent_sha, child_sha)
    if not changed_py:
        if verbose:
            print(f"           → No Python files changed, skipping.")
        return {"status": "skipped_no_py"}

    # ── Checkout files ───────────────────────────────────────────────────
    short = child_sha[:12]
    before_src = run_dir / "staging" / short / "before"
    after_src  = run_dir / "staging" / short / "after"
    checkout_files_to_dir(repo_path, parent_sha, changed_py, before_src)
    checkout_files_to_dir(repo_path, child_sha,  changed_py, after_src)

    # ── DPy ─────────────────────────────────────────────────────────────
    dpy_before_dir = run_dir / "dpy_before" / short
    dpy_after_dir  = run_dir / "dpy_after"  / short
    dpy_before_ok = run_dpy(dpy_cmd, before_src, dpy_before_dir, verbose=False) == 0
    dpy_after_ok  = run_dpy(dpy_cmd, after_src,  dpy_after_dir,  verbose=False) == 0

    # ── Convert to unified CSV ───────────────────────────────────────────
    before_csv = run_dir / "unified_csvs" / f"{short}_before.csv"
    after_csv  = run_dir / "unified_csvs" / f"{short}_after.csv"
    (run_dir / "unified_csvs").mkdir(parents=True, exist_ok=True)

    n_before = convert_dpy_outputs_to_unified_csv(
        dpy_before_dir, before_csv,
        author=commit_info.get("author_name", ""),
        repo=project_name, commit_sha=parent_sha,
        src_dir=before_src,
    ) if dpy_before_ok else 0
    n_after = convert_dpy_outputs_to_unified_csv(
        dpy_after_dir, after_csv,
        author=commit_info.get("author_name", ""),
        repo=project_name, commit_sha=child_sha,
        src_dir=after_src,
    ) if dpy_after_ok else 0

    # ── StaticTracker ────────────────────────────────────────────────────
    introduced = 0
    removed    = 0
    introduced_smells = []
    removed_smells = []
    tracker_ok = False

    if not skip_tracker:
        tracker_result_dir = str(run_dir / "tracker_results" / short)
        tracker_cfg = build_tracker_config(
            loc_repo_path=str(repo_path),
            remote_repo_path=f"file://{repo_path}",
            save_result_path=tracker_result_dir,
            parent_commit=parent_sha,
            parent_report_path=str(before_csv),
            child_commit=child_sha,
            child_report_path=str(after_csv),
        )
        config_yaml = run_dir / "tracker_configs" / f"{short}.yaml"
        tracker_ok = run_static_tracker(
            tracker_cfg, config_yaml,
            python_executable=python_executable,
            java_home=java_home,
            verbose=False,
        )
        if tracker_ok:
            results    = collect_tracker_results(tracker_result_dir)
            for p in results["introduced"]:
                introduced_smells.extend(parse_tracker_csv(p))
            for p in results["removed"]:
                removed_smells.extend(parse_tracker_csv(p))
            
            introduced = len(introduced_smells)
            removed    = len(removed_smells)
    else:
        # Without tracker, approximate using raw DPy delta
        introduced = max(0, n_after  - n_before)
        removed    = max(0, n_before - n_after)

    entry = {
        "sha": child_sha,
        "parent_sha": parent_sha,
        "subject": commit_info["subject"],
        "author_name": commit_info.get("author_name", ""),
        "author_email": commit_info.get("author_email", ""),
        "date": commit_info.get("date", ""),
        "co_authors": commit_info.get("co_authors", []),
        "tag": tag,
        "tag_reasons": tag_result.reasons,
        "changed_py_files": len(changed_py),
        "dpy_smells_before": n_before,
        "dpy_smells_after": n_after,
        "tracker_success": tracker_ok,
        "introduced": introduced,
        "removed": removed,
        "introduced_smells": introduced_smells,
        "removed_smells": removed_smells,
    }

    if verbose:
        print(f"           → ✓  introduced={introduced}  removed={removed}")

    return {"status": "ok", "entry": entry, "tag": tag, "introduced": introduced, "removed": removed}


def run_history(
    project_path: str,
    dpy_cmd: str,
    python_executable: str = sys.executable,
    java_home: Optional[str] = None,
    max_commits: Optional[int] = None,
    since: Optional[str] = None,
    verbose: bool = True,
    skip_tracker: bool = False,
    workers: int = 1,
) -> dict:
    """
    Walk the commit history of *project_path* and collect smell
    introduction/removal data per commit, tagged by AI vs. Human authorship.

    Parameters
    ----------
    project_path : str
        Absolute path to a local Git repository.
    dpy_cmd : str
        Path to the DPy executable.
    python_executable : str
        Python interpreter with JPype + GitPython installed.
    java_home : str, optional
        Custom JAVA_HOME for RefactoringMiner.
    max_commits : int, optional
        Limit the number of commits analysed (newest first).
    since : str, optional
        ``--since`` value passed to git log (date string or commit SHA).
    verbose : bool
    skip_tracker : bool
        If True, skip StaticTracker and only collect DPy raw counts
        (useful for quick dry-runs).
    workers : int
        Number of parallel workers to process commits concurrently.

    Returns
    -------
    dict
        Aggregated summary.
    """
    project_path_obj = Path(project_path).resolve()
    project_name = get_project_name_from_path(str(project_path_obj))

    # ── Setup run ────────────────────────────────────────────────────────────
    run_id  = build_run_id(project_name)
    run_dir = create_run_directory(run_id)
    if verbose:
        print(f"\n[History] Run ID  : {run_id}")
        print(f"[History] Run dir : {run_dir}")

    # ── Clone repo into DataStore ─────────────────────────────────────────────
    repo_dest = run_dir / "cloned_repo"
    repo_path = copy_local_repository(project_path_obj, repo_dest, verbose=verbose)

    # ── Fetch commit log ─────────────────────────────────────────────────────
    commits = get_commit_log(repo_path, max_count=max_commits, since=since)
    if verbose:
        print(f"[History] Total commits to inspect: {len(commits)}")

    # ── Per-commit aggregation ───────────────────────────────────────────────
    aggregated = {
        TAG_AI:    {"introduced": 0, "removed": 0, "commits_analysed": 0},
        TAG_HUMAN: {"introduced": 0, "removed": 0, "commits_analysed": 0},
    }
    commit_log_entries: list[dict] = []
    skipped_no_py  = 0
    skipped_no_par = 0

    # Build tasks
    tasks = []
    for idx, commit_info in enumerate(commits):
        if idx + 1 >= len(commits):
            skipped_no_par += 1
            continue
        parent_sha = commits[idx + 1]["sha"]
        tasks.append((idx, commit_info, parent_sha))

    if workers > 1:
        if verbose:
            print(f"[History] Running with {workers} parallel workers...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            # We use executor.map to maintain the original commit order
            results = executor.map(
                lambda t: _process_single_commit(
                    t[0], len(commits), t[1], t[2],
                    project_name, repo_path, run_dir, dpy_cmd, skip_tracker, python_executable, java_home, verbose
                ),
                tasks
            )
            for res in results:
                if res["status"] == "skipped_no_py":
                    skipped_no_py += 1
                elif res["status"] == "ok":
                    tag = res["tag"]
                    aggregated[tag]["introduced"]       += res["introduced"]
                    aggregated[tag]["removed"]          += res["removed"]
                    aggregated[tag]["commits_analysed"] += 1
                    commit_log_entries.append(res["entry"])
    else:
        for t in tasks:
            res = _process_single_commit(
                t[0], len(commits), t[1], t[2],
                project_name, repo_path, run_dir, dpy_cmd, skip_tracker, python_executable, java_home, verbose
            )
            if res["status"] == "skipped_no_py":
                skipped_no_py += 1
            elif res["status"] == "ok":
                tag = res["tag"]
                aggregated[tag]["introduced"]       += res["introduced"]
                aggregated[tag]["removed"]          += res["removed"]
                aggregated[tag]["commits_analysed"] += 1
                commit_log_entries.append(res["entry"])

    # ── Persist results ───────────────────────────────────────────────────────
    commit_log_path = run_dir / "commit_log.json"
    with open(commit_log_path, "w", encoding="utf-8") as fh:
        json.dump(commit_log_entries, fh, indent=2)

    summary = {
        "run_id": run_id,
        "project": project_name,
        "mode": "history",
        "total_commits_inspected": len(commits),
        "skipped_no_python_changes": skipped_no_py,
        "skipped_no_parent": skipped_no_par,
        "commits_analysed": len(commit_log_entries),
        "aggregated": aggregated,
        "commit_log_path": str(commit_log_path),
    }
    write_manifest(run_dir, summary)

    _print_history_report(summary)
    return summary


# ---------------------------------------------------------------------------
# Pretty print
# ---------------------------------------------------------------------------

def _print_history_report(summary: dict) -> None:
    sep = "=" * 60
    agg = summary.get("aggregated", {})
    print(f"\n{sep}")
    print(f" HISTORY ANALYSIS REPORT")
    print(sep)
    print(f" Project           : {summary.get('project')}")
    print(f" Run ID            : {summary.get('run_id')}")
    print(f" Commits inspected : {summary.get('total_commits_inspected', 0)}")
    print(f" Commits analysed  : {summary.get('commits_analysed', 0)}")
    print(f" Skipped (no .py)  : {summary.get('skipped_no_python_changes', 0)}")
    print()
    for tag in ("Human", "AI"):
        d = agg.get(tag, {})
        print(f" [{tag:>5}] commits={d.get('commits_analysed',0):>5}  "
              f"introduced={d.get('introduced',0):>6}  "
              f"removed={d.get('removed',0):>6}")
    print(sep)
    print(f" Results in: DataStore/{summary.get('run_id')}/")
    print(sep)


# ---------------------------------------------------------------------------
# CLI usage
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="History smell analysis")
    parser.add_argument("--project-path", required=True)
    parser.add_argument("--dpy-path", required=True)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--java-home", default=None)
    parser.add_argument("--commits", type=int, default=None,
                        help="Maximum number of commits to analyse")
    parser.add_argument("--since", default=None)
    parser.add_argument("--skip-tracker", action="store_true",
                        help="Skip StaticTracker (use DPy delta approximation)")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--workers", type=int, default=1,
                        help="Number of concurrent workers for commit analysis")
    args = parser.parse_args()

    run_history(
        project_path=args.project_path,
        dpy_cmd=args.dpy_path,
        python_executable=args.python,
        java_home=args.java_home,
        max_commits=args.commits,
        since=args.since,
        skip_tracker=args.skip_tracker,
        verbose=not args.quiet,
        workers=args.workers,
    )
