from collections import defaultdict
from typing import Dict, Any, List
from datetime import datetime

def analyze_lifecycle(commit_log: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Sorts commits by date and chunks them into 0-10%, 10-20%, 20-50%, 50-100% 
    of the project timeline, aggregating smells introduced/removed.
    """
    valid_commits = []
    for c in commit_log:
        try:
            dt = datetime.fromisoformat(c.get("date", "").replace("Z", "+00:00"))
            valid_commits.append((dt, c))
        except Exception:
            continue
            
    if not valid_commits:
        return {}

    valid_commits.sort(key=lambda x: x[0])
    total_commits = len(valid_commits)
    
    chunks = {
        "0-10%": {"introduced": 0, "removed": 0},
        "10-20%": {"introduced": 0, "removed": 0},
        "20-50%": {"introduced": 0, "removed": 0},
        "50-100%": {"introduced": 0, "removed": 0},
    }
    
    for i, (_, c) in enumerate(valid_commits):
        pct = (i / total_commits) * 100
        intro = c.get("introduced", 0)
        rem = c.get("removed", 0)
        
        if pct <= 10:
            chunks["0-10%"]["introduced"] += intro
            chunks["0-10%"]["removed"] += rem
        elif pct <= 20:
            chunks["10-20%"]["introduced"] += intro
            chunks["10-20%"]["removed"] += rem
        elif pct <= 50:
            chunks["20-50%"]["introduced"] += intro
            chunks["20-50%"]["removed"] += rem
        else:
            chunks["50-100%"]["introduced"] += intro
            chunks["50-100%"]["removed"] += rem
            
    return chunks

def analyze_by_period(commit_log: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregates smells introduced/removed grouped by day, week, and month.
    """
    by_day = defaultdict(lambda: {"introduced": 0, "removed": 0})
    by_week = defaultdict(lambda: {"introduced": 0, "removed": 0})
    by_month = defaultdict(lambda: {"introduced": 0, "removed": 0})
    
    for c in commit_log:
        try:
            dt = datetime.fromisoformat(c.get("date", "").replace("Z", "+00:00"))
            day = dt.strftime("%Y-%m-%d")
            week = dt.strftime("%Y-W%W")
            month = dt.strftime("%Y-%m")
            
            intro = c.get("introduced", 0)
            rem = c.get("removed", 0)
            
            by_day[day]["introduced"] += intro
            by_day[day]["removed"] += rem
            by_week[week]["introduced"] += intro
            by_week[week]["removed"] += rem
            by_month[month]["introduced"] += intro
            by_month[month]["removed"] += rem
        except Exception:
            continue
            
    return {
        "by_day": dict(sorted(by_day.items())),
        "by_week": dict(sorted(by_week.items())),
        "by_month": dict(sorted(by_month.items())),
    }
