"""Evaluate an existing approved model without fitting or changing its threshold."""

import argparse
import hashlib
import json
import gzip
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score

from models.svm.scoring import decision_scores
from website.registry import load_bundle, model_entry, predict_pairs

ROOT = Path(__file__).resolve().parent.parent


def pair_keys(frame):
    if {'id_left', 'id_right'}.issubset(frame):
        if frame[['id_left', 'id_right']].isna().any().any():
            raise ValueError('Missing product IDs in overlap audit.')
        return pd.Series(['#'.join(sorted((str(a), str(b))))
                          for a, b in zip(frame.id_left, frame.id_right)], index=frame.index)
    parts = frame['pair_id'].astype(str).str.split('#')
    if not parts.map(len).eq(2).all():
        raise ValueError('Overlap audit requires product IDs or pair_id=left#right.')
    return parts.map(lambda pair: '#'.join(sorted(pair)))


def evaluate(data_path, model_id=None, batch_size=256, exclude_training=None):
    entry = model_entry(model_id)
    supported = {'tfidf_pair', 'tfidf_pair_v4', 'logistic_pair_v1', 'random_forest_pair_v1'}
    if entry['adapter'] not in supported:
        raise ValueError('This model needs its original preprocessing adapter before evaluation.')
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
    audit = None
    if exclude_training:
        training_path = Path(exclude_training)
        with zipfile.ZipFile(training_path) as archive:
            members = [name for name in archive.namelist() if Path(name).name == 'computers_train_xlarge.json.gz']
            if len(members) != 1:
                raise ValueError('Expected one computers_train_xlarge.json.gz archive member.')
            with archive.open(members[0]) as file, gzip.GzipFile(fileobj=file) as raw:
                training = pd.read_json(raw, lines=True)
        original_count = len(frame)
        excluded = pair_keys(frame).isin(set(pair_keys(training)))
        frame = frame.loc[~excluded].copy()
        audit = {'reference_archive': training_path.name,
                 'reference_archive_sha256': hashlib.sha256(training_path.read_bytes()).hexdigest(),
                 'archive_member': members[0], 'original_pairs': original_count,
                 'excluded_pairs': int(excluded.sum()), 'retained_pairs': len(frame),
                 'note': 'Exact/reversed pairs excluded against supplied archive; original LR CSV equivalence remains unverified.'}
        if frame.empty or frame['label'].nunique() != 2:
            raise ValueError('Overlap exclusion left no usable two-class evaluation set.')
    if entry['adapter'] in {'tfidf_pair', 'tfidf_pair_v4'}:
        bundle = load_bundle(entry)
        if entry.get('score_type') != 'decision_score' or 'threshold' not in bundle:
            raise ValueError('SVM evaluation requires its saved decision threshold.')
        threshold = float(bundle['threshold'])
        if not np.isfinite(threshold):
            raise ValueError('The saved model threshold must be finite.')
        scores = decision_scores(bundle['model'], bundle['title_vectorizer'],
                                 bundle['description_vectorizer'], frame, batch_size,
                                 feature_schema=bundle.get('feature_schema', 'tfidf_pair'))
        predictions = (scores >= threshold).astype(int)
        score_column = 'decision_score'
    else:
        fields = ['title', 'brand', 'description', 'category', 'specTableContent']
        scores, predictions = [], []
        for start in range(0, len(frame), batch_size):
            chunk = frame.iloc[start:start + batch_size].astype(object)
            chunk = chunk.where(chunk.notna(), None)
            pairs = [tuple({field: row.get(f'{field}_{side}', '') for field in fields}
                           for side in ['left', 'right']) for row in chunk.to_dict('records')]
            batch = predict_pairs(pairs, entry['id'])
            scores.extend(item['raw_score'] for item in batch)
            predictions.extend(int(item['is_match']) for item in batch)
            print(f"{entry['id']}: scored {min(start + batch_size, len(frame)):,}/{len(frame):,} pairs", flush=True)
        scores = np.asarray(scores)
        predictions = np.asarray(predictions)
        threshold = entry['default_threshold']
        score_column = 'probability'
    labels = frame['label'].to_numpy(dtype=int)
    with data_path.open("rb") as file:
        dataset_hash = hashlib.file_digest(file, "sha256").hexdigest()
    result = {
        "model_id": entry["id"], "model_version": entry["version"],
        "model_sha256": entry["sha256"],
        "dataset_id": f"{data_path.name}; sha256:{dataset_hash}",
        "split": "supplied labeled evaluation file",
        "procedure": ("Original saved model, fitted preprocessing and fixed decision rule; no retraining or tuning. "
                      + ("Known exact/reversed pairs excluded against the supplied Computers XL archive. Original LR CSV provenance and full training history are not verified; splits may share products. " if audit else "Training/test overlap not verified. ")
                      + ("Model trained on computers; evaluated here on a broader shared benchmark, not the notebook-specific computer test." if entry['adapter'] in {'logistic_pair_v1', 'random_forest_pair_v1'} else "")),
        "overlap_audit": audit,
        "pair_count": len(frame), "threshold": threshold,
        "retained_pair_ids_sha256": hashlib.sha256("\n".join(frame["pair_id"].astype(str)).encode()).hexdigest(),
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
    details[score_column] = scores
    details["prediction"] = predictions
    details["correct"] = labels == predictions
    return result, details


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "data" / "all_gs.json.gz")
    parser.add_argument("--model", default=None, help="Registry model ID; defaults to the configured active model")
    parser.add_argument("--output", type=Path, default=ROOT / "reports" / "evaluation")
    parser.add_argument("--exclude-training", type=Path, help="Exclude exact/reversed pairs in supplied computers_train.zip XL member")
    args = parser.parse_args()
    if not args.data.is_file():
        parser.error(f"Labeled evaluation file not found: {args.data}")
    try:
        result, details = evaluate(args.data, args.model, exclude_training=args.exclude_training)
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
