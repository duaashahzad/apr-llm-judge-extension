import pandas as pd

def compute_agreement_metrics(results_df: pd.DataFrame) -> dict:
    """
    Compute agreement metrics between judge predictions and test outcomes.
    """
    df = results_df.copy()

    df["judge_passes_tests"] = df["passes_tests"].map(
        {"YES": True, "NO": False, "UNKNOWN": None}
    )
    df["test_pass"] = df["ground_truth_test"].astype(bool)

    eval_df = df.dropna(subset=["judge_passes_tests"]).copy()

    accuracy = (eval_df["judge_passes_tests"] == eval_df["test_pass"]).mean()
    false_pos = ((eval_df["judge_passes_tests"]) & (~eval_df["test_pass"])).sum()
    false_neg = ((~eval_df["judge_passes_tests"]) & (eval_df["test_pass"])).sum()

    return {
        "accuracy": float(accuracy),
        "false_positives": int(false_pos),
        "false_negatives": int(false_neg),
        "n_eval": int(len(eval_df)),
    }
