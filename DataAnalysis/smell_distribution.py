from collections import defaultdict
from typing import Dict, Any, List

def analyze_heatmap(all_smells: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculates the distribution of each specific smell introduced and removed
    across the entire history run.
    """
    introduced_counts = defaultdict(int)
    removed_counts = defaultdict(int)
    
    total_introduced = 0
    total_removed = 0

    for smell in all_smells.get("introduced", []):
        name = smell.get("Bug") or smell.get("smell_name") or smell.get("SmellName") or smell.get("smell") or smell.get("class name") or "Unknown"
        introduced_counts[name] += 1
        total_introduced += 1
        
    for smell in all_smells.get("removed", []):
        name = smell.get("Bug") or smell.get("smell_name") or smell.get("SmellName") or smell.get("smell") or smell.get("class name") or "Unknown"
        removed_counts[name] += 1
        total_removed += 1

    def to_percentages(counts, total):
        if total == 0:
            return {}
        return {k: round((v / total) * 100, 2) for k, v in counts.items()}

    return {
        "introduced_percentages": to_percentages(introduced_counts, total_introduced),
        "removed_percentages": to_percentages(removed_counts, total_removed),
        "introduced_raw": dict(introduced_counts),
        "removed_raw": dict(removed_counts)
    }

def analyze_smell_distribution(commit_log: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregates all smells introduced and removed across the entire commit log.
    """
    all_smells = {
        "introduced": [],
        "removed": []
    }
    
    for c in commit_log:
        all_smells["introduced"].extend(c.get("introduced_smells", []))
        all_smells["removed"].extend(c.get("removed_smells", []))
        
    return analyze_heatmap(all_smells)
