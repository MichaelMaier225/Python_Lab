"""Identity regressions and exact train/serve parity for the new schema."""
import unittest

import numpy as np
import pandas as pd

from models.svm.features_v4 import identity, pair_features, SCHEMA
from models.svm.scoring import decision_scores
from models.svm.train import fit_model, make_vectorizers
from website import registry
from unittest.mock import patch


class SVMV4Tests(unittest.TestCase):
    def test_single_digits_and_capacity_are_not_lost_or_models(self):
        frame = pd.DataFrame({'title_left':['iphone 5 32gb black'], 'title_right':['iphone 4 32gb black']})
        tv, _ = make_vectorizers(frame)
        self.assertIn('5', tv.build_analyzer()('iphone 5'))
        self.assertGreater((tv.transform(['iphone 5']) != tv.transform(['iphone 4'])).nnz, 0)
        self.assertEqual(identity('iphone 5 32gb black')[0], {'iphone5'})
        self.assertEqual(identity('iphone se 32 gb black')[0], {'iphonese'})
        self.assertEqual(identity('iphone 4s 32gb')[0], identity('iphone4s 32 gb')[0])
        self.assertEqual(identity('iphone 5 32gb black')[1], identity('iphone 5 32 gb black')[1])
        self.assertEqual(identity('iphone 5 phone case')[3], 'case')
        self.assertEqual(identity('iphone 5 32gb black')[3], 'phone')
        self.assertIsNone(identity('generic listing')[3])
        self.assertIsNone(identity('iphone bag and case bundle')[3])

    def test_conflict_features_symmetry_and_missing_information(self):
        frame = pd.DataFrame({'title_left':['iphone 5 32gb black', ''],
                              'title_right':['iphone 4 64gb white', 'iphone 4']})
        tv, dv = make_vectorizers(frame)
        features = pair_features(frame, tv, dv)
        reverse = frame.rename(columns={'title_left':'title_right','title_right':'title_left'})
        np.testing.assert_allclose(features.toarray(), pair_features(reverse, tv, dv).toarray())
        identity_features = features.toarray()[:, -15:]
        self.assertEqual(identity_features[0, 2], 1)  # model conflict
        self.assertEqual(identity_features[0, 6], 1)  # capacity conflict
        self.assertEqual(identity_features[0, 10], 1)  # color conflict
        self.assertEqual(identity_features[1, 2], 0)  # missing is not a contradiction

    def test_actual_trainer_evaluator_and_website_use_identical_features(self):
        train = pd.DataFrame({'title_left':['camera 4','camera 4','laptop 8','laptop 8'],
                              'title_right':['camera 4','shoe 9','laptop 8','watch 3'],
                              'label':[1,0,1,0]})
        model, tv, dv, settings = fit_model(train, train.copy())
        bundle = {'model':model,'title_vectorizer':tv,'description_vectorizer':dv, **settings}
        entry = {'id':'v4-fixture','version':'test','adapter':SCHEMA,'score_type':'decision_score','default_threshold':settings['threshold']}
        pairs = [({'title':a},{'title':b}) for a,b in zip(train.title_left,train.title_right)]
        with patch.object(registry,'model_entry',return_value=entry), patch.object(registry,'load_bundle',return_value=bundle):
            served = registry.predict_pairs(pairs)
        scores = decision_scores(model,tv,dv,train,feature_schema=SCHEMA)
        np.testing.assert_allclose([x['raw_score'] for x in served],scores,rtol=1e-12)
        self.assertEqual([x['is_match'] for x in served],(scores >= settings['threshold']).tolist())
