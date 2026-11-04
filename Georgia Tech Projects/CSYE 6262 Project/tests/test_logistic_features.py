"""Compare the serving adapter with the original source without executing training."""
import ast
import hashlib
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
from sklearn import __version__ as sklearn_version
from sklearn.feature_extraction.text import TfidfVectorizer

from models.logistic_regression import features
from website import registry

SOURCE = Path(__file__).resolve().parents[1] / 'models' / 'logistic_regression' / 'train.py'


def original_features(frame, title, description):
    source = SOURCE.read_text()
    helpers = [n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef)]
    namespace = {'pd':pd, 'np':np}
    exec(compile(ast.Module(body=helpers,type_ignores=[]),str(SOURCE),'exec'),namespace)
    namespace.update(test_df=frame.copy(), title_vectorizer=title,
                     description_vectorizer=description, feature_columns=features.FEATURE_COLUMNS)
    # These are the teammate's exact test-feature statements, not its fit/load steps.
    start = source.index('# %% Test - Title Similarity')
    end = source.index('predictions = model.predict(X_test)',start)
    exec(compile(source[start:end],str(SOURCE),'exec'),namespace)
    return namespace['X_test']


class LogisticFeatureTests(unittest.TestCase):
    def frame(self):
        return pd.DataFrame({
            'title_left':['Samsung 001 SSD', 'alpha', 'unknown', 'empty'],
            'title_right':['Samsung 1 SSD', 'beta', 'unknown', 'empty'],
            'description_left':['001 1TB x100', None, '', '  '],
            'description_right':['1 2TB x100', 'detail 003', None, '  '],
            'brand_left':[' Samsung ', None, '', 'Brand'],
            'brand_right':['samsung', 'Other', '', 'Other'],
            'category_left':['Computers', None, '', 'Camera'],
            'category_right':['Computers', None, '', 'Shoes'], 'label':[1,0,0,0]})

    def test_exact_original_feature_semantics(self):
        frame = self.frame()
        title = TfidfVectorizer().fit(['Samsung SSD unknown empty alpha beta'])
        desc = TfidfVectorizer().fit(['001 1TB 2TB x100 detail 003'])
        expected = original_features(frame,title,desc)
        actual = features.pair_features(frame,title,desc)
        pd.testing.assert_frame_equal(actual,expected)
        self.assertEqual(actual['description_available'].tolist(),[1,0,0,1])
        self.assertEqual(actual['brand_available'].tolist(),[1,0,1,1])
        self.assertEqual(features.extract_numeric_tokens('001 002GB X100'),(['1'],['2gb','x100']))

    def test_source_has_only_documented_path_changes(self):
        source = SOURCE.read_text().replace('pd.read_csv(Path(__file__).resolve().parents[2] / "data" / "Computers_XL_Training.csv")','pd.read_csv("Computers_XL_Training.csv")')
        source = source.replace('pd.read_excel(Path(__file__).resolve().parents[2] / "data" / "Gold_Standard.xlsx")','pd.read_excel("Gold_Standard.xlsx")')
        # Normalize line endings so this guard also works on Windows checkouts.
        expected_hash = '87cce5895a0ab19b13646d4e35bf45db1fdaa0f37045ea54d2ee2a15d30418a9'
        self.assertEqual(hashlib.sha256(source.encode()).hexdigest(),expected_hash)

    @unittest.skipUnless(sklearn_version=='1.9.1','Original LR needs its matching sklearn 1.9.1 runtime')
    def test_original_artifact_predictions_match_original_code(self):
        entry = dict(registry.model_entry('logistic_regression_v1'),status='approved')
        bundle = registry.load_bundle(entry)
        frame = self.frame()
        model = bundle['model']
        pairs = []
        for row in frame.to_dict('records'):
            pair = tuple({field:row[f'{field}_{side}'] for field in ['title','brand','description','category']} for side in ['left','right'])
            # Website blanks represent missing CSV values. Align that boundary before comparing.
            pairs.append(pair)
        website_frame=frame.copy()
        for field in ['description','brand','category']:
            for side in ['left','right']:
                col=f'{field}_{side}'
                website_frame[col]=website_frame[col].replace('',None)
        expected=original_features(website_frame,bundle['title_vectorizer'],bundle['description_vectorizer'])
        with patch.object(registry,'model_entry',return_value=entry):
            actual=registry.predict_pairs(pairs,'logistic_regression_v1')
        np.testing.assert_allclose([r['probability'] for r in actual],model.predict_proba(expected)[:,1],rtol=0,atol=0)
        self.assertEqual([r['is_match'] for r in actual],model.predict(expected).astype(bool).tolist())
        self.assertTrue(all(r['decision_score'] is None for r in actual))
        self.assertEqual(bundle['feature_columns'],features.FEATURE_COLUMNS)


if __name__=='__main__': unittest.main()
