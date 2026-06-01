import json
import sys
from DataAnalysis.commit_classification import analyze_by_category

# Create mock data
mock_log = [
    {
        "sha": "sha1", "tag": "Human", "date": "2023-10-01", "subject": "feat: added new login",
        "introduced": 2, "removed": 0,
        "introduced_smells": [{"Bug": "Long Method", "source path": "file1.py"}, {"Bug": "Magic number", "source path": "file1.py"}],
        "removed_smells": []
    },
    {
        "sha": "sha2", "tag": "AI", "date": "2023-10-02", "subject": "fix: bug in login",
        "introduced": 3, "removed": 1,
        "introduced_smells": [{"Bug": "Complex Method", "source path": "file2.py"}, {"Bug": "Long Method", "source path": "file2.py"}, {"Bug": "Magic number", "source path": "file2.py"}],
        "removed_smells": [{"Bug": "Magic number"}]
    }
]

print("Commit Classification:", analyze_by_category(mock_log))
