"""JSON-only prediction worker; never import or execute the training notebook."""
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

from .features import pair_features


def main():
    request = json.load(sys.stdin)
    if sklearn.__version__ != '1.9.1':
        raise ValueError('RF requires scikit-learn 1.9.1.')
    path = Path(request['path'])
    with path.open('rb') as file:
        if hashlib.file_digest(file, 'sha256').hexdigest() != request['checksum']:
            raise ValueError('RF checksum mismatch.')
        file.seek(0)
        with warnings.catch_warnings():
            warnings.simplefilter('error', InconsistentVersionWarning)
            bundle = joblib.load(file)
    model = bundle['model']
    definitions = bundle['features']
    # The received artifact uses feature_columns; the notebook's save cell says feature_names.
    columns = bundle.get('feature_columns', bundle.get('feature_names'))
    if (not isinstance(model, RandomForestClassifier) or list(model.classes_) != [0, 1]
            or columns != [item[0] for item in definitions]
            or len(columns) != model.n_features_in_):
        raise ValueError('Unexpected RF model or feature schema.')
    rows = request['pairs']
    if rows is None:
        print(json.dumps({'available': True}))
        return
    if not rows:
        print('[]')
        return
    frame = pd.DataFrame([{f'{field}_{side}': product.get(field, '')
                           for product, side in [(a, 'left'), (b, 'right')]
                           for field in ['title', 'description', 'brand', 'specTableContent']}
                          for a, b in rows])
    features = pair_features(frame, definitions, columns)
    labels = model.predict(features)
    scores = model.predict_proba(features)[:, 1]
    entry = request['entry']
    output = []
    for label, score in zip(labels, scores):
        if not np.isfinite(score) or not 0 <= score <= 1:
            raise ValueError('RF returned an invalid probability.')
        output.append({'is_match': bool(label), 'prediction': 'Match' if label else 'Not a Match',
                       'raw_score': float(score), 'decision_score': None, 'probability': float(score),
                       'score_type': 'probability', 'score_direction': 'higher_is_match',
                       'threshold': 0.5, 'model_id': entry['id'], 'model_version': entry['version']})
    print(json.dumps(output))


if __name__ == '__main__':
    main()
