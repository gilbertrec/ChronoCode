import json
import sys
from DataAnalysis.developer_insights import analyze_smell_velocity, analyze_file_hotspots, analyze_ai_vs_human_profiles

# Create mock data
mock_log = [
    {
        "sha": "sha1", "tag": "Human", "date": "2023-10-01",
        "introduced": 2, "removed": 0,
        "introduced_smells": [{"Bug": "Long Method", "source path": "file1.py"}, {"Bug": "Magic number", "source path": "file1.py"}],
        "removed_smells": []
    },
    {
        "sha": "sha2", "tag": "AI", "date": "2023-10-02",
        "introduced": 3, "removed": 1,
        "introduced_smells": [{"Bug": "Complex Method", "source path": "file2.py"}, {"Bug": "Long Method", "source path": "file2.py"}, {"Bug": "Magic number", "source path": "file2.py"}],
        "removed_smells": [{"Bug": "Magic number"}]
    }
]

print("Velocity:", analyze_smell_velocity(mock_log, window_size=2))
print("Hotspots:", analyze_file_hotspots(mock_log))
print("Profiles:", analyze_ai_vs_human_profiles(mock_log))
