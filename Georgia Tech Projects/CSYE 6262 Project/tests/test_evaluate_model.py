import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

from scripts import evaluate_model


class EvaluationTests(unittest.TestCase):
    def test_metrics_use_saved_threshold_without_fitting(self):
        frame = pd.DataFrame({'pair_id':['a','b','c'], 'label':[0,1,0],
                              'title_left':['alpha']*3, 'title_right':['beta']*3})
        classifier = Mock(spec=['decision_function','fit'])
        classifier.decision_function.return_value = np.array([-1.0,1.0,-0.2])
        title = TfidfVectorizer().fit(['alpha beta'])
        description = TfidfVectorizer().fit(['placeholder'])
        bundle = {'model':classifier, 'threshold':-0.25,
                  'title_vectorizer':title, 'description_vectorizer':description}
        entry = {'id':'fixture','version':'1','adapter':'tfidf_pair',
                 'score_type':'decision_score','sha256':'fixture-hash'}
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder) / 'labeled.json.gz'
            frame.to_json(data,orient='records',lines=True,compression='gzip')
            with patch.object(evaluate_model,'model_entry',return_value=entry), \
                 patch.object(evaluate_model,'load_bundle',return_value=bundle):
                result,details = evaluate_model.evaluate(data)
        self.assertEqual(result['confusion_matrix'],[[1,1],[0,1]])
        self.assertEqual(result['metrics']['precision'],0.5)
        self.assertEqual(result['metrics']['recall'],1.0)
        self.assertAlmostEqual(result['metrics']['f1'],2/3)
        self.assertAlmostEqual(result['metrics']['accuracy'],2/3)
        self.assertEqual(details['prediction'].tolist(),[0,1,1])
        classifier.fit.assert_not_called()
        self.assertEqual(bundle['threshold'],-0.25)

    def test_pending_adapter_cannot_be_evaluated(self):
        with patch.object(evaluate_model,'model_entry',return_value={'adapter':None}), \
             patch.object(evaluate_model,'load_bundle') as load:
            with self.assertRaises(ValueError):
                evaluate_model.evaluate(Path('unused'))
            load.assert_not_called()


if __name__ == '__main__':
    unittest.main()
