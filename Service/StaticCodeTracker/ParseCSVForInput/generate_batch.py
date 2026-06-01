import pandas as pd
import csv
import os
import sys

def parse_and_generate(after_csv_path, output_batch_csv, before_csv_path=None):
    # Convert input path to absolute immediately so the outputs are context-independent
    after_csv_path = os.path.abspath(after_csv_path)
    output_batch_csv = os.path.abspath(output_batch_csv)
    if before_csv_path:
        before_csv_path = os.path.abspath(before_csv_path)
    
    if not os.path.exists(after_csv_path):
        print(f"File not found: {after_csv_path}")
        sys.exit(1)

    print(f"Reading {after_csv_path}...")
    df_after = pd.read_csv(after_csv_path)

    if before_csv_path and os.path.exists(before_csv_path):
        print(f"Reading {before_csv_path}...")
        df_before = pd.read_csv(before_csv_path)
    else:
        print(f"Warning: before_csv_path not provided or not found, continuing without parent smells.")
        df_before = pd.DataFrame()

    if 'Agent' not in df_after.columns or 'CommitSha' not in df_after.columns or 'Repo' not in df_after.columns:
        print("CSV does not contain 'Agent', 'CommitSha' or 'Repo' columns.")
        sys.exit(1)

    unique_combinations = df_after[['Agent', 'Author', 'Repo', 'CommitSha']].drop_duplicates()
    
    # Setting up localized copies directory inside the current script's directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    split_dir = os.path.join(script_dir, "split_reports")
    os.makedirs(split_dir, exist_ok=True)
    
    with open(output_batch_csv, 'w', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['loc_repo_path','remote_repo_path','save_result_path','parent_commit','parent_report_path','child_commit','child_report_path','static_tool'])
        
        for _, row in unique_combinations.iterrows():
            agent = row['Agent']
            author = row['Author']
            repo = row['Repo']
            child_commit = row['CommitSha']
            
            # Split out individual task files
            df_child_after = df_after[(df_after['Repo'] == repo) & (df_after['CommitSha'] == child_commit)]
            child_report_path = os.path.join(split_dir, f"{child_commit}_after_smells.csv")
            df_child_after.to_csv(child_report_path, index=False)
            
            if not df_before.empty:
                df_child_before = df_before[(df_before['Repo'] == repo) & (df_before['CommitSha'] == child_commit)]
                parent_report_path = os.path.join(split_dir, f"{child_commit}_before_smells.csv")
                df_child_before.to_csv(parent_report_path, index=False)
            else:
                parent_report_path = ""
                
            loc_repo_path = f"{agent}/{author}${repo}"
            remote_repo_path = f"https://github.com/{author}/{repo}"
            
            # Use absolute path for saving results back to the standard place
            save_result_path = os.path.abspath(os.path.join(script_dir, "../../test_mining_micro/results", agent, f"{author}${repo}", child_commit))
            
            # Make sure we actually have the tree structure if necessary, though os.makedirs in MatchingLauncher handles it. No harm in forcing it.
            os.makedirs(save_result_path, exist_ok=True)
            
            parent_commit = ""
            static_tool = 'DesignitePy'
            
            writer.writerow([loc_repo_path, remote_repo_path, save_result_path, parent_commit, parent_report_path, child_commit, child_report_path, static_tool])
            
    print(f"[+] Successfully generated {len(unique_combinations)} tasks in {output_batch_csv}")
    print(f"[+] Individual CSV components chunked into: '{split_dir}/'")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python generate_batch.py <path_to_after_smells.csv> <output_batch_csv> [path_to_before_smells.csv]")
        sys.exit(1)
        
    before_csv_path = sys.argv[3] if len(sys.argv) > 3 else None
    parse_and_generate(sys.argv[1], sys.argv[2], before_csv_path)
