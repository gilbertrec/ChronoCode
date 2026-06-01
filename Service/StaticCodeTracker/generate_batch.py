import pandas as pd
import csv
import os
import sys

def parse_and_generate(after_csv_path, output_batch_csv):
    if not os.path.exists(after_csv_path):
        print(f"File not found: {after_csv_path}")
        sys.exit(1)

    print(f"Reading {after_csv_path}...")
    df_after = pd.read_csv(after_csv_path)

    before_csv_path = after_csv_path.replace("after_smells", "before_smells").replace("test_dpyreport_after", "test_dpyreport_before")
    if os.path.exists(before_csv_path):
        df_before = pd.read_csv(before_csv_path)
    else:
        df_before = pd.DataFrame()

    if 'CommitSha' not in df_after.columns or 'Repo' not in df_after.columns:
        print("CSV does not contain 'CommitSha' or 'Repo' columns.")
        sys.exit(1)

    unique_combinations = df_after[['Author', 'Repo', 'CommitSha']].drop_duplicates()
    
    # Setting up localized copies directory
    split_dir = "split_reports"
    os.makedirs(split_dir, exist_ok=True)
    
    with open(output_batch_csv, 'w', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['loc_repo_path','remote_repo_path','save_result_path','parent_commit','parent_report_path','child_commit','child_report_path','static_tool'])
        
        for _, row in unique_combinations.iterrows():
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
                
            loc_repo_path = f"{repo}_repo"
            remote_repo_path = f"https://github.com/{author}/{repo}"
            save_result_path = "../test_mining_micro/results"
            
            # Leave empty so ParallelLauncher computes it using Utils.getParentCommit()
            parent_commit = ""
            
            static_tool = 'DesignitePy'
            
            writer.writerow([loc_repo_path, remote_repo_path, save_result_path, parent_commit, parent_report_path, child_commit, child_report_path, static_tool])
            
    print(f"[+] Successfully generated {len(unique_combinations)} tasks in {output_batch_csv}")
    print(f"[+] Individual CSV components chunked into: '{split_dir}/'")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python generate_batch.py <path_to_after_smells.csv> <output_batch_csv>")
        sys.exit(1)
        
    parse_and_generate(sys.argv[1], sys.argv[2])
