"""V4 features plus an explicit MacBook compatibility-size conflict."""

import re

from scipy.sparse import csr_matrix, hstack

from .features import text_column
from .features_v4 import pair_features as v4_features

SCHEMA = "tfidf_pair_v5"
SIZE_MENTION = re.compile(r"\b\d+\s*inch\b")
MACBOOK = re.compile(r"\bmacbook\s+(pro|air)\b")
COVERED_SIZE = re.compile(
    r"\b(?:for|fits|compatible with)\s+(1[0-9])\s*inch\s+macbook\s+(pro|air)\b"
)


def covered_size(title):
    if len(MACBOOK.findall(title)) != 1 or len(SIZE_MENTION.findall(title)) != 1:
        return None
    match = COVERED_SIZE.search(title)
    return match.groups() if match else None


def pair_features(frame, title_vectorizer, description_vectorizer):
    # Features
    base = v4_features(frame, title_vectorizer, description_vectorizer)
    left = text_column(frame, "title", "left")
    right = text_column(frame, "title", "right")
    conflicts = []
    for a, b in zip(left, right):
        size_a, size_b = covered_size(a), covered_size(b)
        conflicts.append(int(bool(size_a and size_b and size_a[1] == size_b[1] and size_a[0] != size_b[0])))
    return hstack([base, csr_matrix(conflicts, dtype=float).T], format="csr")
