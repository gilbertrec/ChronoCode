import os
import sys
import json
import csv
import subprocess
import uuid
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel
import yaml

app = FastAPI(title="ChronoCode API")
active_jobs = {}

@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request, exc):
    if exc.status_code == 404 and not request.url.path.startswith("/api/"):
        dist_dir = PROJECT_ROOT / "UI" / "web" / "dist"
        index_file = dist_dir / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
    # Fallback to the default exception handler if needed, or raise
    from fastapi.exception_handlers import http_exception_handler
    return await http_exception_handler(request, exc)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DATASTORE_DIR = PROJECT_ROOT / "DataStore"
MAIN_PY = PROJECT_ROOT / "main.py"
SETTINGS_YAML = PROJECT_ROOT / "settings.yaml"

class SettingsModel(BaseModel):
    dpy_path: Optional[str] = None
    python: Optional[str] = None
    java_home: Optional[str] = None

@app.get("/api/settings")
def get_settings() -> Dict[str, Any]:
    if not SETTINGS_YAML.exists():
        return {}
    try:
        with open(SETTINGS_YAML, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/settings")
def update_settings(settings: SettingsModel):
    data = {}
    if SETTINGS_YAML.exists():
        try:
            with open(SETTINGS_YAML, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception:
            pass
            
    if settings.dpy_path is not None:
        data["dpy-path"] = settings.dpy_path
    if settings.python is not None:
        data["python"] = settings.python
    if settings.java_home is not None:
        data["java-home"] = settings.java_home
        
    try:
        with open(SETTINGS_YAML, "w", encoding="utf-8") as f:
            yaml.dump(data, f)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/directories")
def list_directories(path: Optional[str] = None) -> List[Dict[str, str]]:
    target = Path(path).resolve() if path else Path.home()
    if not target.exists() or not target.is_dir():
        # Fallback to home if invalid
        target = Path.home()
        
    dirs = []
    # Add parent directory if possible
    if target.parent != target:
        dirs.append({"name": "..", "path": str(target.parent)})
        
    try:
        for item in target.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                dirs.append({"name": item.name, "path": str(item)})
    except PermissionError:
        pass
        
    dirs.sort(key=lambda x: x["name"].lower() if x["name"] != ".." else "")
    return dirs

class AnalysisRequest(BaseModel):
    config_file: Optional[str] = None
    project_path: Optional[str] = None
    dpy_path: Optional[str] = None
    command_type: Optional[str] = None
    commits: Optional[int] = None
    since: Optional[str] = None
    skip_tracker: bool = False
    workers: Optional[int] = None

def run_analysis_task(req: AnalysisRequest, job_id: str):
    venv_python = os.path.join(PROJECT_ROOT, ".venv_x86", "bin", "python")
    if os.path.exists(venv_python) and sys.platform == "darwin":
        cmd = [
            "arch",
            "-x86_64",
            venv_python,
            str(MAIN_PY),
        ]
    else:
        cmd = [
            sys.executable,
            str(MAIN_PY),
        ]
    
    if not req.config_file and req.command_type:
        cmd.append(req.command_type)

    if req.config_file:
        cmd.extend(["-c", req.config_file])
    elif SETTINGS_YAML.exists():
        cmd.extend(["-c", str(SETTINGS_YAML)])
        
    if not req.config_file:
        if req.project_path:
            cmd.extend(["--project-path", req.project_path])
        if req.dpy_path:
            cmd.extend(["--dpy-path", req.dpy_path])
        if req.command_type == "history":
            if req.commits:
                cmd.extend(["--commits", str(req.commits)])
            if req.since:
                cmd.extend(["--since", req.since])
            if req.skip_tracker:
                cmd.append("--skip-tracker")
            if req.workers:
                cmd.extend(["--workers", str(req.workers)])
    
    print(f"Starting analysis: {' '.join(cmd)}")
    
    process = subprocess.Popen(cmd, cwd=str(PROJECT_ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    
    project_name = Path(req.project_path).name if req.project_path else "Project"
    if req.config_file:
        project_name = "Config Run"
        
    active_jobs[job_id] = {
        "id": job_id,
        "project": project_name,
        "type": req.command_type or "unknown",
        "progress_current": 0,
        "progress_total": req.commits or 0,
        "status": "running",
        "process": process
    }
    
    progress_re = re.compile(r"\[History\]\s*\[\s*(\d+)/\s*(\d+)\]")
    
    try:
        for line in process.stdout:
            print(line, end="")
            m = progress_re.search(line)
            if m:
                active_jobs[job_id]["progress_current"] = int(m.group(1))
                active_jobs[job_id]["progress_total"] = int(m.group(2))
    except Exception as e:
        print(f"Error reading process output: {e}")
        
    process.wait()
    
    if job_id in active_jobs:
        active_jobs[job_id]["status"] = "completed" if process.returncode == 0 else "failed"
        del active_jobs[job_id]
    
    print(f"Analysis {job_id} finished with code {process.returncode}.")

@app.get("/api/runs")
def list_runs() -> List[Dict[str, Any]]:
    runs = []
    if not DATASTORE_DIR.exists():
        return runs
    
    for run_dir in DATASTORE_DIR.iterdir():
        if run_dir.is_dir():
            manifest_path = run_dir / "manifest.json"
            if manifest_path.exists():
                try:
                    with open(manifest_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        runs.append(data)
                except Exception as e:
                    print(f"Failed to read {manifest_path}: {e}")
    
    runs.sort(key=lambda x: x.get("run_id", ""), reverse=True)
    return runs

@app.get("/api/runs/{run_id}")
def get_run(run_id: str) -> Dict[str, Any]:
    run_dir = DATASTORE_DIR / run_id
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.exists():
        raise HTTPException(status_code=404, detail="Run not found")
    
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)

def parse_csv_smells(csv_path: Path) -> List[Dict[str, Any]]:
    smells = []
    if not csv_path.exists():
        return smells
    try:
        with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                smells.append(row)
    except Exception:
        pass
    return smells

@app.get("/api/runs/{run_id}/smells")
def get_run_smells(run_id: str) -> Dict[str, Any]:
    run_dir = DATASTORE_DIR / run_id
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.exists():
        raise HTTPException(status_code=404, detail="Run not found")
    
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    child_commit = manifest.get("child_commit", "")
    tracker_dir = run_dir / "tracker_results" / child_commit[:12]
    
    introduced = []
    removed = []
    
    if tracker_dir.exists():
        for csv_path in tracker_dir.rglob("introduced_smells*.csv"):
            introduced.extend(parse_csv_smells(csv_path))
        for csv_path in tracker_dir.rglob("*introduced*.csv"):
            introduced.extend(parse_csv_smells(csv_path))
        for csv_path in tracker_dir.rglob("*new_warnings*.csv"):
            introduced.extend(parse_csv_smells(csv_path))
            
        for csv_path in tracker_dir.rglob("removed_smells*.csv"):
            removed.extend(parse_csv_smells(csv_path))
        for csv_path in tracker_dir.rglob("*removed*.csv"):
            removed.extend(parse_csv_smells(csv_path))
        for csv_path in tracker_dir.rglob("*gone_warnings*.csv"):
            removed.extend(parse_csv_smells(csv_path))
            
    return {
        "introduced": introduced,
        "removed": removed
    }

@app.get("/api/runs/{run_id}/history")
def get_run_history(run_id: str) -> List[Dict[str, Any]]:
    run_dir = DATASTORE_DIR / run_id
    commit_log_path = run_dir / "commit_log.json"
    if not commit_log_path.exists():
        raise HTTPException(status_code=404, detail="History log not found")
    
    with open(commit_log_path, "r", encoding="utf-8") as f:
        return json.load(f)

@app.get("/api/runs/{run_id}/history/smells")
def get_history_commit_smells(run_id: str, commit_sha: str) -> Dict[str, Any]:
    run_dir = DATASTORE_DIR / run_id
    short_sha = commit_sha[:12]
    tracker_dir = run_dir / "tracker_results" / short_sha
    
    introduced = []
    removed = []
    
    if tracker_dir.exists():
        for csv_path in tracker_dir.rglob("introduced_smells*.csv"):
            introduced.extend(parse_csv_smells(csv_path))
        for csv_path in tracker_dir.rglob("*introduced*.csv"):
            introduced.extend(parse_csv_smells(csv_path))
        for csv_path in tracker_dir.rglob("*new_warnings*.csv"):
            introduced.extend(parse_csv_smells(csv_path))
            
        for csv_path in tracker_dir.rglob("removed_smells*.csv"):
            removed.extend(parse_csv_smells(csv_path))
        for csv_path in tracker_dir.rglob("*removed*.csv"):
            removed.extend(parse_csv_smells(csv_path))
        for csv_path in tracker_dir.rglob("*gone_warnings*.csv"):
            removed.extend(parse_csv_smells(csv_path))
            
    return {
        "introduced": introduced,
        "removed": removed
    }

@app.get("/api/runs/{run_id}/diff")
def get_commit_diff(run_id: str, commit_sha: str, file_path: str) -> Dict[str, Any]:
    run_dir = DATASTORE_DIR / run_id
    cloned_repo = run_dir / "cloned_repo"
    
    if not cloned_repo.exists():
        raise HTTPException(status_code=404, detail="Cloned repo not found for this run")
        
    # Extract relative path if it's an absolute staging path
    rel_path = file_path
    if "/after/" in file_path:
        rel_path = file_path.split("/after/")[-1]
    elif "/before/" in file_path:
        rel_path = file_path.split("/before/")[-1]
        
    cmd = ["git", "show", "-U20", commit_sha, "--", rel_path]
    try:
        res = subprocess.run(cmd, cwd=str(cloned_repo), capture_output=True, text=True, check=True)
        return {"diff": res.stdout}
    except subprocess.CalledProcessError as e:
        return {"diff": f"Failed to get diff for {rel_path}:\n{e.stderr}"}

from DataAnalysis import analyze_heatmap, analyze_lifecycle, analyze_by_period, analyze_by_category

@app.get("/api/runs/{run_id}/advanced_analysis")
def get_advanced_analysis(run_id: str, author_filter: str = "all") -> Dict[str, Any]:
    run_dir = DATASTORE_DIR / run_id
    commit_log_path = run_dir / "commit_log.json"
    if not commit_log_path.exists():
        raise HTTPException(status_code=404, detail="History log not found")
    
    with open(commit_log_path, "r", encoding="utf-8") as f:
        full_commit_log = json.load(f)
        
    if author_filter == "ai":
        commit_log = [c for c in full_commit_log if c.get("tag") == "AI"]
    elif author_filter == "human":
        commit_log = [c for c in full_commit_log if c.get("tag") != "AI"]
    else:
        commit_log = full_commit_log
        
    # Aggregate ALL smells from ALL commits to generate heatmap
    all_smells = {"introduced": [], "removed": []}
    for commit in commit_log:
        sha = commit.get("sha")
        if sha:
            smells = get_history_commit_smells(run_id, sha)
            all_smells["introduced"].extend(smells.get("introduced", []))
            all_smells["removed"].extend(smells.get("removed", []))
            
    heatmap_data = analyze_heatmap(all_smells)
    lifecycle_data = analyze_lifecycle(commit_log)
    period_data = analyze_by_period(commit_log)
    category_data = analyze_by_category(commit_log)
    
    return {
        "heatmap": heatmap_data,
        "temporal": {
            "lifecycle": lifecycle_data,
            **period_data
        },
        "categories": category_data,
        "commit_log": full_commit_log,
        "all_smells": all_smells
    }

@app.post("/api/analyze")
def trigger_analysis(req: AnalysisRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    background_tasks.add_task(run_analysis_task, req, job_id)
    return {"status": "started", "job_id": job_id, "message": "Analysis started in background"}

@app.get("/api/jobs")
def get_jobs() -> List[Dict[str, Any]]:
    return [
        {
            "id": j["id"],
            "project": j["project"],
            "type": j["type"],
            "progress_current": j["progress_current"],
            "progress_total": j["progress_total"],
            "status": j["status"]
        }
        for j in active_jobs.values()
    ]

@app.post("/api/jobs/{job_id}/stop")
def stop_job(job_id: str):
    if job_id in active_jobs:
        job = active_jobs[job_id]
        if job["process"]:
            try:
                job["process"].terminate()
            except Exception:
                pass
        del active_jobs[job_id]
        return {"status": "stopped"}
    raise HTTPException(status_code=404, detail="Job not found")

dist_dir = PROJECT_ROOT / "UI" / "web" / "dist"
if dist_dir.exists():
    app.mount("/", StaticFiles(directory=str(dist_dir), html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5172)
