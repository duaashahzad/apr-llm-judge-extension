from pathlib import Path
import csv

# CHANGE THIS to where you cloned llm-apr-knowledge-injection
SOAR_REPO = Path(r"C:\Users\smazi\OneDrive\Belmont 4th Year Work\Research\llm-apr-knowledge-injection")

OUT_CSV = Path(__file__).resolve().parents[1] / "data" / "patches" / "pysnooper_10.csv"

# folders to pull from
PATCH_DIRS = [
    SOAR_REPO / "bug-data" / "PySnooper" / "3" / "patch_v0",
    SOAR_REPO / "bug-data" / "PySnooper" / "3" / "patch_v0_llama",
]

def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")

def main():
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for d in PATCH_DIRS:
        if not d.exists():
            print(f"[WARN] Missing: {d}")
            continue
        md_files = sorted(d.glob("*.md"))[:5]  # take first 5 from each => 10 total
        for i, f in enumerate(md_files):
            patch_text = read_text(f).strip()
            source = "gpt" if "llama" not in d.name.lower() else "llama"
            bug_id = f"pysnooper-3-{source}-{i}"
            rows.append([bug_id, "UNKNOWN", "UNKNOWN", patch_text, ""])

    with OUT_CSV.open("w", newline="", encoding="utf-8") as fp:
        w = csv.writer(fp)
        w.writerow(["bug_id", "bug_description", "buggy_code", "patch_diff", "tests_pass"])
        w.writerows(rows)

    print(f"[OK] Wrote {len(rows)} rows to {OUT_CSV}")

if __name__ == "__main__":
    main()
