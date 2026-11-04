"""Shared batch scoring for saved-model evaluation and size experiments."""

import numpy as np

from .features import pair_features


def decision_scores(model, title_vectorizer, description_vectorizer, frame, batch_size=256, feature_schema="tfidf_pair"):
    if feature_schema not in {"tfidf_pair", "tfidf_pair_v4"}:
        raise ValueError("Unknown SVM feature schema.")
    builder = pair_features
    if feature_schema == "tfidf_pair_v4":
        from .features_v4 import pair_features as builder
    if batch_size < 1:
        raise ValueError("Batch size must be positive.")
    scores = []
    for start in range(0, len(frame), batch_size):
        features = builder(frame.iloc[start:start + batch_size],
                                 title_vectorizer, description_vectorizer)
        scores.extend(model.decision_function(features).tolist())
    scores = np.asarray(scores)
    if not np.isfinite(scores).all():
        raise ValueError("The model produced non-finite scores.")
    return scores
