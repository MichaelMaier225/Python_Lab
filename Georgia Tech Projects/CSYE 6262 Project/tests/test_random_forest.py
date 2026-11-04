"""Check RF artifact provenance, original notebook feature parity, and actual model selection."""
import ast
import asyncio
from contextlib import closing
import hashlib
import json
import math
from pathlib import Path
import string
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

import httpx
import numpy as np
import pandas as pd

from models.RF.features import pair_features, STOP_WORDS
from models.RF.runtime import python_path
from website import database, feedback, registry
from website.main import app

ROOT = Path(__file__).resolve().parents[1]


class RandomForestTests(unittest.TestCase):
    def test_original_notebook_feature_parity(self):
        notebook = json.loads((ROOT / 'models/RF/random_forest.ipynb').read_text())
        tree = ast.parse(''.join(notebook['cells'][0]['source']))
        # Execute just original function definitions, never the training cells or imports.
        functions = ast.Module(body=[item for item in tree.body if isinstance(item, ast.FunctionDef) and item.name != 'run_magellan'], type_ignores=[])
        original = {'pd': pd, 'math': math, 'string': string}
        exec(compile(functions, '<original RF notebook functions>', 'exec'), original)
        original['TOKENIZERS'] = {'qgm_3': original['tok_qgram3'], 'dlm_dc0': original['tok_delim_space']}
        original['SIM_FUNCS'] = {name: original[name] for name in [
            'lev_dist', 'lev_sim', 'jaro_winkler', 'needleman_wunsch', 'smith_waterman',
            'jaccard', 'cosine', 'monge_elkan']}
        definitions = [('title_q', 'title', 'jaccard', 'qgm_3'),
                       ('description_cos', 'description', 'cosine', 'dlm_dc0'),
                       ('brand_edit', 'brand', 'lev_sim', None),
                       ('brand_monge', 'brand', 'monge_elkan', None),
                       ('spec_q', 'specTableContent', 'jaccard', 'qgm_3')]
        frame = pd.DataFrame([
            {'title_left': 'The Samsung &amp; Laptop!', 'title_right': 'Samsung laptop',
             'description_left': '16GB RAM 1TB', 'description_right': '8GB RAM 1TB',
             'brand_left': 'HP', 'brand_right': 'Hewlett Packard',
             'specTableContent_left': 'RAM: 16GB', 'specTableContent_right': 'RAM 8GB'},
            {'title_left': '', 'title_right': 'A computer', 'description_left': None,
             'description_right': '', 'brand_left': None, 'brand_right': '',
             'specTableContent_left': '', 'specTableContent_right': None}])
        expected = frame.copy().fillna('')
        for col in expected:
            expected[col] = expected[col].apply(original['preprocess_string'], args=(STOP_WORDS,))
            expected[col] = expected[col].replace(['nan', 'null'], '')
        columns = [item[0] for item in definitions]
        pd.testing.assert_frame_equal(pair_features(frame, definitions, columns),
                                      original['extract_feature_vecs'](expected, definitions))

    @unittest.skipUnless(python_path().is_file(), 'Install the separate RF runtime first')
    def test_received_artifact_matches_original_features_and_predictions(self):
        entry = registry.model_entry('random_forest_v1')
        path = registry.artifact_path(entry)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),
                         'b02e11e11a706573181abe41bff7f7f1c7a6f0debc8edb26d2bd1209e82e0791')
        code = '''
import ast, json, math, string
import joblib, pandas as pd
from pathlib import Path
from models.RF.features import STOP_WORDS
nb=json.loads(Path('models/RF/random_forest.ipynb').read_text())
ns={'pd':pd,'math':math,'string':string}
tree=ast.parse(''.join(nb['cells'][0]['source']))
exec(compile(ast.Module(body=[x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name != "run_magellan"],type_ignores=[]),'<notebook>','exec'),ns)
ns['TOKENIZERS']={x:ns[y] for x,y in [('qgm_3','tok_qgram3'),('dlm_dc0','tok_delim_space')]}
ns['SIM_FUNCS']={x:ns[x] for x in ['lev_dist','lev_sim','jaro_winkler','needleman_wunsch','smith_waterman','jaccard','cosine','monge_elkan']}
b=joblib.load('trained_models/RF/random_forest_v1.joblib')
products=[{'title':'Samsung laptop 16GB','brand':'Samsung','description':'computer','specTableContent':'16GB RAM'},
          {'title':'HP printer','brand':'HP','description':'laser printer','specTableContent':''}]
pairs=[(products[0],products[0]),(products[0],products[1]),({},products[1])]
f=pd.DataFrame([{field+'_'+side:product.get(field,'') for product,side in [(a,'left'),(c,'right')] for field in ['title','description','brand','specTableContent']} for a,c in pairs])
for col in f:
 f[col]=f[col].apply(ns['preprocess_string'],args=(STOP_WORDS,)).replace(['nan','null'],'')
X=ns['extract_feature_vecs'](f,b['features'])[b['feature_columns']]
print(json.dumps({'pairs':pairs,'scores':b['model'].predict_proba(X)[:,1].tolist(),'labels':b['model'].predict(X).tolist()}))
'''
        expected = json.loads(subprocess.check_output([str(python_path()), '-c', code], cwd=ROOT, text=True))
        actual = registry.predict_pairs(expected['pairs'], entry['id'])
        np.testing.assert_allclose([x['raw_score'] for x in actual], expected['scores'], rtol=0, atol=1e-14)
        self.assertEqual([x['is_match'] for x in actual], [bool(x) for x in expected['labels']])

    @unittest.skipUnless(python_path().is_file(), 'Install the separate RF runtime first')
    def test_actual_api_selection_candidates_batch_and_feedback(self):
        async def request(method, path, body=None):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
                response = await client.request(method, path, json=body)
                self.assertEqual(response.status_code, 200, response.text)
                return response.json()
        def call(method, path, body=None):
            return asyncio.run(request(method, path, body))
        a = {'title': 'Samsung laptop 16GB', 'brand': 'Samsung', 'description': 'computer'}
        b = {'title': 'Samsung laptop 8GB', 'brand': 'Samsung', 'description': 'computer'}
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(database, 'DB_PATH', Path(temporary) / 'products.db'), patch.object(feedback, 'DB_PATH', Path(temporary) / 'feedback.db'):
                with closing(database.connect()) as conn, conn:
                    database.initialize(conn)
                    for product in [a, b]:
                        conn.execute('INSERT INTO products(title, brand, description) VALUES (?, ?, ?)', tuple(product.values()))
                for model_id, kind, threshold in [('linear_svc_v3', 'decision_score', -0.25), ('random_forest_v1', 'probability', 0.5), ('logistic_regression_v1', 'probability', 0.5)]:
                    body = {'product_a': a, 'product_b': b, 'model_id': model_id}
                    result = call('POST', '/predict', body)
                    self.assertEqual(result['model_id'], model_id)
                    self.assertEqual(result['score_type'], kind)
                    self.assertEqual(result['threshold'], threshold)
                    candidates = call('GET', f'/candidates/1?model_id={model_id}')
                    self.assertEqual(candidates['candidates'][0]['prediction']['model_id'], model_id)
                    batch = call('POST', '/predict/batch', {'model_id': model_id, 'pairs': [body]})
                    self.assertAlmostEqual(batch['results'][0]['raw_score'], result['raw_score'], places=12)
                    saved = call('POST', '/feedback', dict(body, model_version=result['model_version'], request_id=str(uuid4()), choice='unsure'))
                    self.assertTrue(saved['saved'])
                with closing(database.connect()) as conn:
                    # Feedback uses a different file, never the catalog database.
                    self.assertEqual(conn.execute('SELECT COUNT(*) FROM products').fetchone()[0], 2)
                import sqlite3
                with closing(sqlite3.connect(Path(temporary) / 'feedback.db')) as conn:
                    self.assertEqual({x[0] for x in conn.execute('SELECT model_id FROM feedback')}, {'linear_svc_v3', 'random_forest_v1', 'logistic_regression_v1'})
