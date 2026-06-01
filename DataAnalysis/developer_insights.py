from collections import defaultdict
from typing import Dict, Any, List

def analyze_smell_velocity(commit_log: List[Dict[str, Any]], window_size: int = 5) -> List[Dict[str, Any]]:
    """
    Calculates a rolling average (velocity) of smells introduced and removed.
    Positive velocity means technical debt is increasing.
    """
    if not commit_log:
        return []
        
    # Sort from oldest to newest for chronological velocity
    sorted_commits = sorted(commit_log, key=lambda x: x.get("date", ""), reverse=False)
    
    velocity_data = []
    
    for i in range(len(sorted_commits)):
        window = sorted_commits[max(0, i - window_size + 1): i + 1]
        
        intro_sum = sum(c.get("introduced", 0) for c in window)
        rem_sum = sum(c.get("removed", 0) for c in window)
        
        velocity_data.append({
            "sha": sorted_commits[i]["sha"],
            "date": sorted_commits[i].get("date", ""),
            "introduced_rolling_avg": round(intro_sum / len(window), 2),
            "removed_rolling_avg": round(rem_sum / len(window), 2),
            "net_velocity": round((intro_sum - rem_sum) / len(window), 2)
        })
        
    return velocity_data

def get_smell_name(smell: dict) -> str:
    return smell.get("Bug") or smell.get("smell_name") or smell.get("SmellName") or smell.get("smell") or smell.get("class name") or "Unknown"

def analyze_file_hotspots(commit_log: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Identifies which files are accumulating the most new smells.
    """
    file_counts = defaultdict(int)
    
    for c in commit_log:
        for smell in c.get("introduced_smells", []):
            # 'source path' is usually provided by the tracker
            file_path = smell.get("source path") or smell.get("File") or smell.get("file")
            if file_path:
                # normalize path to filename
                filename = file_path.split("/")[-1]
                file_counts[filename] += 1
                
    return dict(sorted(file_counts.items(), key=lambda x: x[1], reverse=True))

def analyze_ai_vs_human_profiles(commit_log: List[Dict[str, Any]], top_n: int = 3) -> Dict[str, Dict[str, Any]]:
    """
    Identifies the top smell types introduced by AI vs Human.
    """
    ai_counts = defaultdict(int)
    human_counts = defaultdict(int)
    
    for c in commit_log:
        tag = c.get("tag", "Human")
        target_dict = ai_counts if tag == "AI" else human_counts
        
        for smell in c.get("introduced_smells", []):
            name = get_smell_name(smell)
            target_dict[name] += 1
            
    def get_top(counts):
        return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True)[:top_n])
        
    return {
        "AI": get_top(ai_counts),
        "Human": get_top(human_counts)
    }
