"""Evaluate an existing approved model without fitting or changing its threshold."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score

from models.svm.scoring import decision_scores
from website.registry import load_bundle, model_entry

ROOT = Path(__file__).resolve().parent.parent


def evaluate(data_path, model_id=None, batch_size=256):
    entry = model_entry(model_id)
    if entry["adapter"] != "tfidf_pair":
        raise ValueError("This model needs its original preprocessing adapter before evaluation.")
    bundle = load_bundle(entry)
    if entry.get("score_type") != "decision_score" or "threshold" not in bundle:
        raise ValueError("This evaluator requires a decision-score model with a saved threshold.")
    if batch_size < 1:
        raise ValueError("Batch size must be positive.")
    data_path = Path(data_path)
    frame = pd.read_json(data_path, lines=True, compression="gzip")
    required = {"pair_id", "label", "title_left", "title_right"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError("Missing dataset columns: " + ", ".join(sorted(missing)))
    if frame.empty or frame["label"].isna().any() or not set(frame["label"]).issubset({0, 1}):
        raise ValueError("Evaluation needs nonempty labeled pairs with labels 0 and 1.")
    threshold = float(bundle["threshold"])
    if not np.isfinite(threshold):
        raise ValueError("The saved model threshold must be finite.")
    scores = decision_scores(bundle["model"], bundle["title_vectorizer"],
                             bundle["description_vectorizer"], frame, batch_size)
    labels = frame["label"].to_numpy(dtype=int)
    predictions = (scores >= threshold).astype(int)
    with data_path.open("rb") as file:
        dataset_hash = hashlib.file_digest(file, "sha256").hexdigest()
    result = {
        "model_id": entry["id"], "model_version": entry["version"],
        "model_sha256": entry["sha256"],
        "dataset_id": f"{data_path.name}; sha256:{dataset_hash}",
        "split": "supplied labeled evaluation file",
        "procedure": "Saved model and fixed threshold; no training or tuning. Training/test overlap not verified.",
        "pair_count": len(frame), "threshold": threshold,
        "metrics": {
            "accuracy": accuracy_score(labels, predictions),
            "precision": precision_score(labels, predictions, zero_division=0),
            "recall": recall_score(labels, predictions, zero_division=0),
            "f1": f1_score(labels, predictions, zero_division=0)
        },
        "confusion_matrix": confusion_matrix(labels, predictions, labels=[0, 1]).tolist(),
        "confusion_matrix_order": "[[TN, FP], [FN, TP]]"
    }
    details = frame[[name for name in ["pair_id", "title_left", "title_right", "label"] if name in frame]].copy()
    details["decision_score"] = scores
    details["prediction"] = predictions
    details["correct"] = labels == predictions
    return result, details


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "data" / "all_gs.json.gz")
    parser.add_argument("--model", default=None, help="Registry model ID; defaults to the configured active model")
    parser.add_argument("--output", type=Path, default=ROOT / "reports" / "evaluation")
    args = parser.parse_args()
    if not args.data.is_file():
        parser.error(f"Labeled evaluation file not found: {args.data}")
    try:
        result, details = evaluate(args.data, args.model)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    protected = [ROOT / name for name in ["models", "trained_models", "website", "data", "tests", "scripts", "docs"]]
    output = args.output.resolve()
    if output == ROOT or any(output.is_relative_to(path) for path in protected):
        parser.error("Save evaluation reports outside the source, dataset, and model folders (default: reports/evaluation).")
    output.mkdir(parents=True, exist_ok=True)
    (output / "evaluation.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    details.to_csv(output / "predictions.csv", index=False)
    details.loc[~details["correct"]].to_csv(output / "errors.csv", index=False)
    print(f"Model: {result['model_id']} | Pairs: {result['pair_count']:,} | Saved threshold: {result['threshold']}")
    for name, value in result["metrics"].items():
        print(f"{name.capitalize()}: {value:.2%}")
    print("Confusion matrix [[TN, FP], [FN, TP]]:", result["confusion_matrix"])
    print(f"Reports saved to: {output}")
    print("No model was retrained or overwritten. Keep test data separate from tuning.")


if __name__ == "__main__":
    main()
