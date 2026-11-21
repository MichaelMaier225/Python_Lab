import unittest

import numpy as np
import pandas as pd

from models.svm.features_v4 import pair_features as v4_features
from models.svm.features_v5 import SCHEMA, pair_features
from models.svm.scoring import decision_scores
from models.svm.train import fit_model, make_vectorizers


class SVMV5Tests(unittest.TestCase):
    def setUp(self):
        self.frame = pd.DataFrame({
            "title_left": ["AppleCare+ for 13-inch MacBook Pro"] * 5,
            "title_right": [
                "AppleCare+ for 15-inch MacBook Pro",
                "AppleCare+ for 13 inch MacBook Pro",
                "AppleCare+ for MacBook Pro",
                "AppleCare+ for 13-inch MacBook Air",
                "Cover for 15-inch MacBook Pro or 13-inch Pro",
            ],
            "label": [0, 1, 1, 0, 1],
        })

    def test_compatibility_feature_is_symmetric_and_keeps_v4_columns(self):
        title, description = make_vectorizers(self.frame)
        base = v4_features(self.frame, title, description)
        features = pair_features(self.frame, title, description)
        reverse = self.frame.rename(columns={"title_left": "title_right", "title_right": "title_left"})
        np.testing.assert_array_equal(features[:, -1].toarray().ravel(), [1, 0, 0, 0, 0])
        np.testing.assert_array_equal(features[:, :-1].toarray(), base.toarray())
        np.testing.assert_array_equal(features.toarray(), pair_features(reverse, title, description).toarray())

    def test_fitted_model_scores_with_the_v5_schema(self):
        train = self.frame.iloc[:3]
        valid = self.frame.iloc[3:]
        model, title, description, settings = fit_model(
            train, valid, feature_builder=pair_features, feature_schema=SCHEMA,
        )
        self.assertEqual(settings["feature_schema"], SCHEMA)
        self.assertNotEqual(model.coef_[0, -1], 0)
        expected = model.decision_function(pair_features(valid, title, description))
        scores = decision_scores(model, title, description, valid, batch_size=1, feature_schema=SCHEMA)
        np.testing.assert_allclose(scores, expected)
