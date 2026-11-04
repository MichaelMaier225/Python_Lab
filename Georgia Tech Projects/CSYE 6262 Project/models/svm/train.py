"""WDC V2 product matching: SVM v3 with richer pairwise features.

Place the original archives in the project data/ directory.
Run from the project root: python -m models.svm.train
"""
from __future__ import annotations

import gzip
import io
import json
import re
import zipfile
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import classification_report, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.svm import LinearSVC

from .features import pair_features, text_column

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
    title_vec = TfidfVectorizer(ngram_range=(1, 2), max_features=50000, sublinear_tf=True)
    desc_vec = TfidfVectorizer(ngram_range=(1, 2), max_features=30000, sublinear_tf=True)
    title_vec.fit(titles)
    # A nonempty fallback prevents failure if a training split lacks descriptions.
    desc_vec.fit(descriptions if any(descriptions) else ["placeholder"])
    print(f"Vocabulary: title={len(title_vec.vocabulary_):,}, description={len(desc_vec.vocabulary_):,}", flush=True)
    return title_vec, desc_vec


def report(label: str, y: np.ndarray, pred: np.ndarray):
    print(f"\n{label}\n{'-' * 55}", flush=True)
    print(classification_report(y, pred, digits=4, zero_division=0), flush=True)
    print("Confusion matrix [[TN, FP], [FN, TP]]:", flush=True)
    print(confusion_matrix(y, pred, labels=[0, 1]), flush=True)
    print(f"Match precision={precision_score(y, pred, zero_division=0):.4f}; "
          f"recall={recall_score(y, pred, zero_division=0):.4f}; "
          f"F1={f1_score(y, pred, zero_division=0):.4f}", flush=True)


def fit_model(train, valid):
    print("\nFitting training-only vectorizers...", flush=True)
    tv, dv = make_vectorizers(train)
    print("Building training features...", flush=True)
    xt = pair_features(train, tv, dv)
    print("Building validation features...", flush=True)
    xv = pair_features(valid, tv, dv)
    yt, yv = train["label"].to_numpy(), valid["label"].to_numpy()

    # Choose both regularization and threshold using validation only.
    print("\nValidation tuning (C and decision threshold):", flush=True)
    best = None
    for c in (0.01, 0.1, 1, 10):
        for weight in (None, "balanced"):
            model = LinearSVC(C=c, class_weight=weight, max_iter=15000, random_state=SEED)
            model.fit(xt, yt)
            scores = model.decision_function(xv)
            for threshold in (-0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0):
                pred = (scores >= threshold).astype(int)
                f1 = f1_score(yv, pred, zero_division=0)
                precision = precision_score(yv, pred, zero_division=0)
                # Break F1 ties in favor of higher precision.
                rank = (f1, precision)
                if best is None or rank > best[0]:
                    best = (rank, c, weight, threshold, model)
            print(f"C={c:<5} class_weight={str(weight):<8} done", flush=True)

    (_, _), best_c, best_weight, best_threshold, selected = best
    print(f"\nSelected: C={best_c}, class_weight={best_weight}, threshold={best_threshold}", flush=True)
    settings = {"C": best_c, "class_weight": best_weight, "threshold": best_threshold}
    return selected, tv, dv, settings


def main():
    MODELS.mkdir(parents=True, exist_ok=True)
    df = read_train()
    valid_ids = read_validation_ids()
    gold = read_gold()
    mask = df["pair_id"].isin(valid_ids)
    train, valid = df.loc[~mask].copy(), df.loc[mask].copy()
    print(f"Training={len(train):,}; validation={len(valid):,}; unmatched validation IDs={len(valid_ids - set(df['pair_id'])):,}", flush=True)
    if len(valid) == 0 or len(train) == 0:
        raise ValueError("Official validation split did not produce nonempty train/validation partitions")
    overlap = set(df["pair_id"]) & set(gold["pair_id"])
    print(f"Gold-standard pair ID overlap: {len(overlap)}", flush=True)
    if overlap:
        raise ValueError("Training/gold pair overlap detected")

    selected, tv, dv, settings = fit_model(train, valid)
    best_c, best_weight, best_threshold = settings["C"], settings["class_weight"], settings["threshold"]
    xv = pair_features(valid, tv, dv)
    report("OFFICIAL VALIDATION RESULTS", valid["label"].to_numpy(),
           (selected.decision_function(xv) >= best_threshold).astype(int))

    print("\nRefitting on all training pairs...", flush=True)
    full_tv, full_dv = make_vectorizers(df)
    xa = pair_features(df, full_tv, full_dv)
    final_model = LinearSVC(C=best_c, class_weight=best_weight, max_iter=15000, random_state=SEED)
    final_model.fit(xa, df["label"].to_numpy())

    print("Building gold-standard features...", flush=True)
    xg = pair_features(gold, full_tv, full_dv)
    gold_pred = (final_model.decision_function(xg) >= best_threshold).astype(int)
    report("GOLD-STANDARD TEST RESULTS", gold["label"].to_numpy(), gold_pred)

    output = MODELS / f"svm_{SIZE}_v3.joblib"
    joblib.dump({"model": final_model, "title_vectorizer": full_tv,
                 "description_vectorizer": full_dv, "threshold": best_threshold,
                 "C": best_c, "class_weight": best_weight, "size": SIZE}, output)
    print(f"\nSaved model to: {output}\nFinished!", flush=True)


if __name__ == "__main__":
    main()
