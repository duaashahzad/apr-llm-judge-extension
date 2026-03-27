
import os
import time
import requests
import json
import re
import argparse
import pandas as pd
from pathlib import Path
from metrics import compute_agreement_metrics

def load_patches(csv_path: Path) -> pd.DataFrame:
    print(f"[DEBUG] Loading patches from: {csv_path}")
    print(f"[DEBUG] Exists? {csv_path.exists()}")
    df = pd.read_csv(csv_path)
    print(f"[DEBUG] Loaded rows: {len(df)}")
    print(f"[DEBUG] Columns: {list(df.columns)}")
    return df

def build_prompt(row: pd.Series) -> str:
    return f"""You must respond only in json.

BUG DESCRIPTION:
{row['bug_description']}

BUGGY CODE:
{row['buggy_code']}

PATCH:
{row['patch_diff']}

Return ONLY valid json in this schema:
{{
  "compiles": "YES/NO/UNKNOWN",
  "passes_tests": "YES/NO/UNKNOWN",
  "semantic_correctness": 1-5,
  "confidence": 1-5,
  "explanation": "1-2 sentence justification"
}}
"""

def call_llm_mock(prompt: str) -> str:
    # Always returns valid JSON so parsing should work
    return """
{
  "compiles": "YES",
  "passes_tests": "YES",
  "semantic_correctness": 5,
  "confidence": 4,
  "explanation": "Mock response for pipeline testing."
}
"""

def parse_output(response_text: str) -> dict:
    text = (response_text or "").strip()

    # Remove common Markdown code fences like ```json ... ```
    if text.startswith("```"):
        # Drop the first fence line (``` or ```json)
        text = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", text)
        # Drop the ending fence
        text = re.sub(r"\s*```$", "", text).strip()

    # Try direct JSON parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Fallback: extract first JSON object from text
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass

        return {
            "compiles": "UNKNOWN",
            "passes_tests": "UNKNOWN",
            "semantic_correctness": 0,
            "confidence": 0,
            "explanation": f"Invalid JSON output: {text[:200]}"
        }

def call_llm_deepseek(prompt: str) -> str:
    """
    Calls DeepSeek Chat Completions API and returns the assistant content (JSON string).
    Uses JSON mode to enforce valid JSON output.
    """
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is not set. In PowerShell: $env:DEEPSEEK_API_KEY='sk-...'")

    url = "https://api.deepseek.com/v1/chat/completions"

    # JSON mode requires the prompt mention "json"
    system_msg = (
        "You are a strict evaluator of code patches for automated program repair. "
        "Return ONLY valid json."
    )

    payload = {
    "model": "deepseek/deepseek-r1",
    "messages": [
        {
            "role": "system",
            "content": "You are a strict evaluator of program repair patches. Respond ONLY in valid JSON."
        },
        {
            "role": "user",
            "content": prompt
        }
    ],
    "temperature": 0,
    "max_tokens": 300
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    for attempt in range(1, 4):
        try:
            print("[DEBUG] Calling DeepSeek API")
            r = requests.post(url, headers=headers, json=payload, timeout=60)

            if r.status_code == 200:
                data = r.json()
                return data["choices"][0]["message"]["content"]

            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(2 * attempt)
                continue

            raise RuntimeError(f"DeepSeek API error {r.status_code}: {r.text}")

        except requests.RequestException as e:
            if attempt == 3:
                raise RuntimeError(f"DeepSeek request failed: {e}") from e
            time.sleep(2 * attempt)

    raise RuntimeError("DeepSeek API failed after retries.")

def call_llm_openrouter(prompt: str) -> str:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")

    url = "https://openrouter.ai/api/v1/chat/completions"

    payload = {
        "model": "deepseek/deepseek-r1",
        "messages": [
            {
                "role": "system",
                "content": "You are a strict evaluator of program repair patches. Respond ONLY in valid JSON."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0,
        "max_tokens": 300
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/your-repo-name",
        "X-Title": "APR LLM Judge Extension"
    }

    for attempt in range(1, 6):
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=120)

            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]

            if r.status_code in (429, 500, 502, 503, 504):
                print(f"[DEBUG] OpenRouter error {r.status_code} on attempt {attempt}; retrying...")
                time.sleep(3 * attempt)
                continue

            print(f"[DEBUG] OpenRouter status: {r.status_code}")
            raise RuntimeError(f"OpenRouter error {r.status_code}: {r.text}")

        except requests.Timeout:
            print(f"[DEBUG] Request timed out on attempt {attempt}; retrying...")
            time.sleep(3 * attempt)

        except requests.RequestException as e:
            if attempt == 5:
                raise RuntimeError(f"OpenRouter request failed after retries: {e}") from e
            print(f"[DEBUG] Request exception on attempt {attempt}: {e}")
            time.sleep(3 * attempt)

    raise RuntimeError("OpenRouter failed after repeated retries.")

def run_judge(input_csv_override=None, output_csv_override=None):

    # Resolve repo root relative to this file
    repo_root = Path(__file__).resolve().parents[1]
    print(f"[DEBUG] Repo root: {repo_root}")

    # Input / output paths
    data_dir = repo_root / "data"
    output_dir = data_dir / "judge_results"

    if input_csv_override is not None:
        input_csv = Path(input_csv_override)
    else:
        input_csv = data_dir / "patches" / "pysnooper_10.csv"

    if output_csv_override is not None:
        output_csv = Path(output_csv_override)
    else:
        output_csv = output_dir / "openrouter_r1.csv"

    # Load patch data
    df = load_patches(input_csv)

    results = []
    
    for _, row in df.iterrows():
        prompt = build_prompt(row)

        # API call
        response = call_llm_openrouter(prompt)

        # Prevent crash if API returns None
        if response is None:
            response = ""

        if response:
            print("[DEBUG] Raw LLM response:", repr(response[:300]))
        else:
            print("[DEBUG] Raw LLM response: None")

        parsed = parse_output(response)

        parsed["bug_id"] = row["bug_id"]
        parsed["ground_truth_test"] = row["tests_pass"]

        results.append(parsed)

    results_df = pd.DataFrame(results)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    results_df.to_csv(output_csv, index=False)

    print(f"[OK] Saved results to: {output_csv}")

    m = compute_agreement_metrics(results_df)

    print(f"[METRICS] Agreement accuracy: {m['accuracy']:.2%}")
    print(f"[METRICS] False positives: {m['false_positives']}")
    print(f"[METRICS] False negatives: {m['false_negatives']}")
    print(f"[METRICS] Evaluated rows: {m['n_eval']}")
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_csv", type=str, default=None)
    parser.add_argument("--output_csv", type=str, default=None)
    args = parser.parse_args()

    run_judge(args.input_csv, args.output_csv)
    
