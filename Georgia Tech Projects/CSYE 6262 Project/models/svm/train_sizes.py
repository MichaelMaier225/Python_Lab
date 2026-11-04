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
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score

from .features import clean, pair_features
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
            "confusion_matrix": confusion_matrix(labels, predicted, labels=[0, 1]).tolist()}


def score_frame(model, title, description, frame):
    output = []
    for start in range(0, len(frame), 256):
        features = pair_features(frame.iloc[start:start + 256], title, description)
        output.extend(model.decision_function(features).tolist())
    if not np.isfinite(output).all():
        raise ValueError("The model produced non-finite scores.")
    return np.asarray(output)


def run(data_dir=DATA, output_root=None, sizes=SIZES):
    data_dir = Path(data_dir)
    for name in ["all_train.zip", "all_valid.zip", "all_gs.json.gz"]:
        if not (data_dir / name).is_file():
            raise ValueError(f"Missing input: {data_dir / name}")
    print("Sizes:", ", ".join(sizes), "+ combined. Models train sequentially; larger sizes may take substantial time and RAM.", flush=True)
    combined, membership, validation, validation_keys, audit = collect_data(data_dir, sizes)
    gold = prepare_pairs(read_gold(data_dir))
    if set(combined["_key"]) & set(gold["_key"]):
        raise ValueError("Training/validation and gold test contain overlapping or reversed product pairs.")
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
    root = Path(output_root) if output_root else MODELS / "size_experiments"
    output = root / run_id
    output.mkdir(parents=True, exist_ok=False)
    provenance = {}
    for name in ["all_train.zip", "all_valid.zip", "all_gs.json.gz"]:
        with (data_dir / name).open("rb") as file:
            provenance[name] = hashlib.file_digest(file, "sha256").hexdigest()
    runtime = {"python": platform.python_version(), "scikit-learn": version("scikit-learn")}
    results = []
    validation[["pair_id", "_key", "label"]].to_csv(output / "validation_pairs.csv", index=False)

    for size in (*sizes, "combined"):
        print(f"\n=== {size.upper()} ===", flush=True)
        train = pool if size == "combined" else pool.loc[pool["_key"].isin(membership[size])]
        if train["label"].nunique() != 2:
            raise ValueError(f"{size}: training needs both match and non-match labels.")
        started = time.perf_counter()
        model, title, description, settings = fit_model(train, validation)
        training_seconds = time.perf_counter() - started
        scores = score_frame(model, title, description, validation)
        validation_metrics = metrics(validation["label"].to_numpy(), scores, settings["threshold"])
        artifact = output / f"svm_{size}.joblib"
        joblib.dump({"model": model, "title_vectorizer": title,
                     "description_vectorizer": description, **settings, "size": size,
                     "training_pairs": len(train), "validation_pairs": len(validation),
                     "validation_metrics": validation_metrics, "source_hashes": provenance,
                     "runtime": runtime, "validation_refit": False}, artifact)
        results.append({"size": size, "training_pairs": len(train), "artifact": artifact.name,
                        "settings": settings, "training_seconds": training_seconds, "validation": validation_metrics})
        (output / "results.json").write_text(json.dumps({"status": "training", "results": results}, indent=2) + "\n")
        print(f"Saved {artifact.name}; validation precision={validation_metrics['precision']:.4f}, F1={validation_metrics['f1']:.4f}", flush=True)
        del model, title, description, scores
        gc.collect()

    # All configurations are fixed before looking at any final test results.
    for result in results:
        bundle = joblib.load(output / result["artifact"])
        scores = score_frame(bundle["model"], bundle["title_vectorizer"], bundle["description_vectorizer"], gold)
        result["test"] = metrics(gold["label"].to_numpy(), scores, bundle["threshold"])
        errors = gold[["pair_id", "title_left", "title_right", "label"]].copy()
        errors["score"] = scores
        errors["prediction"] = (scores >= bundle["threshold"]).astype(int)
        errors.loc[errors["label"] != errors["prediction"]].to_csv(output / f"errors_{result['size']}.csv", index=False)
        del bundle, scores
        gc.collect()
    recommended = max(results, key=lambda item: (item["validation"]["f1"], item["validation"]["precision"]))["size"]
    report = {"status": "complete", "runtime": runtime, "source_hashes": provenance,
              "audit": audit, "common_validation_pairs": len(validation), "test_pairs": len(gold),
              "recommended_by_validation": recommended, "combined_equivalent_to": equivalent_union, "results": results,
              "note": "Gold test was not used for tuning or model selection. Combined is a deduplicated union, not extra independent data. No model was automatically deployed."}
    (output / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    rows = [{"size": item["size"], "training_pairs": item["training_pairs"], "training_seconds": item["training_seconds"],
             **{f"{split}_{key}": item[split][key] for split in ["validation", "test"]
                for key in ["accuracy", "precision", "recall", "f1"]}} for item in results]
    summary = pd.DataFrame(rows)
    summary.to_csv(output / "comparison.csv", index=False)
    print(summary.to_string(index=False), flush=True)
    print(f"\nSaved all models and reports to {output}\nRecommended by validation: {recommended}. Live SVM unchanged.", flush=True)
    return output, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DATA)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--sizes", nargs="+", choices=SIZES, default=list(SIZES))
    args = parser.parse_args()
    if len(args.sizes) != len(set(args.sizes)):
        parser.error("Choose each size once.")
    try:
        run(args.data_dir, args.output_root, tuple(args.sizes))
    except (ValueError, OSError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
