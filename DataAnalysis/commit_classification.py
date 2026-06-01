import re
from typing import Dict, Any, List

def classify_commit(subject: str) -> str:
    """
    Classifies a commit subject based on Conventional Commits conventions.
    Returns one of: 'feat', 'fix', 'refactor', 'docs', 'chore', 'test', 'other'
    """
    subject = subject.lower().strip()
    
    # Common conventional commit prefixes
    match = re.match(r'^(feat|fix|refactor|docs|chore|test|style|perf|build|ci)(\([^)]+\))?:', subject)
    if match:
        return match.group(1)
        
    # Heuristics if no convention is strictly followed
    if subject.startswith("add ") or subject.startswith("added ") or subject.startswith("new "):
        return "feat"
    if subject.startswith("fix ") or subject.startswith("fixed ") or "bug" in subject:
        return "fix"
    if subject.startswith("refactor ") or subject.startswith("refactored ") or "cleanup" in subject:
        return "refactor"
        
    return "other"

def analyze_by_category(commit_log: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregates smells introduced/removed grouped by commit category.
    """
    categories = {
        "feat": {"introduced": 0, "removed": 0, "top_introduced_smells": {}},
        "fix": {"introduced": 0, "removed": 0, "top_introduced_smells": {}},
        "refactor": {"introduced": 0, "removed": 0, "top_introduced_smells": {}},
        "docs": {"introduced": 0, "removed": 0, "top_introduced_smells": {}},
        "chore": {"introduced": 0, "removed": 0, "top_introduced_smells": {}},
        "test": {"introduced": 0, "removed": 0, "top_introduced_smells": {}},
        "other": {"introduced": 0, "removed": 0, "top_introduced_smells": {}},
    }
    
    for c in commit_log:
        cat = classify_commit(c.get("subject", ""))
        if cat not in categories:
            categories[cat] = {"introduced": 0, "removed": 0, "top_introduced_smells": {}}
            
        categories[cat]["introduced"] += c.get("introduced", 0)
        categories[cat]["removed"] += c.get("removed", 0)
        
        # Track specific smells introduced by this category
        for smell in c.get("introduced_smells", []):
            name = smell.get("Bug") or smell.get("smell_name") or smell.get("SmellName") or smell.get("smell") or smell.get("class name") or "Unknown"
            if name not in categories[cat]["top_introduced_smells"]:
                categories[cat]["top_introduced_smells"][name] = 0
            categories[cat]["top_introduced_smells"][name] += 1
            
    # Sort top introduced smells for each category
    for cat in categories:
        sorted_smells = dict(sorted(categories[cat]["top_introduced_smells"].items(), key=lambda x: x[1], reverse=True)[:5])
        categories[cat]["top_introduced_smells"] = sorted_smells
        
    return categories
