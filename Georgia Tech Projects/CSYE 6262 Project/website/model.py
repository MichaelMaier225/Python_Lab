
import json
import re
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix, hstack


ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = ROOT / "models" / "svm_small_v3.joblib"


def clean(value):
    if value is None:
        return ""

    if isinstance(value, (float, np.floating)) and np.isnan(value):
        return ""

    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)

    return re.sub(
        r"\s+",
        " ",
        re.sub(r"[^\w]+", " ", str(value).lower())
    ).strip()


def text_column(df, field, side):
    name = f"{field}_{side}"

    if name not in df:
        return [""] * len(df)

    return [clean(x) for x in df[name]]


def token_set(text):
    return set(text.split())


def number_set(text):
    return set(re.findall(r"\b\d+(?:\.\d+)?\b", text))


def model_set(text):
    tokens = text.split()

    found = {
        t for t in tokens
        if re.search(r"[a-z]", t) and re.search(r"\d", t)
    }

    for a, b in zip(tokens, tokens[1:]):
        if (a.isalpha() and b.isdigit()) or (
            a.isdigit() and b.isalpha()
        ):
            found.add(a + b)

    return found


def overlap_score(a, b):
    return len(a & b) / len(a | b) if a or b else 0.0


def pair_features(df, title_vec, desc_vec):
    lt = text_column(df, "title", "left")
    rt = text_column(df, "title", "right")

    ld = text_column(df, "description", "left")
    rd = text_column(df, "description", "right")

    lb = text_column(df, "brand", "left")
    rb = text_column(df, "brand", "right")

    ta = title_vec.transform(lt)
    tb = title_vec.transform(rt)

    da = desc_vec.transform(ld)
    db = desc_vec.transform(rd)

    title_intersection = ta.multiply(tb)
    desc_intersection = da.multiply(db)

    title_cos = np.asarray(
        title_intersection.sum(axis=1)
    ).ravel()

    desc_cos = np.asarray(
        desc_intersection.sum(axis=1)
    ).ravel()

    rows = []

    for i, (a, b, x, y, brand_a, brand_b) in enumerate(
        zip(lt, rt, ld, rd, lb, rb)
    ):
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
            min(len(a), len(b)) / max(len(a), len(b))
            if a or b else 0.0,
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

    numeric = csr_matrix(
        np.asarray(rows, dtype=np.float64)
    )

    return hstack(
        [title_intersection, desc_intersection, numeric],
        format="csr"
    )


@lru_cache(maxsize=1)
def load_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"SVM model not found: {MODEL_PATH}"
        )

    return joblib.load(MODEL_PATH)


def predict_match(product_a, product_b):
    saved = load_model()

    model = saved["model"]
    title_vec = saved["title_vectorizer"]
    desc_vec = saved["description_vectorizer"]
    threshold = float(saved["threshold"])

    row = {
        "title_left": product_a.title,
        "title_right": product_b.title,
        "brand_left": product_a.brand,
        "brand_right": product_b.brand,
        "description_left": product_a.description,
        "description_right": product_b.description,
    }

    df = pd.DataFrame([row])

    X = pair_features(df, title_vec, desc_vec)

    score = float(model.decision_function(X)[0])

    is_match = score >= threshold

    result = {
        "is_match": bool(is_match),
        "prediction": "Match" if is_match else "Not a Match",
        "decision_score": round(score, 4),
        "threshold": threshold,
    }

    if (
        is_match
        and product_a.price is not None
        and product_b.price is not None
    ):
        difference = abs(
            product_a.price - product_b.price
        )

        if product_a.price < product_b.price:
            cheaper = "Product A"
        elif product_b.price < product_a.price:
            cheaper = "Product B"
        else:
            cheaper = "Same price"

        result["price_comparison"] = {
            "price_difference": round(difference, 2),
            "cheaper_product": cheaper,
        }

    return result
