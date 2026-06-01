import csv
import os
import subprocess
import yaml
from concurrent.futures import ThreadPoolExecutor
from Utils import getParentCommit

# Set this to the number of parallel repositories/commits you want to analyze simultaneously
# Be careful: each worker spawns its own JVM, which consumes memory (~1-2GB per worker)
MAX_WORKERS = 4 

def run_tracker(task_config, temp_yaml_path):
    # 1. Write a temporary dedicated YAML config for this specific run
    with open(temp_yaml_path, 'w') as f:
        yaml.dump(task_config, f, default_flow_style=False)
    
    # 2. Define the exact bash execution command to run the tool cleanly (including x86 env)
    cmd = [
        "arch", "-x86_64", 
        "env", 'JAVA_HOME=/Users/gilberto/Library/Java/JavaVirtualMachines/openjdk-19.0.1/Contents/Home',
        "/Users/gilberto/Documents/AI-DEV-Analysis/test_mining_micro/x86_venv/bin/python",
        "MatchingLauncher_StaticTracker.py", 
        temp_yaml_path
    ]
    
    print(f"[*] Starting analysis for Child Commit: {task_config['child_commit']}...")
    
    # 3. Spawn the subprocess
    process = subprocess.run(cmd, capture_output=True, text=True)
    
    if process.returncode != 0:
        print(f"[!] Error analyzing {task_config['child_commit']}:\n{process.stderr}\n{process.stdout}")
    else:
        print(f"[+] Successfully completed matching for {task_config['child_commit']}!")
    
    # 4. Keep the temporary yaml file instead of cleaning it up
    # so we can trace configurations for debugging.
    # if os.path.exists(temp_yaml_path):
    #     os.remove(temp_yaml_path)
        
    return process.returncode

def launch_batch(batch_csv_path, root_repo_folder):
    tasks = []
    
    config_dir = "config_file"
    os.makedirs(config_dir, exist_ok=True)
    
    # Read the batch configuration CSV
    if not os.path.exists(batch_csv_path):
        print(f"Could not find batch config file: {batch_csv_path}")
        return
        
    with open(batch_csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            raw_loc_path = row.get('loc_repo_path', '')
            # Given a loc_repo_path like 'Copilot/hacs$integration' map it correctly onto the root_repo_folder
            loc_repo_path = os.path.join(root_repo_folder, raw_loc_path)
            child_commit = row.get('child_commit')
            
            # If parent_commit is empty or missing in CSV, dynamically query it through Git
            parent_commit = row.get('parent_commit')
            if not parent_commit:
                parent_commit = getParentCommit(loc_repo_path, child_commit)
                
            config = {
                'loc_repo_path': loc_repo_path,
                'remote_repo_path': row.get('remote_repo_path'),
                'save_result_path': row.get('save_result_path', '../test_mining_micro/results'),
                'parent_commit': parent_commit,
                'parent_report_path': row.get('parent_report_path'),
                'child_commit': child_commit,
                'child_report_path': row.get('child_report_path'),
                'static_tool': row.get('static_tool', 'DesignitePy'),
                'java_jar_path': './refactoringJava/target/refactoringJava-1.0-SNAPSHOT-jar-with-dependencies.jar'
            }
            temp_yaml = os.path.join(config_dir, f"temp_config_{row.get('child_commit', i)}.yaml")
            tasks.append((config, temp_yaml))

    print(f"Loaded {len(tasks)} pairing tasks. Launching in parallel with {MAX_WORKERS} workers...")

    # Execute them in parallel using a ThreadPool spawning subprocesses
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for config, temp_yaml in tasks:
            executor.submit(run_tracker, config, temp_yaml)

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python ParallelLauncher.py <path_to_batch_csv> <root_repo_folder>")
        sys.exit(1)
        
    batch_csv = sys.argv[1]
    root_folder = sys.argv[2]
    launch_batch(batch_csv, root_folder)
