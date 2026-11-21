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



class SavedProbabilityEvaluationTests(unittest.TestCase):
    def test_uses_saved_classifier_labels_and_preserves_specifications(self):
        # At p=0.5, the original binary classifiers choose class 0.
        frame = pd.DataFrame({'pair_id':['1#2','3#4'], 'label':[0,1],
                              'title_left':['phone case','camera'], 'title_right':['phone','camera'],
                              'specTableContent_left':['16GB RAM',None]})
        entry = {'id':'fixture-lr','version':'1','adapter':'logistic_pair_v1',
                 'sha256':'fixture-hash','default_threshold':0.5}
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder) / 'gold.json.gz'
            frame.to_json(data,orient='records',lines=True,compression='gzip')
            with patch.object(evaluate_model,'model_entry',return_value=entry), \
                 patch.object(evaluate_model,'load_bundle') as load, \
                 patch.object(evaluate_model,'predict_pairs',return_value=[
                     {'raw_score':0.5,'is_match':False},{'raw_score':0.8,'is_match':True}]) as predict:
                result, details = evaluate_model.evaluate(data)
        self.assertEqual(result['confusion_matrix'],[[1,0],[0,1]])
        self.assertEqual(details['prediction'].tolist(),[0,1])
        self.assertIn('probability', details)
        self.assertEqual(predict.call_args.args[0][0][0]['specTableContent'],'16GB RAM')
        load.assert_not_called()

    def test_reversed_training_pair_is_excluded_without_changing_sources(self):
        import gzip
        import zipfile
        frame = pd.DataFrame({'pair_id':['1#2','3#4','5#6'], 'label':[0,0,1],
                              'title_left':['a','b','c'], 'title_right':['d','e','c']})
        entry = {'id':'fixture-rf','version':'1','adapter':'random_forest_pair_v1',
                 'sha256':'fixture-hash','default_threshold':0.5}
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            data = root/'gold.json.gz';frame.to_json(data,orient='records',lines=True,compression='gzip')
            archive = root/'computers_train.zip'
            with zipfile.ZipFile(archive,'w') as zipped:
                zipped.writestr('computers_train_xlarge.json.gz',gzip.compress(
                    pd.DataFrame({'pair_id':['2#1']}).to_json(orient='records',lines=True).encode()))
            original = data.read_bytes(), archive.read_bytes()
            with patch.object(evaluate_model,'model_entry',return_value=entry), \
                 patch.object(evaluate_model,'predict_pairs',return_value=[
                     {'raw_score':0.1,'is_match':False},{'raw_score':0.9,'is_match':True}]):
                result, details = evaluate_model.evaluate(data,exclude_training=archive)
            self.assertEqual(result['pair_count'],2)
            self.assertEqual(result['overlap_audit']['excluded_pairs'],1)
            self.assertEqual(details.pair_id.tolist(),['3#4','5#6'])
            self.assertEqual((data.read_bytes(),archive.read_bytes()),original)


if __name__ == "__main__":
    unittest.main()
