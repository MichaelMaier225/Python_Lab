"""WDC V2 product matching: SVM v3 with richer pairwise features.

Place this file beside data/all_train.zip, data/all_valid.zip,
and data/all_gs.json.gz.

Run: py -3.12 -u train_svm_v3.py
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
from scipy.sparse import csr_matrix, hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import classification_report, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.svm import LinearSVC

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
MODELS = ROOT / "models"
SIZE = "small"  # Try medium or large after establishing a baseline.
SEED = 42


def read_train() -> pd.DataFrame:
    path = DATA / "all_train.zip"
    print(f"Loading {SIZE} training data...", flush=True)
    with zipfile.ZipFile(path) as z:
        matches = [n for n in z.namelist() if n.lower().endswith(f"all_train_{SIZE}.json.gz")]
        if len(matches) != 1:
            raise ValueError(f"Expected one training member; found {matches}. Archive: {z.namelist()[:20]}")
        with z.open(matches[0]) as f, gzip.GzipFile(fileobj=f) as g:
            df = pd.read_json(g, lines=True)
    df["pair_id"] = df["pair_id"].astype(str)
    df["label"] = df["label"].astype(int)
    print(f"Loaded {len(df):,} training pairs", flush=True)
    return df


def read_validation_ids() -> set[str]:
    path = DATA / "all_valid.zip"
    with zipfile.ZipFile(path) as z:
        matches = [n for n in z.namelist() if not n.endswith("/") and SIZE in Path(n).name.lower()]
        if len(matches) != 1:
            raise ValueError(f"Expected one {SIZE} validation file; found {matches}")
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


def read_gold() -> pd.DataFrame:
    print("Loading gold standard...", flush=True)
    df = pd.read_json(DATA / "all_gs.json.gz", compression="gzip", lines=True)
    df["pair_id"] = df["pair_id"].astype(str)
    df["label"] = df["label"].astype(int)
    print(f"Gold-standard pairs: {len(df):,}", flush=True)
    return df


def clean(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, (float, np.floating)) and np.isnan(value):
        return ""
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    return re.sub(r"\s+", " ", re.sub(r"[^\w]+", " ", str(value).lower())).strip()


def text_column(df: pd.DataFrame, field: str, side: str) -> list[str]:
    name = f"{field}_{side}"
    if name not in df:
        return [""] * len(df)
    return [clean(x) for x in df[name]]


def token_set(text: str) -> set[str]:
    return set(text.split())


def number_set(text: str) -> set[str]:
    return set(re.findall(r"\b\d+(?:\.\d+)?\b", text))


def model_set(text: str) -> set[str]:
    # Alphanumeric identifiers, e.g. 'rtx4060', 'a7iv', 'wh1000xm5'.
    # Also capture adjacent letter/number tokens as a possible identifier.
    tokens = text.split()
    found = {t for t in tokens if re.search(r"[a-z]", t) and re.search(r"\d", t)}
    for a, b in zip(tokens, tokens[1:]):
        if (a.isalpha() and b.isdigit()) or (a.isdigit() and b.isalpha()):
            found.add(a + b)
    return found


def overlap_score(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a or b else 0.0


def pair_features(df: pd.DataFrame, title_vec: TfidfVectorizer,
                  desc_vec: TfidfVectorizer) -> csr_matrix:
    lt, rt = text_column(df, "title", "left"), text_column(df, "title", "right")
    ld, rd = text_column(df, "description", "left"), text_column(df, "description", "right")
    lb, rb = text_column(df, "brand", "left"), text_column(df, "brand", "right")

    ta, tb = title_vec.transform(lt), title_vec.transform(rt)
    da, db = desc_vec.transform(ld), desc_vec.transform(rd)
    title_intersection = ta.multiply(tb)
    desc_intersection = da.multiply(db)
    title_cos = np.asarray(title_intersection.sum(axis=1)).ravel()
    desc_cos = np.asarray(desc_intersection.sum(axis=1)).ravel()

    rows = []
    for i, (a, b, x, y, brand_a, brand_b) in enumerate(zip(lt, rt, ld, rd, lb, rb)):
        at, bt = token_set(a), token_set(b)
        an, bn = number_set(a), number_set(b)
        am, bm = model_set(a), model_set(b)
        brand_known = bool(brand_a and brand_b)
        nums_known = bool(an and bn)
        models_known = bool(am and bm)
        rows.append([
            title_cos[i],
            desc_cos[i],
            overlap_score(at, bt),
            min(len(a), len(b)) / max(len(a), len(b)) if a or b else 0.0,
            float(bool(a) and a == b),
            float(bool(x) and bool(y)),
            float(brand_known),
            float(brand_known and brand_a == brand_b),
            float(brand_known and brand_a != brand_b),
            float(bool(an or bn)),
            float(nums_known and an == bn),
            float(nums_known and an != bn),
            overlap_score(an, bn),
            float(bool(am or bm)),
            float(models_known and am == bm),
            float(models_known and am != bm),
            overlap_score(am, bm),
        ])
    numeric = csr_matrix(np.asarray(rows, dtype=np.float64))
    return hstack([title_intersection, desc_intersection, numeric], format="csr")


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


def main():
    MODELS.mkdir(exist_ok=True)
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
                    best = (rank, c, weight, threshold)
            print(f"C={c:<5} class_weight={str(weight):<8} done", flush=True)

    (_, _), best_c, best_weight, best_threshold = best
    print(f"\nSelected: C={best_c}, class_weight={best_weight}, threshold={best_threshold}", flush=True)
    selected = LinearSVC(C=best_c, class_weight=best_weight, max_iter=15000, random_state=SEED)
    selected.fit(xt, yt)
    report("OFFICIAL VALIDATION RESULTS", yv,
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
