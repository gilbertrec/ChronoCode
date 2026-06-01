"""
analyzer_manager.py
--------------------
Central orchestration service that:
  - Builds the DataStore output folder structure
  - Optionally clones a remote git repository
  - Exposes helpers to:
      * Run DPy
      * Convert raw DPy JSON/CSV output to the unified smell CSV schema
      * Launch StaticTracker
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import time
import yaml
from pathlib import Path
from typing import Optional

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_STATIC_TRACKER_DIR = _PROJECT_ROOT / "Service" / "StaticCodeTracker"
if str(_STATIC_TRACKER_DIR) not in sys.path:
    sys.path.insert(0, str(_STATIC_TRACKER_DIR))

DATASTORE_ROOT = _PROJECT_ROOT / "DataStore"
DATASTORE_ROOT.mkdir(parents=True, exist_ok=True)

_UNIFIED_COLUMNS = [
    "Agent", "Author", "Repo", "CommitSha",
    "smell_type", "smell_name", "Method", "Line", "File", "Description",
]

_SHA_PREFIX_RE = re.compile(r"^[0-9a-f]{40}/")

def get_project_name_from_path(project_path: str) -> str:
    return Path(project_path).name

def build_run_id(project_name: str, timestamp: Optional[float] = None) -> str:
    if timestamp is None:
        timestamp = time.time()
    raw = f"{project_name}_{timestamp}"
    h = hashlib.md5(raw.encode("utf-8")).hexdigest()[:8]
    return f"{project_name}_{h}"

def create_run_directory(run_id: str) -> Path:
    run_dir = DATASTORE_ROOT / run_id
    for subdir in ["cloned_repo", "dpy_before", "dpy_after", "tracker_results", "plots", "tracker_configs"]:
        (run_dir / subdir).mkdir(parents=True, exist_ok=True)
    return run_dir

def copy_local_repository(repo_path: Path, dest_dir: Path, verbose: bool = False) -> Path:
    if dest_dir.exists() and any(dest_dir.iterdir()):
        if verbose:
            print(f"[Manager] Directory {dest_dir} not empty, skipping local copy.")
        return dest_dir
    cmd = ["git", "clone", "--quiet", str(repo_path), str(dest_dir)]
    res = subprocess.run(cmd, capture_output=not verbose, text=True)
    if res.returncode != 0:
        print(f"[Manager] Error cloning local repo: {res.stderr}")
    return dest_dir

def get_commit_log(repo_path: Path, max_count: Optional[int] = 2, since: Optional[str] = None) -> list[dict]:
    cmd = ["git", "log", "--format=%H%x00%s%x00%an%x00%cI%x00%b%x1E"]
    if max_count is not None:
        cmd.append(f"-{max_count}")
    if since:
        cmd.append(f"--since={since}")
    res = subprocess.run(cmd, cwd=str(repo_path), capture_output=True, text=True)
    commits = []
    for record in res.stdout.split("\x1e"):
        record = record.strip()
        if not record:
            continue
        parts = record.split("\x00")
        if len(parts) >= 4:
            sha = parts[0]
            subject = parts[1]
            author_name = parts[2]
            date = parts[3]
            body = parts[4] if len(parts) > 4 else ""
            
            co_authors = []
            for b_line in body.split("\n"):
                if b_line.strip().lower().startswith("co-authored-by:"):
                    co_authors.append(b_line.split(":", 1)[1].strip())
                    
            commits.append({
                "sha": sha, 
                "subject": subject, 
                "author_name": author_name,
                "date": date,
                "co_authors": co_authors
            })
    return commits

def get_changed_python_files(repo_path: Path, parent_commit: str, child_commit: str) -> list[str]:
    cmd = ["git", "diff", "--name-only", parent_commit, child_commit]
    res = subprocess.run(cmd, cwd=str(repo_path), capture_output=True, text=True)
    return [line.strip() for line in res.stdout.splitlines() if line.strip().endswith(".py")]

def checkout_files_to_dir(repo_path: Path, commit: str, files: list[str], dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for f in files:
        res = subprocess.run(["git", "show", f"{commit}:{f}"], cwd=str(repo_path), capture_output=True)
        if res.returncode == 0:
            out_file = dest / f
            out_file.parent.mkdir(parents=True, exist_ok=True)
            with open(out_file, "wb") as out:
                out.write(res.stdout)

def run_dpy(dpy_cmd: str, input_dir: Path, output_dir: Path, verbose: bool = False) -> int:
    cmd = [
        dpy_cmd,
        "analyze",
        "-i", str(input_dir),
        "-o", str(output_dir),
        "-f", "csv"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    with open(output_dir / "dpy_stdout.log", "w") as f:
        f.write(res.stdout)
    with open(output_dir / "dpy_stderr.log", "w") as f:
        f.write(res.stderr)
    return res.returncode

def _infer_smell_type(filename: str) -> str:
    name = filename.lower()
    if "design" in name:
        return "design"
    if "implementation" in name:
        return "implementation"
    if "architecture" in name:
        return "architecture"
    return "unknown"

def _strip_sha_from_path(filepath: str) -> str:
    return _SHA_PREFIX_RE.sub("", filepath)

def find_dpy_csv_outputs(dpy_out_dir: Path) -> list[Path]:
    return list(dpy_out_dir.glob("*smells*.csv"))

def find_dpy_json_outputs(dpy_out_dir: Path) -> list[Path]:
    return list(dpy_out_dir.glob("*.json"))

def convert_dpy_outputs_to_unified_csv(
    dpy_out_dir: Path,
    unified_csv_path: Path,
    agent: str = "",
    author: str = "",
    repo: str = "",
    commit_sha: str = "",
    src_dir: Optional[Path] = None,
) -> int:
    import json as _json

    rows_written = 0
    unified_csv_path.parent.mkdir(parents=True, exist_ok=True)

    with open(unified_csv_path, "w", newline="", encoding="utf-8") as fout:
        writer = csv.DictWriter(fout, fieldnames=_UNIFIED_COLUMNS)
        writer.writeheader()

        for csv_file in find_dpy_csv_outputs(dpy_out_dir):
            smell_type = _infer_smell_type(csv_file.name)
            try:
                with open(csv_file, "r", encoding="utf-8", errors="replace") as fin:
                    reader = csv.DictReader(fin)
                    for row in reader:
                        smell_name = (
                            row.get("Smell") or row.get("smell_name") or
                            row.get("SmellName") or "Unknown"
                        ).strip()
                        method = (
                            row.get("Method Name") or row.get("Method") or ""
                        ).strip()
                        line = (
                            row.get("Line no") or row.get("Line") or row.get("line") or ""
                        ).strip()
                        file_path = (
                            row.get("File") or row.get("Type Name") or ""
                        ).strip()
                        if src_dir and file_path:
                            try:
                                file_path = str(Path(file_path).relative_to(src_dir))
                            except ValueError:
                                pass
                        description = (
                            row.get("Cause") or row.get("Description") or ""
                        ).strip()
                        writer.writerow({
                            "Agent": agent, "Author": author,
                            "Repo": repo, "CommitSha": commit_sha,
                            "smell_type": smell_type, "smell_name": smell_name,
                            "Method": method, "Line": line,
                            "File": _strip_sha_from_path(file_path),
                            "Description": description,
                        })
                        rows_written += 1
            except Exception as exc:
                print(f"[Manager] Warning: could not parse CSV {csv_file}: {exc}")

        for json_file in find_dpy_json_outputs(dpy_out_dir):
            smell_type = _infer_smell_type(json_file.name)
            try:
                with open(json_file, "r", encoding="utf-8", errors="replace") as fin:
                    data = _json.load(fin)
                if isinstance(data, list):
                    smell_list = data
                elif isinstance(data, dict):
                    smell_list = []
                    for v in data.values():
                        if isinstance(v, list):
                            smell_list.extend(v)
                else:
                    smell_list = []

                for item in smell_list:
                    if not isinstance(item, dict):
                        continue
                    smell_name = (
                        item.get("smell") or item.get("name") or
                        item.get("SmellName") or "Unknown"
                    )
                    method = item.get("method") or item.get("Method Name") or ""
                    line   = str(item.get("line") or item.get("Line no") or item.get("Line") or "")
                    file_path = item.get("file") or item.get("File") or ""
                    if src_dir and file_path:
                        try:
                            file_path = str(Path(str(file_path).strip()).relative_to(src_dir))
                        except ValueError:
                            pass
                    description = item.get("cause") or item.get("description") or ""
                    writer.writerow({
                        "Agent": agent, "Author": author,
                        "Repo": repo, "CommitSha": commit_sha,
                        "smell_type": smell_type,
                        "smell_name": str(smell_name).strip(),
                        "Method": str(method).strip(),
                        "Line": line.strip(),
                        "File": _strip_sha_from_path(str(file_path).strip()),
                        "Description": str(description).strip(),
                    })
                    rows_written += 1
            except Exception as exc:
                print(f"[Manager] Warning: could not parse JSON {json_file}: {exc}")

    return rows_written

def build_tracker_config(
    loc_repo_path: str,
    remote_repo_path: str,
    save_result_path: str,
    parent_commit: str,
    parent_report_path: str,
    child_commit: str,
    child_report_path: str
) -> dict:
    java_jar_path = _STATIC_TRACKER_DIR / "refactoringJava" / "target" / "refactoringJava-1.0-SNAPSHOT-jar-with-dependencies.jar"
    return {
        "static_tool": "DesignitePy",
        "parent_commit": parent_commit,
        "child_commit": child_commit,
        "loc_repo_path": loc_repo_path,
        "remote_repo_path": remote_repo_path,
        "parent_report_path": parent_report_path,
        "child_report_path": child_report_path,
        "java_jar_path": str(java_jar_path),
        "save_result_path": save_result_path
    }

def run_static_tracker(
    tracker_cfg: dict,
    config_yaml: Path,
    python_executable: str,
    java_home: str = "",
    verbose: bool = False
) -> bool:
    config_yaml.parent.mkdir(parents=True, exist_ok=True)
    with open(config_yaml, "w") as f:
        yaml.dump(tracker_cfg, f, default_flow_style=False)
    
    launcher_script = _STATIC_TRACKER_DIR / "MatchingLauncher_StaticTracker.py"
    cmd = shlex.split(python_executable) + [str(launcher_script), str(config_yaml)]
    
    env = os.environ.copy()
    if java_home:
        env["JAVA_HOME"] = java_home

    res = subprocess.run(cmd, env=env, capture_output=True, text=True)
    
    log_dir = Path(tracker_cfg["save_result_path"]).parent
    log_dir.mkdir(parents=True, exist_ok=True)
    with open(log_dir / f"tracker_stdout.log", "w") as f:
        f.write(res.stdout)
    with open(log_dir / f"tracker_stderr.log", "w") as f:
        f.write(res.stderr)
        
    if res.returncode != 0:
        print(f"[StaticTracker] Warning: exit code {res.returncode}")
    if "IndexOutOfBoundsException" in res.stderr:
        print("[StaticTracker] Note: RefactoringMiner crashed due to AST error. This is a known issue for some files.")
        return True
    
    return res.returncode == 0

def collect_tracker_results(tracker_result_dir: str) -> dict:
    d = Path(tracker_result_dir)
    return {
        "introduced": (
            list(d.rglob("introduced_smells*.csv")) + 
            list(d.rglob("*introduced*.csv")) +
            list(d.rglob("*new_warnings*.csv"))
        ),
        "removed": (
            list(d.rglob("removed_smells*.csv")) + 
            list(d.rglob("*removed*.csv")) +
            list(d.rglob("*gone_warnings*.csv"))
        ),
    }

def count_smells_in_csv(csv_path: Path) -> int:
    if not csv_path.exists():
        return 0
    with open(csv_path, "r", encoding="utf-8") as f:
        lines = sum(1 for _ in f)
        return max(0, lines - 1)

def parse_tracker_csv(csv_path: Path) -> list[dict]:
    if not csv_path.exists():
        return []
    smells = []
    try:
        with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                smells.append(dict(row))
    except Exception as e:
        print(f"[Manager] Error parsing {csv_path}: {e}")
    return smells

def write_manifest(run_dir: Path, manifest: dict) -> None:
    with open(run_dir / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)