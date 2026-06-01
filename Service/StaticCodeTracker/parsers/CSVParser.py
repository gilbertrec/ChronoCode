import csv
import os
from SmellInstance import SmellInstance

def DesignitePyCSVReader(csv_path):
    """
    Reads a DesignitePy CSV report and converts each row into a BugInstance object 
    for StaticCodeTracker to process.
    """
    bug_instances = set()
    
    if not os.path.exists(csv_path):
        print(f"File not found: {csv_path}")
        return bug_instances

    with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            bug = SmellInstance()
            
            import re
            
            # 1. Path Mapping
            full_path = (row.get("File") or row.get("Path") or "").strip()
            # Note: StaticCodeTracker expects relative paths matching the git diff exactly
            # DesignitePy gives absolute paths like /home/.../00681379740a0f8cf4a4c08f954336ad143cb6c8/src/crewai/crew.py
            # We must strip up to and including the 40-char SHA commit subfolder
            match = re.search(r'/[0-9a-f]{40}/(.*)$', full_path)
            if match:
                full_path = match.group(1)
            bug.setSourcePath(full_path)
            
            # 2. Line Mapping
            line_str = str(row.get("Line") or row.get("line") or "-1").strip()
            if "-" in line_str:
                parts = line_str.split("-")
                bug.setStartLine(parts[0].strip())
                bug.setEndLine(parts[1].strip())
            else:
                bug.setStartLine(line_str)
                bug.setEndLine(line_str) # standard single line fallback
            
            # 3. Smell Type / Rule Mapping
            smell_type = (row.get("smell_type") or row.get("SmellType") or "Unknown").strip()
            smell_name = (row.get("smell_name") or row.get("SmellName") or "Unknown").strip()
            
            bug.setCategoryAbbrev(smell_type)
            bug.setSmellAbbv(smell_name)
            
            # Optional defaults
            bug.setClass("") 
            bug.setMethod("")
            bug.setField("")
            bug.setPriority("1")
            
            bug_instances.add(bug)
            
    return bug_instances
