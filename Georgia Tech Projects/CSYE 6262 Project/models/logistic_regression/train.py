# %% Imports
import joblib
from pathlib import Path

import pandas as pd
import numpy as np

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import classification_report, confusion_matrix

# %% Load Computer_XL_Training
df = pd.read_csv(Path(__file__).resolve().parents[2] / "data" / "Computers_XL_Training.csv")

print("Dataset shape:", df.shape)
print(df["label"].value_counts())

# %% Title Similarity - TF-IDF fitted on training data only
train_df = df.copy()

print("Training pairs:", len(train_df))

train_titles = pd.concat([
    train_df["title_left"].fillna(""),
    train_df["title_right"].fillna("")
], ignore_index=True)

title_vectorizer = TfidfVectorizer()

train_vectors = title_vectorizer.fit_transform(train_titles)

n_train = len(train_df)

train_left_vectors = train_vectors[:n_train]
train_right_vectors = train_vectors[n_train:]

train_similarity = (
    train_left_vectors
    .multiply(train_right_vectors)
    .sum(axis=1)
)

train_df["title_similarity"] = np.asarray(
    train_similarity
).ravel()

print(
    train_df.groupby("label")["title_similarity"].describe()
)

# %% Same Category Feature
train_df["same_category"] = (
    train_df["category_left"] ==
    train_df["category_right"]
).astype(int)

print(
    pd.crosstab(
        train_df["same_category"],
        train_df["label"]
    )
)


# %% Extract Numeric and Alphanumeric Tokens from Descriptions
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


train_df["extracted_left"] = (
    train_df["description_left"]
    .apply(extract_numeric_tokens)
)

train_df["pure_numbers_left"] = (
    train_df["extracted_left"]
    .apply(lambda x: x[0])
)

train_df["alphanumeric_left"] = (
    train_df["extracted_left"]
    .apply(lambda x: x[1])
)

train_df["extracted_right"] = (
    train_df["description_right"]
    .apply(extract_numeric_tokens)
)

train_df["pure_numbers_right"] = (
    train_df["extracted_right"]
    .apply(lambda x: x[0])
)

train_df["alphanumeric_right"] = (
    train_df["extracted_right"]
    .apply(lambda x: x[1])
)


# %% Jaccard Similarity
def jaccard_similarity(left_tokens, right_tokens):

    left_set = set(left_tokens)
    right_set = set(right_tokens)

    common_tokens = left_set & right_set
    all_tokens = left_set | right_set

    if len(all_tokens) == 0:
        return 0

    return len(common_tokens) / len(all_tokens)


train_df["jaccard_num"] = train_df.apply(
    lambda row: jaccard_similarity(
        row["pure_numbers_left"],
        row["pure_numbers_right"]
    ),
    axis=1
)

train_df["jaccard_alph"] = train_df.apply(
    lambda row: jaccard_similarity(
        row["alphanumeric_left"],
        row["alphanumeric_right"]
    ),
    axis=1
)

print(
    train_df.groupby("label")[[
        "jaccard_num",
        "jaccard_alph"
    ]].describe()
)


# %% Brand Features
train_df["brand_available"] = (
    train_df["brand_left"].notna() &
    train_df["brand_right"].notna()
).astype(int)


def matching_brand(left_brand, right_brand):

    if pd.isna(left_brand) or pd.isna(right_brand):
        return 0

    left_brand = left_brand.lower().strip()
    right_brand = right_brand.lower().strip()

    if left_brand == right_brand:
        return 1
    else:
        return 0


train_df["brand_match"] = train_df.apply(
    lambda row: matching_brand(
        row["brand_left"],
        row["brand_right"]
    ),
    axis=1
)


# %% Current Model Features
initial_features = [
    "title_similarity",
    "same_category",
    "jaccard_num",
    "jaccard_alph",
    "brand_available",
    "brand_match"
]

print(train_df[initial_features + ["label"]].head())
# %%
train_descriptions = pd.concat([
    train_df["description_left"].fillna(""),
    train_df["description_right"].fillna("")
], ignore_index=True)

description_vectorizer = TfidfVectorizer()

description_vectors = description_vectorizer.fit_transform(
    train_descriptions
)

n_train = len(train_df)

description_left_vectors = description_vectors[:n_train]
description_right_vectors = description_vectors[n_train:]

description_similarity = (
    description_left_vectors
    .multiply(description_right_vectors)
    .sum(axis=1)
)

train_df["description_similarity"] = np.asarray(
    description_similarity
).ravel()

#%%
train_df.groupby("label")[
    "description_similarity"
].describe()

train_df.loc[
    train_df["price_left"].notna(),
    ["price_left", "price_right", "label"]
].head(15)

train_df.loc[
    train_df["specTableContent_left"].notna(),
    ["specTableContent_left", "specTableContent_right", "label"]
].head(5)

print(train_df["specTableContent_left"].dropna().iloc[0])

# %% Description availability
train_df["description_available"] = (
    train_df["description_left"].notna() &
    train_df["description_right"].notna()
).astype(int)


# %% Features used by the model

feature_columns = [
    "title_similarity",
    "description_similarity",
    "description_available",
    "same_category",
    "jaccard_num",
    "jaccard_alph",
    "brand_available",
    "brand_match"
]

X_train = train_df[feature_columns]
y_train = train_df["label"]

from sklearn.linear_model import LogisticRegression

model = LogisticRegression(random_state=42)
model.fit(X_train, y_train)

print("Model training completed!")

# %% Load Gold Standard for Testing

test_df = pd.read_excel(Path(__file__).resolve().parents[2] / "data" / "Gold_Standard.xlsx")

print("Testing pairs:", len(test_df))
print(test_df["label"].value_counts())

# # %% Check Training and Testing Overlap

# train_ids = set(train_df["id_left"]) | set(train_df["id_right"])
# test_ids = set(test_df["id_left"]) | set(test_df["id_right"])

# overlap = train_ids & test_ids

# print("Training products:", len(train_ids))
# print("Testing products:", len(test_ids))
# print("Overlapping products:", len(overlap))

# %% Test - Title Similarity

test_titles = pd.concat([
    test_df["title_left"].fillna(""),
    test_df["title_right"].fillna("")
], ignore_index=True)

test_title_vectors = title_vectorizer.transform(test_titles)

n_test = len(test_df)

test_left_vectors = test_title_vectors[:n_test]
test_right_vectors = test_title_vectors[n_test:]

test_similarity = (
    test_left_vectors
    .multiply(test_right_vectors)
    .sum(axis=1)
)

test_df["title_similarity"] = np.asarray(test_similarity).ravel()

# %% Test - Description Similarity

test_descriptions = pd.concat([
    test_df["description_left"].fillna(""),
    test_df["description_right"].fillna("")
], ignore_index=True)

test_description_vectors = description_vectorizer.transform(
    test_descriptions
)

test_left_description = test_description_vectors[:n_test]
test_right_description = test_description_vectors[n_test:]

test_description_similarity = (
    test_left_description
    .multiply(test_right_description)
    .sum(axis=1)
)

test_df["description_similarity"] = np.asarray(
    test_description_similarity
).ravel()

# %% Test - Description Availability

test_df["description_available"] = (
    test_df["description_left"].notna() &
    test_df["description_right"].notna()
).astype(int)

test_df["same_category"] = (
    test_df["category_left"] ==
    test_df["category_right"]
).astype(int)

# %% Test - Numeric and Alphanumeric Tokens

test_df["extracted_left"] = test_df["description_left"].apply(extract_numeric_tokens)
test_df["extracted_right"] = test_df["description_right"].apply(extract_numeric_tokens)

test_df["pure_numbers_left"] = test_df["extracted_left"].apply(lambda x: x[0])
test_df["pure_numbers_right"] = test_df["extracted_right"].apply(lambda x: x[0])

test_df["alphanumeric_left"] = test_df["extracted_left"].apply(lambda x: x[1])
test_df["alphanumeric_right"] = test_df["extracted_right"].apply(lambda x: x[1])

# %% Test - Jaccard Similarity

test_df["jaccard_num"] = test_df.apply(
    lambda row: jaccard_similarity(
        row["pure_numbers_left"],
        row["pure_numbers_right"]
    ),
    axis=1
)

test_df["jaccard_alph"] = test_df.apply(
    lambda row: jaccard_similarity(
        row["alphanumeric_left"],
        row["alphanumeric_right"]
    ),
    axis=1
)

# %% Test - Brand Features

test_df["brand_available"] = (
    test_df["brand_left"].notna() &
    test_df["brand_right"].notna()
).astype(int)

test_df["brand_match"] = test_df.apply(
    lambda row: matching_brand(
        row["brand_left"],
        row["brand_right"]
    ),
    axis=1
)

# %%

X_test = test_df[feature_columns]
y_test = test_df["label"]

predictions = model.predict(X_test)

prediction_probability = model.predict_proba(X_test)[:, 1]

print("Classification Report:")
print(classification_report(y_test, predictions))

print("Confusion Matrix:")
print(confusion_matrix(y_test, predictions))

# %%
