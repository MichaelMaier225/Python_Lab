"""Train each WDC size and its deduplicated union. Never overwrite the live SVM."""

import argparse
import gc
import hashlib
import json
import platform
import time
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score, fbeta_score

from .features import clean
from .features_v4 import SCHEMA
from .scoring import decision_scores
from .train import DATA, MODELS, fit_model, read_gold, read_train, read_validation_ids

SIZES = ("small", "medium", "large", "xlarge")
TEXT_FIELDS = ("title", "brand", "description")


def prepare_pairs(frame):
    frame = frame.copy()
    if not {"pair_id", "label"}.issubset(frame):
        raise ValueError("Every training/test record needs pair_id and label.")
    if frame["pair_id"].isna().any() or frame["pair_id"].astype(str).str.strip().eq("").any():
        raise ValueError("Pair IDs must be present.")
    if frame["label"].isna().any() or not set(frame["label"]).issubset({0, 1}):
        raise ValueError("Pair labels must be 0 or 1.")
    if {"id_left", "id_right"}.issubset(frame):
        if frame[["id_left", "id_right"]].isna().any().any():
            raise ValueError("Product IDs must be present on both sides.")
        left, right = frame["id_left"].astype(str), frame["id_right"].astype(str)
    else:
        split = frame["pair_id"].astype(str).str.split("#")
        if not split.map(len).eq(2).all():
            raise ValueError("Pair IDs must identify both products, or supply id_left/id_right.")
        left, right = split.str[0], split.str[1]
    frame["_key"] = ["#".join(sorted((a, b))) for a, b in zip(left, right)]
    # Only fields actually used by this SVM are retained to bound memory usage.
    for field in TEXT_FIELDS:
        for side in ["left", "right"]:
            column = f"{field}_{side}"
            frame[column] = frame[column].map(clean) if column in frame else ""
    # Canonicalize orientation so reversed duplicates have identical features.
    reverse = left > right
    for field in TEXT_FIELDS:
        a, b = f"{field}_left", f"{field}_right"
        frame.loc[reverse, [a, b]] = frame.loc[reverse, [b, a]].to_numpy()
    columns = ["pair_id", "label", "_key"] + [f"{field}_{side}" for field in TEXT_FIELDS for side in ["left", "right"]]
    return frame[columns]


def deduplicate(frame):
    duplicate = frame.loc[frame["_key"].duplicated(keep=False)]
    if not duplicate.empty:
        compared = ["label"] + [f"{field}_{side}" for field in TEXT_FIELDS for side in ["left", "right"]]
        if duplicate.groupby("_key")[compared].nunique(dropna=False).gt(1).any().any():
            raise ValueError("Repeated product pairs have conflicting labels or input features. Inspect the source data first.")
    return frame.drop_duplicates("_key").reset_index(drop=True)


def collect_data(data_dir, sizes):
    validation_ids = set()
    for size in sizes:
        validation_ids.update(read_validation_ids(size, data_dir))
    combined = pd.DataFrame()
    membership, validation_keys, audit = {}, set(), {}
    for size in sizes:
        frame = prepare_pairs(read_train(size, data_dir))
        membership[size] = set(frame["_key"])
        validation_keys.update(frame.loc[frame["pair_id"].isin(validation_ids), "_key"])
        unique = deduplicate(frame)
        audit[size] = {"source_rows": len(frame), "unique_pairs": len(unique)}
        combined = deduplicate(pd.concat([combined, unique], ignore_index=True))
        del frame, unique
    if not validation_keys:
        raise ValueError("Official validation IDs did not match the training records.")
    validation = combined.loc[combined["_key"].isin(validation_keys)].copy()
    if validation["label"].nunique() != 2:
        raise ValueError("The common validation set must contain both labels.")
    audit["combined"] = {"source_rows": sum(audit[size]["source_rows"] for size in sizes),
                         "unique_pairs": len(combined)}
    return combined, membership, validation, validation_keys, audit


def metrics(labels, scores, threshold):
    predicted = (np.asarray(scores) >= threshold).astype(int)
    return {"accuracy": accuracy_score(labels, predicted),
            "precision": precision_score(labels, predicted, zero_division=0),
            "recall": recall_score(labels, predicted, zero_division=0),
            "f1": f1_score(labels, predicted, zero_division=0),
            "f0_5": fbeta_score(labels, predicted, beta=0.5, zero_division=0),
            "confusion_matrix": confusion_matrix(labels, predicted, labels=[0, 1]).tolist()}


def run(data_dir=DATA, output_root=None, sizes=SIZES, overlap_policy="quarantine"):
    if overlap_policy not in {"quarantine", "error"}:
        raise ValueError("Choose overlap policy quarantine or error.")
    data_dir = Path(data_dir)
    for name in ["all_train.zip", "all_valid.zip", "all_gs.json.gz"]:
        if not (data_dir / name).is_file():
            raise ValueError(f"Missing input: {data_dir / name}")
    print("SVM v4 — validation objective F0.5 (precision emphasized). Sizes:", ", ".join(sizes), "+ combined. Models train sequentially; larger sizes may take substantial time and RAM.", flush=True)
    combined, membership, validation, validation_keys, audit = collect_data(data_dir, sizes)
    gold = prepare_pairs(read_gold(data_dir))
    gold_keys = set(gold["_key"])
    overlap = set(combined["_key"]) & gold_keys
    if overlap and overlap_policy == "error":
        raise ValueError("Training/validation and gold test contain overlapping or reversed product pairs.")
    quarantined = combined.loc[combined["_key"].isin(overlap)].copy()
    quarantined["source_sizes"] = [",".join(size for size in sizes if key in membership[size])
                                   for key in quarantined["_key"]]
    quarantined["was_validation"] = quarantined["_key"].isin(validation_keys)
    exclusions = {
        "policy": overlap_policy, "unique_pairs_removed": len(overlap),
        "validation_pairs_removed": int(quarantined["was_validation"].sum()),
        "by_size": {size: len(membership[size] & gold_keys) for size in sizes}
    }
    audit["gold_overlap"] = exclusions
    if overlap:
        print(f"Quarantining {len(overlap):,} gold-test pairs from training/validation (including reversed pairs). Gold test is unchanged.", flush=True)
        for size in sizes:
            print(f"  {size}: {exclusions['by_size'][size]:,} excluded pairs", flush=True)
    combined = combined.loc[~combined["_key"].isin(gold_keys)].copy()
    validation = validation.loc[~validation["_key"].isin(gold_keys)].copy()
    validation_keys -= gold_keys
    for size in sizes:
        membership[size] -= gold_keys
    audit["combined"]["usable_unique_pairs"] = len(combined)
    if validation["label"].nunique() != 2:
        raise ValueError("After gold-test quarantine the common validation set needs both labels.")
    # Fixed holdout is shared across sizes. No final refit on these held-out pairs.
    pool = combined.loc[~combined["_key"].isin(validation_keys)].copy()
    if pool.empty:
        raise ValueError("No training pairs remain after validation exclusion.")
    print(f"Union: {len(combined):,} unique pairs; common validation: {len(validation):,}; train pool: {len(pool):,}", flush=True)
    equivalent_union = [size for size in sizes if len(pool) == len(membership[size] - validation_keys)
                        and pool["_key"].isin(membership[size]).all()]
    if equivalent_union:
        print("Combined has the same unique training pairs as: " + ", ".join(equivalent_union), flush=True)
    del combined
    gc.collect()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    root = Path(output_root) if output_root else MODELS / "v4_size_experiments"
    output = root / run_id
    output.mkdir(parents=True, exist_ok=False)
    provenance = {}
    for name in ["all_train.zip", "all_valid.zip", "all_gs.json.gz"]:
        with (data_dir / name).open("rb") as file:
            provenance[name] = hashlib.file_digest(file, "sha256").hexdigest()
    runtime = {"python": platform.python_version(), "scikit-learn": version("scikit-learn")}
    pipeline_hashes = {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                       for name in ['features.py', 'features_v4.py', 'train.py', 'scoring.py', 'train_sizes.py']}
    results = []
    validation[["pair_id", "_key", "label"]].to_csv(output / "validation_pairs.csv", index=False)
    quarantined.to_csv(output / "quarantined_gold_overlap.csv", index=False)
    (output / "split_audit.json").write_text(json.dumps({"source_hashes": provenance, "audit": audit}, indent=2) + "\n")

    for size in (*sizes, "combined"):
        print(f"\n=== {size.upper()} ===", flush=True)
        train = pool if size == "combined" else pool.loc[pool["_key"].isin(membership[size])]
        if train["label"].nunique() != 2:
            raise ValueError(f"{size}: training needs both match and non-match labels.")
        if train["_key"].isin(gold_keys | validation_keys).any():
            raise ValueError(f"{size}: protected validation/test pairs remain in training.")
        started = time.perf_counter()
        model, title, description, settings = fit_model(train, validation)
        training_seconds = time.perf_counter() - started
        train_scores = decision_scores(model, title, description, train, feature_schema=SCHEMA)
        training_metrics = metrics(train["label"].to_numpy(), train_scores, settings["threshold"])
        train_products = {part for key in train["_key"] for part in key.split("#")}
        valid_products = {part for key in validation["_key"] for part in key.split("#")}
        shared_products = len(train_products & valid_products)
        gold_products = {part for key in gold_keys for part in key.split("#")}
        shared_test_products = len(train_products & gold_products)
        print(f"Shared product IDs: train/validation={shared_products:,}; train/test={shared_test_products:,}. Pair-disjoint is not product-disjoint.", flush=True)
        scores = decision_scores(model, title, description, validation, feature_schema=SCHEMA)
        validation_metrics = metrics(validation["label"].to_numpy(), scores, settings["threshold"])
        artifact = output / f"svm_{size}.joblib"
        joblib.dump({"model": model, "title_vectorizer": title,
                     "description_vectorizer": description, **settings, "size": size,
                     "training_pairs": len(train), "validation_pairs": len(validation),
                     "validation_metrics": validation_metrics, "training_metrics": training_metrics, "source_hashes": provenance,
                     "runtime": runtime, "pipeline_hashes": pipeline_hashes, "validation_refit": False,
                     "gold_overlap_exclusions": exclusions}, artifact)
        results.append({"size": size, "training_pairs": len(train), "artifact": artifact.name,
                        "settings": settings, "training_seconds": training_seconds, "training": training_metrics,
                        "shared_train_validation_product_ids": shared_products,
                        "shared_train_test_product_ids": shared_test_products, "validation": validation_metrics})
        (output / "results.json").write_text(json.dumps({"status": "training", "results": results}, indent=2) + "\n")
        print(f"Saved {artifact.name}; threshold={settings['threshold']:.4f}; validation precision={validation_metrics['precision']:.4f}, recall={validation_metrics['recall']:.4f}, F1={validation_metrics['f1']:.4f}, F0.5={validation_metrics['f0_5']:.4f}", flush=True)
        print(f"TRAIN precision={training_metrics['precision']:.4f}, recall={training_metrics['recall']:.4f}, F1={training_metrics['f1']:.4f}; VALIDATION F1 gap={training_metrics['f1'] - validation_metrics['f1']:+.4f}", flush=True)
        del model, title, description, scores, train_scores
        gc.collect()

    recommended = max(results, key=lambda item: (item["validation"]["f0_5"], item["validation"]["precision"]))["size"]
    print(f"Selected by validation F0.5 before test scoring: {recommended}", flush=True)
    # All configurations are fixed before looking at any final test results.
    for result in results:
        bundle = joblib.load(output / result["artifact"])
        scores = decision_scores(bundle["model"], bundle["title_vectorizer"], bundle["description_vectorizer"], gold, feature_schema=SCHEMA)
        result["test"] = metrics(gold["label"].to_numpy(), scores, bundle["threshold"])
        test = result["test"]
        print(f"{result['size'].upper()} TEST: accuracy={test['accuracy']:.2%}, precision={test['precision']:.2%}, recall={test['recall']:.2%}, F1={test['f1']:.2%}; threshold={bundle['threshold']:.4f}", flush=True)
        errors = gold[["pair_id", "title_left", "title_right", "label"]].copy()
        errors["score"] = scores
        errors["prediction"] = (scores >= bundle["threshold"]).astype(int)
        errors.loc[errors["label"] != errors["prediction"]].to_csv(output / f"errors_{result['size']}.csv", index=False)
        diagnostic_path = Path(__file__).resolve().parents[2] / 'docs/evaluation/svm_sizes_20261104/known_false_matches.json'
        if diagnostic_path.is_file():
            examples = json.loads(diagnostic_path.read_text())['pairs']
            diagnostic_frame = pd.DataFrame([{f'{field}_{side}': product.get(field, '')
                for product, side in [(item['a'], 'left'), (item['b'], 'right')]
                for field in TEXT_FIELDS} for item in examples])
            diagnostic_scores = decision_scores(bundle['model'], bundle['title_vectorizer'], bundle['description_vectorizer'], diagnostic_frame, feature_schema=SCHEMA)
            result['known_browser_examples'] = [{'score': float(score), 'prediction': bool(score >= bundle['threshold']),
                                                 'expected_match': item['expected_match']}
                                                for score, item in zip(diagnostic_scores, examples)]
            wrong = sum(item['prediction'] != item['expected_match'] for item in result['known_browser_examples'])
            print(f"{result['size'].upper()} KNOWN BROWSER FAILURES: {wrong}/{len(examples)} still wrong. Diagnostic examples, not an independent performance estimate.", flush=True)
        del bundle, scores
        gc.collect()
    report = {"status": "complete", "feature_schema": SCHEMA, "selection_metric": "F0.5", "runtime": runtime, "source_hashes": provenance,
              "pipeline_hashes": pipeline_hashes, "audit": audit, "common_validation_pairs": len(validation), "test_pairs": len(gold),
              "recommended_by_validation": recommended, "combined_equivalent_to": equivalent_union, "results": results,
              "note": "Gold test was not used for tuning or model selection. Combined is a deduplicated union, not extra independent data. No model was automatically deployed."}
    (output / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    rows = [{"size": item["size"], "training_pairs": item["training_pairs"], "training_seconds": item["training_seconds"],
             **{f"{split}_{key}": item[split][key] for split in ["training", "validation", "test"]
                for key in ["accuracy", "precision", "recall", "f1"]}} for item in results]
    summary = pd.DataFrame(rows)
    summary.to_csv(output / "comparison.csv", index=False)
    terminal = pd.DataFrame([{'Model': item['size'].upper(), 'Threshold': f"{item['settings']['threshold']:.4f}",
                               **{key.capitalize(): f"{item['test'][key]:.2%}" for key in ['accuracy', 'precision', 'recall', 'f1']}}
                              for item in results])
    print("\nFINAL GOLD-TEST RESULTS (not website precision):", flush=True)
    print(terminal.to_string(index=False), flush=True)
    print(f"\nSaved all models and reports to {output}\nRecommended by validation: {recommended}. Live SVM unchanged. Compare held-out results before deployment. Benchmark results do not establish phone/accessory performance.", flush=True)
    return output, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DATA)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--sizes", nargs="+", choices=SIZES, default=list(SIZES))
    parser.add_argument("--overlap-policy", choices=["quarantine", "error"], default="quarantine",
                        help="Remove gold-test pairs from training/validation and audit them (default), or stop on any overlap.")
    args = parser.parse_args()
    if len(args.sizes) != len(set(args.sizes)):
        parser.error("Choose each size once.")
    try:
        run(args.data_dir, args.output_root, tuple(args.sizes), args.overlap_policy)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
