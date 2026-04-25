import pandas as pd
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

RESULT_FOLDERS = [
    REPO_ROOT / "data" / "judge_results" / "rawshan",
    REPO_ROOT / "data" / "judge_results" / "auto",
]

OUTPUT_DIR = REPO_ROOT / "data" / "analysis"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

master_rows = []

for folder in RESULT_FOLDERS:
    if not folder.exists():
        continue

    for csv_file in folder.rglob("*.csv"):
        try:
            df = pd.read_csv(csv_file)

            df["source_file"] = csv_file.name
            df["source_path"] = str(csv_file.relative_to(REPO_ROOT))
            df["result_group"] = folder.name

            filename = csv_file.stem.replace("_results", "")
            df["dataset_name"] = filename

            parts = filename.replace("plausible_patches_", "").split("_")
            df["project"] = parts[0] if len(parts) > 0 else "unknown"
            df["bug_number"] = parts[1] if len(parts) > 1 else "unknown"

            master_rows.append(df)

        except Exception as e:
            print(f"[SKIP] Could not read {csv_file}: {e}")

if not master_rows:
    raise RuntimeError("No CSV files found in data/judge_results/rawshan or data/judge_results/auto")

master_df = pd.concat(master_rows, ignore_index=True)

if "passes_tests" in master_df.columns and "ground_truth_test" not in master_df.columns:
    master_df["ground_truth_test"] = master_df["passes_tests"]

if "ground_truth_test" in master_df.columns and "passes_tests" in master_df.columns:
    master_df["agreement"] = (
        master_df["passes_tests"].astype(str).str.upper()
        == master_df["ground_truth_test"].astype(str).str.upper()
    )

if "passes_tests" in master_df.columns and "ground_truth_test" in master_df.columns:
    pred = master_df["passes_tests"].astype(str).str.upper()
    truth = master_df["ground_truth_test"].astype(str).str.upper()

    master_df["false_positive"] = (pred == "TRUE") & (truth == "FALSE")
    master_df["false_negative"] = (pred == "FALSE") & (truth == "TRUE")
    master_df["unknown"] = pred.str.contains("UNKNOWN", na=False)

excel_path = OUTPUT_DIR / "master_judge_results.xlsx"
csv_path = OUTPUT_DIR / "master_judge_results.csv"

master_df.to_csv(csv_path, index=False)

with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
    master_df.to_excel(writer, sheet_name="Master Results", index=False)

    if "project" in master_df.columns:
        summary = master_df.groupby("project").agg(
            total_rows=("project", "count"),
            unknown_count=("unknown", "sum") if "unknown" in master_df.columns else ("project", "count"),
            false_positive_count=("false_positive", "sum") if "false_positive" in master_df.columns else ("project", "count"),
            false_negative_count=("false_negative", "sum") if "false_negative" in master_df.columns else ("project", "count"),
        ).reset_index()

        summary.to_excel(writer, sheet_name="Project Summary", index=False)

print(f"[OK] Wrote master CSV: {csv_path}")
print(f"[OK] Wrote master Excel: {excel_path}")
print(f"[OK] Total rows combined: {len(master_df)}")