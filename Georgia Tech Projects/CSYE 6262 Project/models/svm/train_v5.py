import argparse
import hashlib
import json
from datetime import datetime, timezone
from importlib.metadata import version
from itertools import chain
from pathlib import Path

import joblib
import pandas as pd

from website.registry import load_bundle, model_entry

from .features_v5 import SCHEMA, pair_features
from .scoring import decision_scores
from .train import DATA, MODELS, fit_model, read_gold
from .train_sizes import SIZES, collect_data, deduplicate, metrics, prepare_pairs


def compare(frame, bundles):
    return {
        name: metrics(frame["label"], decision_scores(
            bundle["model"], bundle["title_vectorizer"], bundle["description_vectorizer"],
            frame, feature_schema=bundle["feature_schema"],
        ), bundle["threshold"])
        for name, bundle in bundles.items()
    }


def run(data_dir=DATA, output_root=MODELS / "v5", fresh_test=None):
    # Load data
    data_dir = Path(data_dir)
    inputs = [data_dir / name for name in ("all_train.zip", "all_valid.zip", "all_gs.json.gz")]
    missing = [str(path) for path in inputs if not path.is_file()]
    if missing:
        raise ValueError("Missing WDC inputs: " + ", ".join(missing))

    baseline = load_bundle(model_entry("linear_svc_combined"))
    gold = deduplicate(prepare_pairs(read_gold(data_dir)))
    combined, _, validation, validation_keys, _ = collect_data(data_dir, SIZES)
    gold_keys = set(gold["_key"])
    train = combined.loc[~combined["_key"].isin(validation_keys | gold_keys)]
    validation = validation.loc[~validation["_key"].isin(gold_keys)]
    del combined
    tests = {"wdc_gold": gold}
    if fresh_test:
        fresh = deduplicate(prepare_pairs(pd.read_json(fresh_test, lines=True, compression="gzip")))
        seen_products = {product for key in chain(train["_key"], validation["_key"], gold["_key"])
                         for product in key.split("#")}
        fresh = fresh.loc[~fresh["_key"].map(
            lambda key: any(product in seen_products for product in key.split("#"))
        )]
        tests["fresh"] = fresh

    for name, frame in {"training": train, "validation": validation, **tests}.items():
        if frame["label"].nunique() != 2:
            raise ValueError(f"{name} needs both match and different pairs after overlap checks.")

    # Train model
    model, title, description, settings = fit_model(
        train, validation, feature_builder=pair_features, feature_schema=SCHEMA,
    )
    source_hashes = {}
    for path in inputs:
        with path.open("rb") as file:
            source_hashes[path.name] = hashlib.file_digest(file, "sha256").hexdigest()
    candidate = {
        "model": model, "title_vectorizer": title, "description_vectorizer": description,
        **settings, "training_pairs": len(train), "validation_pairs": len(validation),
        "source_hashes": source_hashes, "runtime": {"scikit-learn": version("scikit-learn")},
    }

    # Evaluate and save
    report = {
        "feature": "macbook_compatibility_size_conflict",
        "feature_weight": float(model.coef_[0, -1]),
        "source_hashes": source_hashes,
        "results": {name: {"pairs": len(frame), **compare(frame, {"v4": baseline, "v5": candidate})}
                    for name, frame in tests.items()},
    }
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    output = Path(output_root) / run_id
    output.mkdir(parents=True)
    joblib.dump(candidate, output / "svm_combined.joblib")
    (output / "comparison.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"Saved v5 candidate and comparison to {output}")
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DATA)
    parser.add_argument("--output-root", type=Path, default=MODELS / "v5")
    parser.add_argument("--fresh-test", type=Path, help="Verified WDC-format pairs as gzipped JSON Lines.")
    args = parser.parse_args()
    try:
        run(args.data_dir, args.output_root, args.fresh_test)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
