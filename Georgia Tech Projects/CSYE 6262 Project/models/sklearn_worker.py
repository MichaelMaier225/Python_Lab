"""Shared RF/LR prediction worker in their original sklearn runtime; never executes training."""
import hashlib
import json
from pathlib import Path
import sys
import warnings

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.exceptions import InconsistentVersionWarning

from models.RF.features import pair_features as rf_features
from models.logistic_regression.features import pair_features as logistic_features, FEATURE_COLUMNS
from sklearn.linear_model import LogisticRegression


def main():
    request = json.load(sys.stdin)
    if sklearn.__version__ != '1.9.1':
        raise ValueError('This worker requires scikit-learn 1.9.1.')
    path = Path(request['path'])
    with path.open('rb') as file:
        if hashlib.file_digest(file, 'sha256').hexdigest() != request['checksum']:
            raise ValueError('Model checksum mismatch.')
        file.seek(0)
        with warnings.catch_warnings():
            warnings.simplefilter('error', InconsistentVersionWarning)
            bundle = joblib.load(file)
    model = bundle['model']
    adapter = request['entry']['adapter']
    if list(model.classes_) != [0, 1]:
        raise ValueError('Expected binary labels 0=different and 1=match.')
    if adapter == 'random_forest_pair_v1':
        definitions = bundle['features']
        columns = bundle.get('feature_columns', bundle.get('feature_names'))
        if (not isinstance(model, RandomForestClassifier)
                or columns != [item[0] for item in definitions]
                or len(columns) != model.n_features_in_):
            raise ValueError('Unexpected RF model or feature schema.')
    elif adapter == 'logistic_pair_v1':
        if (not isinstance(model, LogisticRegression) or bundle.get('feature_columns') != FEATURE_COLUMNS
                or model.n_features_in_ != len(FEATURE_COLUMNS)
                or not {'title_vectorizer', 'description_vectorizer'}.issubset(bundle)):
            raise ValueError('Unexpected LR model or fitted preprocessing.')
    else:
        raise ValueError('Unsupported isolated-runtime adapter.')
    rows = request['pairs']
    if rows is None:
        print(json.dumps({'available': True}))
        return
    if not rows:
        print('[]')
        return
    fields = ['title', 'description', 'brand', 'category'] if adapter == 'logistic_pair_v1' else ['title', 'description', 'brand', 'specTableContent']
    frame = pd.DataFrame([{f'{field}_{side}': product.get(field, '')
                           for product, side in [(a, 'left'), (b, 'right')]
                           for field in fields}
                          for a, b in rows])
    if adapter == 'logistic_pair_v1':
        for field in ['brand', 'description', 'category']:
            for side in ['left', 'right']:
                frame[f'{field}_{side}'] = frame[f'{field}_{side}'].replace('', None)
        features = logistic_features(frame, bundle['title_vectorizer'], bundle['description_vectorizer'])
    else:
        features = rf_features(frame, definitions, columns)
    labels = model.predict(features)
    scores = model.predict_proba(features)[:, 1]
    entry = request['entry']
    output = []
    for label, score in zip(labels, scores):
        if not np.isfinite(score) or not 0 <= score <= 1:
            raise ValueError('Model returned an invalid probability.')
        output.append({'is_match': bool(label), 'prediction': 'Match' if label else 'Not a Match',
                       'raw_score': float(score), 'decision_score': None, 'probability': float(score),
                       'score_type': 'probability', 'score_direction': 'higher_is_match',
                       'threshold': 0.5, 'model_id': entry['id'], 'model_version': entry['version']})
    print(json.dumps(output))


if __name__ == '__main__':
    main()
