"""WDC V2 SVM v4 training helpers.

Place the original archives in the project data/ directory.
Run from the project root: python -m models.svm.train
"""
from __future__ import annotations

import gzip
import io
import json
import re
import zipfile
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import precision_recall_curve
from sklearn.svm import LinearSVC
from sklearn.exceptions import ConvergenceWarning

from .features import text_column
from .features_v4 import pair_features, SCHEMA

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
MODELS = ROOT / "trained_models" / "svm"
SIZE = "small"  # Try medium or large after establishing a baseline.
SEED = 42


def read_train(size=SIZE, data_dir=DATA) -> pd.DataFrame:
    path = Path(data_dir) / "all_train.zip"
    print(f"Loading {size} training data...", flush=True)
    with zipfile.ZipFile(path) as z:
        matches = [n for n in z.namelist() if n.lower().endswith(f"all_train_{size}.json.gz")]
        if len(matches) != 1:
            raise ValueError(f"Expected one training member; found {matches}. Archive: {z.namelist()[:20]}")
        with z.open(matches[0]) as f, gzip.GzipFile(fileobj=f) as g:
            df = pd.read_json(g, lines=True)
    df["pair_id"] = df["pair_id"].astype(str)
    if df["label"].isna().any() or not set(df["label"]).issubset({0, 1}):
        raise ValueError("Dataset labels must be 0 or 1.")
    df["label"] = df["label"].astype(int)
    print(f"Loaded {len(df):,} training pairs", flush=True)
    return df


def read_validation_ids(size=SIZE, data_dir=DATA) -> set[str]:
    path = Path(data_dir) / "all_valid.zip"
    with zipfile.ZipFile(path) as z:
        matches = [n for n in z.namelist() if not n.endswith("/") and re.search(rf"(?<![a-z0-9]){re.escape(size)}(?![a-z0-9])", Path(n).name.lower())]
        if len(matches) != 1:
            raise ValueError(f"Expected one {size} validation file; found {matches}")
        name = matches[0]
        raw = z.read(name)
    if name.lower().endswith(".gz"):
        raw = gzip.decompress(raw)
    content = raw.decode("utf-8-sig").strip()
    print(f"Validation file: {name}", flush=True)
    if name.lower().endswith((".csv", ".csv.gz")):
        table = pd.read_csv(io.StringIO(content), dtype=str)
        col = "pair_id" if "pair_id" in table else table.columns[0] if len(table.columns) == 1 else None
        if col is None:
            raise ValueError(f"Cannot identify pair_id column: {table.columns.tolist()}")
        ids = table[col].dropna().astype(str).tolist()
    else:
        try:
            obj = json.loads(content)
            if isinstance(obj, dict):
                obj = next((obj[k] for k in ("pair_id", "pair_ids", "validation_ids", "ids") if k in obj), None)
            if not isinstance(obj, list):
                raise ValueError("Validation JSON must contain a list of IDs")
            ids = [str(x.get("pair_id", "")) if isinstance(x, dict) else str(x) for x in obj]
        except json.JSONDecodeError:
            ids = [str(json.loads(line)["pair_id"]) if line.startswith("{") else line.strip('"')
                   for line in content.splitlines() if line.strip() and line.strip().lower() != "pair_id"]
    result = {x for x in ids if x and x.lower() != "nan"}
    print(f"Validation IDs: {len(result):,}", flush=True)
    return result


def read_gold(data_dir=DATA) -> pd.DataFrame:
    print("Loading gold standard...", flush=True)
    df = pd.read_json(Path(data_dir) / "all_gs.json.gz", compression="gzip", lines=True)
    df["pair_id"] = df["pair_id"].astype(str)
    if df["label"].isna().any() or not set(df["label"]).issubset({0, 1}):
        raise ValueError("Dataset labels must be 0 or 1.")
    df["label"] = df["label"].astype(int)
    print(f"Gold-standard pairs: {len(df):,}", flush=True)
    return df


def make_vectorizers(train: pd.DataFrame):
    titles = text_column(train, "title", "left") + text_column(train, "title", "right")
    descriptions = text_column(train, "description", "left") + text_column(train, "description", "right")
    title_vec = TfidfVectorizer(ngram_range=(1, 2), max_features=50000, sublinear_tf=True, token_pattern=r"(?u)\b\w+\b")
    desc_vec = TfidfVectorizer(ngram_range=(1, 2), max_features=30000, sublinear_tf=True, token_pattern=r"(?u)\b\w+\b")
    title_vec.fit(titles)
    # A nonempty fallback prevents failure if a training split lacks descriptions.
    desc_vec.fit(descriptions if any(descriptions) else ["placeholder"])
    print(f"Vocabulary: title={len(title_vec.vocabulary_):,}, description={len(desc_vec.vocabulary_):,}", flush=True)
    return title_vec, desc_vec


def fit_model(train, valid):
    print("\nFitting training-only vectorizers...", flush=True)
    tv, dv = make_vectorizers(train)
    print("Building training features...", flush=True)
    xt = pair_features(train, tv, dv)
    print("Building validation features...", flush=True)
    xv = pair_features(valid, tv, dv)
    yt, yv = train["label"].to_numpy(), valid["label"].to_numpy()

    # Choose both regularization and threshold using validation only.
    print("\nValidation tuning (C and threshold, optimizing F0.5):", flush=True)
    best = None
    for c in (0.001, 0.01, 0.1, 1, 10):
        for weight in (None, "balanced"):
            model = LinearSVC(C=c, class_weight=weight, max_iter=15000, random_state=SEED)
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always", ConvergenceWarning)
                model.fit(xt, yt)
            if any(issubclass(item.category, ConvergenceWarning) for item in caught):
                print(f"C={c}: solver did not converge; excluding this candidate.", flush=True)
                continue
            scores = model.decision_function(xv)
            precision, recall, thresholds = precision_recall_curve(yv, scores)
            precision, recall = precision[:-1], recall[:-1]
            beta2 = 0.5 ** 2
            objective = (1 + beta2) * precision * recall / np.maximum(beta2 * precision + recall, 1e-15)
            index = np.lexsort((recall, precision, objective))[-1]
            rank = (float(objective[index]), float(precision[index]), float(recall[index]))
            if best is None or rank > best[0]:
                best = (rank, c, weight, float(thresholds[index]), model)
            print(f"C={c:<5} class_weight={str(weight):<8} done", flush=True)

    if best is None:
        raise ValueError("No SVM candidate converged. Inspect training inputs before increasing iteration limits.")
    _, best_c, best_weight, best_threshold, selected = best
    print(f"\nSelected: C={best_c}, class_weight={best_weight}, threshold={best_threshold}", flush=True)
    settings = {"C": best_c, "class_weight": best_weight, "threshold": best_threshold, "feature_schema": SCHEMA, "selection_metric": "F0.5"}
    return selected, tv, dv, settings


def main():
    # One maintained training workflow: all sizes, audited splits, no validation refit.
    from .train_sizes import main as train_all_sizes
    train_all_sizes()


if __name__ == "__main__":
    main()
