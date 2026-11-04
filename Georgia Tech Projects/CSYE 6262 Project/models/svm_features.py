"""Original SVM feature calculations, shared by training and serving."""

import json
import re

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix, hstack
from sklearn.feature_extraction.text import TfidfVectorizer


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
