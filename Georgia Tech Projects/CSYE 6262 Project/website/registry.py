"""Small, server-configured registry. Never accept artifact paths from requests."""

import hashlib
import json
import math
import os
import warnings
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.exceptions import InconsistentVersionWarning

from models.svm.features import pair_features
from models.logistic_regression.features import FEATURE_COLUMNS, pair_features as logistic_features

ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = ROOT / "trained_models" / "registry.json"


class ModelUnavailable(ValueError):
    pass


def entries():
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))["models"]


def model_entry(model_id=None):
    config = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    model_id = model_id or os.getenv("ACTIVE_MODEL", config["default_model"])
    for entry in config["models"]:
        if entry["id"] == model_id:
            return entry
    raise ModelUnavailable("Unknown configured model.")


def artifact_path(entry):
    directory = Path(os.getenv("PRODUCTMATCH_MODEL_DIR", ROOT / "trained_models")).resolve()
    path = (directory / entry["artifact"]).resolve()
    if not path.is_relative_to(directory):
        raise ModelUnavailable("Model artifact must remain inside the model directory.")
    return path


@lru_cache(maxsize=4)
def read_bundle(path, checksum, modified):
    if not checksum or len(checksum) != 64:
        raise ModelUnavailable("Set the trusted model SHA-256 in the registry or MODEL_SHA256 before loading it.")
    with Path(path).open("rb") as file:
        digest = hashlib.file_digest(file, "sha256").hexdigest()
        if digest != checksum.lower():
            raise ModelUnavailable("Model checksum does not match the trusted SHA-256.")
        file.seek(0)
        with warnings.catch_warnings():
            warnings.simplefilter("error", InconsistentVersionWarning)
            bundle = joblib.load(file)
    required = {"model", "title_vectorizer", "description_vectorizer"}
    if not isinstance(bundle, dict) or not required.issubset(bundle):
        raise ModelUnavailable("Model bundle is missing its classifier or fitted vectorizers.")
    if list(bundle["model"].classes_) != [0, 1]:
        raise ModelUnavailable("This adapter requires binary labels 0=different and 1=match.")
    return bundle


def load_bundle(entry=None):
    entry = entry or model_entry()
    if entry["status"] != "approved":
        raise ModelUnavailable("Experimental models cannot serve predictions until approved.")
    if entry["adapter"] not in {"tfidf_pair", "logistic_pair_v1"}:
        raise ModelUnavailable("No adapter is registered for this feature pipeline.")
    path = artifact_path(entry)
    if not path.is_file():
        raise ModelUnavailable("Trained model is not installed on this server.")
    checksum = entry.get("sha256")
    if entry["id"] == model_entry()["id"]:
        checksum = os.getenv("MODEL_SHA256", checksum)
    bundle = read_bundle(str(path), checksum, path.stat().st_mtime_ns)
    if entry["adapter"] == "logistic_pair_v1" and bundle.get("feature_columns") != FEATURE_COLUMNS:
        raise ModelUnavailable("LR feature order does not match its original training code.")
    return bundle


def capabilities(entry, bundle):
    kind = entry.get("score_type")
    model = bundle["model"]
    score = (kind == "decision_score" and hasattr(model, "decision_function")) or (
        kind == "probability" and hasattr(model, "predict_proba")
    )
    threshold = bundle.get("threshold", entry.get("default_threshold"))
    if threshold is not None:
        threshold = float(threshold)
        if not math.isfinite(threshold):
            raise ModelUnavailable("Model threshold must be finite.")
    return {
        "continuous_score": bool(score),
        "threshold": bool(score and threshold is not None),
        "probability": bool(score and kind == "probability"),
        "score_type": kind if score else None,
        "score_direction": "higher_is_match" if score else None,
        "default_threshold": threshold if score else None,
    }


def model_info(entry=None):
    entry = entry or model_entry()
    info = {key: value for key, value in entry.items() if key not in {"artifact", "sha256"}}
    try:
        bundle = load_bundle(entry)
        info.update(available=True, capabilities=capabilities(entry, bundle), message=None)
    except ModelUnavailable as exc:
        info.update(available=False, capabilities=None, message=str(exc))
    except Exception:
        info.update(available=False, capabilities=None,
                    message="Model could not be loaded. Verify its artifact and training library versions.")
    return info


def predict_pairs(pairs, model_id=None):
    entry = model_entry(model_id)
    bundle = load_bundle(entry)
    flags = capabilities(entry, bundle)
    rows = []
    for a, b in pairs:
        fields = ["title", "brand", "description"]
        if entry["adapter"] == "logistic_pair_v1":
            fields.append("category")
        rows.append({f"{field}_{side}": product.get(field, "")
                     for product, side in [(a, "left"), (b, "right")]
                     for field in fields})
    if not rows:
        return []
    frame = pd.DataFrame(rows)
    feature_builder = pair_features
    if entry["adapter"] == "logistic_pair_v1":
        # Empty website fields represent missing CSV cells, which pandas read as NaN.
        for field in ["brand", "description", "category"]:
            for side in ["left", "right"]:
                column = f"{field}_{side}"
                frame[column] = frame[column].replace("", None)
        feature_builder = logistic_features
    features = feature_builder(frame, bundle["title_vectorizer"], bundle["description_vectorizer"])
    model = bundle["model"]
    scores = None
    if flags["score_type"] == "decision_score":
        scores = np.asarray(model.decision_function(features)).reshape(-1)
    elif flags["score_type"] == "probability":
        scores = np.asarray(model.predict_proba(features))[:, 1]
    if entry["adapter"] == "logistic_pair_v1":
        labels = model.predict(features)  # Preserve the teammate's original classifier decision, including ties.
    else:
        labels = (scores >= flags["default_threshold"]).astype(int) if flags["threshold"] else model.predict(features)
    output = []
    for i, label in enumerate(labels):
        score = float(scores[i]) if scores is not None else None
        if score is not None and not math.isfinite(score):
            raise ModelUnavailable("Model produced a non-finite score.")
        if flags["probability"] and not 0 <= score <= 1:
            raise ModelUnavailable("Model probability must be between zero and one.")
        output.append({
            "is_match": bool(label), "prediction": "Match" if label else "Not a Match",
            "raw_score": score,
            "decision_score": round(score, 4) if flags["score_type"] == "decision_score" else None,
            "probability": score if flags["probability"] else None,
            "score_type": flags["score_type"], "score_direction": flags["score_direction"],
            "threshold": flags["default_threshold"], "model_id": entry["id"], "model_version": entry["version"],
        })
    return output
