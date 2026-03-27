from pathlib import Path
import csv
import subprocess
import sys

# ---- Adjust these if needed ----
PROJECTS = ["pandas"]   # later change to ["PySnooper", "keras"]
LIMIT_PATCHES_PER_CONFIG = None  # e.g. 5 for testing, or None for all
RUN_JUDGE = True

CONFIG_MAP = {
    "patch_v0": "v0_gpt",
    "patch_v0_llama": "v0_llama",
    "patch_v_all_gpt": "vall_gpt",
    "patch_v_all_llama": "vall_llama",
}

def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")

def build_csv_for_config(source_dir: Path, out_csv: Path, project: str, bug_id: str, config_label: str):
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    md_files = sorted(source_dir.glob("*.md"))
    if LIMIT_PATCHES_PER_CONFIG is not None:
        md_files = md_files[:LIMIT_PATCHES_PER_CONFIG]

    rows = []
    for i, f in enumerate(md_files):
        patch_text = read_text(f).strip()
        row_id = f"{project.lower()}-{bug_id}-{config_label}-{i}"
        rows.append([
            row_id,         # bug_id
            "UNKNOWN",      # bug_description
            "UNKNOWN",      # buggy_code
            patch_text,     # patch_diff
            ""              # tests_pass (empty if unknown)
        ])

    with out_csv.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.writer(fp)
        writer.writerow(["bug_id", "bug_description", "buggy_code", "patch_diff", "tests_pass"])
        writer.writerows(rows)

    print(f"[OK] Wrote input CSV: {out_csv} ({len(rows)} patches)")

from run_patch_judge import run_judge as run_judge_internal

def run_judge(input_csv, output_csv, repo_root):
    print(f"[RUN] judge on {input_csv}")
    run_judge_internal(str(input_csv), str(output_csv))

def main():
    repo_root = Path(__file__).resolve().parents[1]
    research_root = repo_root.parent
    source_repo = research_root / "llm-apr-knowledge-injection"

    if not source_repo.exists():
        raise FileNotFoundError(f"Could not find source repo at: {source_repo}")

    patch_csv_dir = repo_root / "data" / "patches" / "auto"
    result_dir = repo_root / "data" / "judge_results" / "auto"

    for project in PROJECTS:
        project_dir = source_repo / "bug-data" / project
        if not project_dir.exists():
            print(f"[WARN] Missing project folder: {project_dir}")
            continue

        bug_dirs = sorted([p for p in project_dir.iterdir() if p.is_dir()])

        for bug_dir in bug_dirs:
            bug_id = bug_dir.name

            for source_folder, config_label in CONFIG_MAP.items():
                cfg_dir = bug_dir / source_folder
                if not cfg_dir.exists():
                    print(f"[SKIP] {project}/{bug_id}/{source_folder} does not exist")
                    continue

                md_files = sorted(cfg_dir.glob("*.md"))
                if not md_files:
                    print(f"[SKIP] {project}/{bug_id}/{source_folder} has no .md files")
                    continue

                input_csv = patch_csv_dir / f"{project.lower()}_{bug_id}_{config_label}.csv"
                output_csv = result_dir / f"{project.lower()}_{bug_id}_{config_label}_results.csv"

                if output_csv.exists():
                    print(f"[SKIP] Already completed: {output_csv.name}")
                    continue

                build_csv_for_config(cfg_dir, input_csv, project, bug_id, config_label)

                if RUN_JUDGE:
                    run_judge(input_csv, output_csv, repo_root)

    print("[DONE] Finished processing all selected projects/bugs/configs.")

if __name__ == "__main__":
    main()