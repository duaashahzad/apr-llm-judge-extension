import os
from pathlib import Path
from run_patch_judge import run_judge

# Root of your repo
repo_root = Path(__file__).resolve().parents[1]

# Where Rawshan CSVs are
input_root = repo_root / "data" / "patches" / "rawshan"

# Where results will go
output_root = repo_root / "data" / "judge_results" / "rawshan"
output_root.mkdir(parents=True, exist_ok=True)

# Loop through experiments
for exp_dir in sorted(input_root.iterdir()):
    if not exp_dir.is_dir():
        continue

    print(f"\n[EXP] {exp_dir.name}")

    for csv_file in exp_dir.glob("*.csv"):
        input_csv = csv_file

        output_csv = output_root / f"{csv_file.stem}_results.csv"

        # Skip if already done
        if output_csv.exists():
            print(f"[SKIP] {csv_file.name}")
            continue

        print(f"[RUN] {csv_file.name}")

        try:
            run_judge(
                input_csv_override=str(input_csv),
                output_csv_override=str(output_csv)
            )
        except Exception as e:
            print(f"[ERROR] {csv_file.name}: {e}")