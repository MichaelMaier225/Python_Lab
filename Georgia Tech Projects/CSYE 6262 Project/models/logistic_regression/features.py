"""Serving-only features matching the teammate's original LR calculations.

The training script is not imported: importing it would retrain the model.
"""

import numpy as np
import pandas as pd

FEATURE_COLUMNS = [
    "title_similarity", "description_similarity", "description_available",
    "same_category", "jaccard_num", "jaccard_alph", "brand_available", "brand_match"
]


def extract_numeric_tokens(description):
    import re

    if pd.isna(description):
        return [], []

    numeric_tokens = re.findall(
        r"\b\w*\d\w*\b",
        description.lower()
    )

    pure_numbers = []
    alphanumeric_tokens = []

    for token in numeric_tokens:

        # Normalize leading zeros
        token = re.sub(r"^0+(?=\d)", "", token)

        if token.isdigit():
            pure_numbers.append(token)
        else:
            alphanumeric_tokens.append(token)

    return pure_numbers, alphanumeric_tokens


def jaccard_similarity(left_tokens, right_tokens):

    left_set = set(left_tokens)
    right_set = set(right_tokens)

    common_tokens = left_set & right_set
    all_tokens = left_set | right_set

    if len(all_tokens) == 0:
        return 0

    return len(common_tokens) / len(all_tokens)


def matching_brand(left_brand, right_brand):

    if pd.isna(left_brand) or pd.isna(right_brand):
        return 0

    left_brand = left_brand.lower().strip()
    right_brand = right_brand.lower().strip()

    if left_brand == right_brand:
        return 1
    else:
        return 0


def pair_features(frame, title_vectorizer, description_vectorizer):
    data = frame.copy()
    for field in ["title", "description", "brand", "category"]:
        for side in ["left", "right"]:
            name = f"{field}_{side}"
            if name not in data:
                data[name] = np.nan
    title_a = title_vectorizer.transform(data["title_left"].fillna(""))
    title_b = title_vectorizer.transform(data["title_right"].fillna(""))
    desc_a = description_vectorizer.transform(data["description_left"].fillna(""))
    desc_b = description_vectorizer.transform(data["description_right"].fillna(""))
    data["title_similarity"] = np.asarray(title_a.multiply(title_b).sum(axis=1)).ravel()
    data["description_similarity"] = np.asarray(desc_a.multiply(desc_b).sum(axis=1)).ravel()
    data["description_available"] = (data["description_left"].notna() & data["description_right"].notna()).astype(int)
    data["same_category"] = (data["category_left"] == data["category_right"]).astype(int)
    left = data["description_left"].apply(extract_numeric_tokens)
    right = data["description_right"].apply(extract_numeric_tokens)
    data["jaccard_num"] = [jaccard_similarity(a[0], b[0]) for a, b in zip(left, right)]
    data["jaccard_alph"] = [jaccard_similarity(a[1], b[1]) for a, b in zip(left, right)]
    data["brand_available"] = (data["brand_left"].notna() & data["brand_right"].notna()).astype(int)
    data["brand_match"] = [matching_brand(a, b) for a, b in zip(data["brand_left"], data["brand_right"])]
    return data[FEATURE_COLUMNS]
