"""Synthetic fixtures validate software behavior, not real-world model accuracy."""

from contextlib import closing
import asyncio
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
import joblib
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC

from website import database, feedback, registry
from website.attributes import compare_attributes
from website.main import app
from models.svm.features import pair_features


class ProductMatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.environment = patch.dict(os.environ, {'PRODUCTMATCH_MODEL_DIR': str(self.root), 'ACTIVE_MODEL': 'fixture'})
        self.environment.start()
        self.old_checksum = os.environ.pop('MODEL_SHA256', None)
        self.db_patch = patch.object(database, 'DB_PATH', self.root / 'products.db')
        self.feedback_patch = patch.object(feedback, 'DB_PATH', self.root / 'products.db')
        self.registry_patch = patch.object(registry, 'REGISTRY_PATH', self.root / 'registry.json')
        for p in [self.db_patch, self.feedback_patch, self.registry_patch]: p.start()
        self.a = {'title': 'Samsung 990 1TB SSD', 'brand': 'Samsung', 'description': 'Fast drive', 'price': 100, 'currency': 'USD'}
        self.b = {'title': 'Samsung 990 SSD', 'brand': 'Samsung', 'description': 'Fast drive', 'price': 90, 'currency': 'USD'}
        self.c = {'title': 'Lenovo laptop', 'brand': 'Lenovo', 'description': 'Portable computer', 'price': 500, 'currency': 'EUR'}
        self.pairs = [(self.a, self.b), (self.a, self.c), (self.c, self.c), (self.b, self.c)]
        rows = [{f'{field}_{side}': product[field]
                 for product, side in [(a,'left'),(b,'right')]
                 for field in ['title','brand','description']} for a,b in self.pairs]
        self.frame = pd.DataFrame(rows)
        self.tv = TfidfVectorizer(ngram_range=(1,2)).fit([p['title'] for p in [self.a,self.b,self.c]])
        self.dv = TfidfVectorizer().fit([p['description'] for p in [self.a,self.b,self.c]])
        self.features = pair_features(self.frame, self.tv, self.dv)
        self.estimator = LinearSVC(random_state=42).fit(self.features, [1,0,1,0])
        self.install(self.estimator, 'decision_score', 0.25)
        with closing(database.connect()) as conn, conn:
            database.initialize(conn)
            for i,p in enumerate([self.a,self.b,self.c],1):
                conn.execute('INSERT INTO products (id, source_id, title, brand, description, price, currency, seller) VALUES (?,?,?,?,?,?,?,?)',
                             (i,str(i),p['title'],p['brand'],p['description'],p['price'],p['currency'],f'vendor {i}'))
            conn.commit()

    def tearDown(self):
        registry.read_bundle.cache_clear()
        for p in [self.db_patch,self.feedback_patch,self.registry_patch]: p.stop()
        self.environment.stop()
        if self.old_checksum is not None: os.environ['MODEL_SHA256'] = self.old_checksum
        self.temp.cleanup()

    def install(self, estimator, kind, threshold):
        path = self.root / 'fixture.joblib'
        bundle = {'model':estimator,'title_vectorizer':self.tv,'description_vectorizer':self.dv}
        if threshold is not None: bundle['threshold'] = threshold
        joblib.dump(bundle,path)
        self.entry = {'id':'fixture','name':'Test fixture','version':'test-only','algorithm':type(estimator).__name__,
                      'status':'approved','adapter':'tfidf_pair','artifact':path.name,
                      'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'score_type':kind,'evaluation':None}
        (self.root / 'registry.json').write_text(json.dumps({'default_model':'fixture','models':[self.entry]}))
        registry.read_bundle.cache_clear()

    def request(self, method, path, body=None):
        async def run():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
                return await client.request(method,path,json=body)
        return asyncio.run(run())

    def test_frozen_feature_regression_and_symmetry(self):
        expected = np.asarray(json.loads((Path(__file__).parent / 'fixtures' / 'svm_features.json').read_text()))
        np.testing.assert_allclose(self.features.toarray(),expected,rtol=1e-12,atol=1e-12)
        reversed_frame = self.frame.rename(columns={f'{field}_{side}':f'{field}_{other}'
            for field in ['title','brand','description'] for side,other in [('left','right'),('right','left')]})
        np.testing.assert_allclose(pair_features(reversed_frame,self.tv,self.dv).toarray(),expected)

    def test_baseline_prediction_parity_and_batch(self):
        expected = self.estimator.decision_function(self.features)
        results = registry.predict_pairs(self.pairs)
        for score,result in zip(expected,results):
            self.assertAlmostEqual(result['raw_score'],score,places=12)
            self.assertEqual(result['decision_score'],round(float(score),4))
            self.assertEqual(result['is_match'],bool(score>=0.25))
            self.assertIsNone(result['probability'])
        body={'pairs':[{'product_a':a,'product_b':b} for a,b in self.pairs]}
        response=self.request('POST','/predict/batch',body)
        self.assertEqual(response.status_code,200)
        self.assertEqual(len(response.json()['results']),4)

    def test_probability_adapter(self):
        model=LogisticRegression().fit(self.features,[1,0,1,0])
        self.install(model,'probability',0.5)
        result=registry.predict_pairs([self.pairs[0]])[0]
        self.assertAlmostEqual(result['probability'],model.predict_proba(self.features[:1])[0,1])
        self.assertIsNone(result['decision_score'])

    def test_label_only_adapter(self):
        model=DummyClassifier(strategy='most_frequent').fit(self.features,[1,0,1,0])
        self.install(model,None,None)
        info=registry.model_info()
        self.assertFalse(info['capabilities']['continuous_score'])
        result=registry.predict_pairs([self.pairs[0]])[0]
        self.assertIsNone(result['raw_score'])
        self.assertIsNone(result['threshold'])

    def test_checksum_approval_and_path_validation(self):
        entry=dict(self.entry,sha256='0'*64)
        with self.assertRaises(registry.ModelUnavailable): registry.load_bundle(entry)
        with self.assertRaises(registry.ModelUnavailable): registry.load_bundle(dict(self.entry,status='experimental'))
        with self.assertRaises(registry.ModelUnavailable): registry.artifact_path(dict(self.entry,artifact='../outside.joblib'))
        with self.assertRaises(registry.ModelUnavailable): registry.model_entry('unknown')

    def test_search_and_candidates(self):
        response=self.request('GET','/search?q=Samsung')
        self.assertEqual(response.json()['count'],2)
        data=self.request('GET','/candidates/1').json()
        self.assertEqual([i['product']['id'] for i in data['candidates']],[2])
        self.assertIsNotNone(data['candidates'][0]['prediction'])
        self.assertEqual(self.request('GET','/candidates/999').status_code,404)
        self.assertEqual(self.request('GET','/search?q=%22%20OR%20%2A').status_code,200)

    def test_missing_model_preserves_candidate_retrieval(self):
        (self.root/'fixture.joblib').unlink()
        response=self.request('GET','/candidates/1')
        self.assertEqual(response.status_code,200)
        self.assertFalse(response.json()['model']['available'])
        self.assertIsNone(response.json()['candidates'][0]['prediction'])
        self.assertEqual(self.request('GET','/health').status_code,503)
        self.assertEqual(self.request('GET','/live').status_code,200)
        self.assertEqual(self.request('POST','/predict',{'product_a':self.a,'product_b':self.b}).status_code,503)

    def test_validation_and_limits(self):
        body={'product_a':dict(self.a,title='   '),'product_b':self.b}
        self.assertEqual(self.request('POST','/predict',body).status_code,422)
        body={'pairs':[{'product_a':self.a,'product_b':self.b}]*51}
        self.assertEqual(self.request('POST','/predict/batch',body).status_code,422)
        self.assertEqual(self.request('GET','/search?q=x').status_code,422)
        self.assertEqual(self.request('GET','/candidates/1?limit=51').status_code,422)
        body={'product_a':dict(self.a,price=-1),'product_b':self.b}
        self.assertEqual(self.request('POST','/predict',body).status_code,422)

    def test_currency_safe_price_comparison(self):
        pair={'product_a':self.a,'product_b':self.a}
        result=self.request('POST','/predict',pair).json()
        self.assertIn('price_comparison',result)
        pair['product_b']=dict(self.a,currency='EUR')
        self.assertNotIn('price_comparison',self.request('POST','/predict',pair).json())
        pair['product_b']=dict(self.a,price=None)
        self.assertNotIn('price_comparison',self.request('POST','/predict',pair).json())

    def test_attributes_and_missing_values(self):
        a={'brand':'SAMSUNG','title':'model: AB-123 16GB RAM 1TB SSD color: grey'}
        b={'brand':'Samsung','title':'model: AB123 8GB RAM 1000GB SSD color: gray'}
        rows={r['attribute']:r for r in compare_attributes(a,b)}
        self.assertEqual(rows['Brand']['status'],'match')
        self.assertEqual(rows['Model']['status'],'match')
        self.assertEqual(rows['RAM']['status'],'conflict')
        self.assertEqual(rows['Storage']['status'],'match')
        self.assertEqual(rows['Color']['status'],'match')
        self.assertTrue(all(r['status']=='unknown' for r in compare_attributes({'title':'1TB'},{'title':'1TB'})))
        self.assertEqual(self.request('POST','/compare',{'product_a':self.a,'product_b':self.b}).status_code,200)

    def test_feedback_idempotency_and_persistence(self):
        body={'product_a':self.a,'product_b':self.b,'choice':'unsure','request_id':'a95c96e1-2a6a-4b3e-83ca-56cfaabda101',
              'model_id':'fixture','model_version':'test-only'}
        response=self.request('POST','/feedback',body)
        self.assertEqual(response.status_code,200)
        self.assertFalse(response.json()['duplicate'])
        self.assertTrue(self.request('POST','/feedback',body).json()['duplicate'])
        self.assertEqual(self.request('POST','/feedback',dict(body,choice='match')).status_code,409)
        self.assertEqual(self.request('POST','/feedback',dict(body,model_version='old')).status_code,409)
        import sqlite3
        with closing(sqlite3.connect(self.root/'feedback.db')) as conn, conn:
            row=conn.execute('SELECT model_id,model_version,record FROM feedback').fetchone()
            self.assertEqual(row[:2],('fixture','test-only'))
            self.assertEqual(json.loads(row[2])['prediction']['model_id'],'fixture')
        self.assertEqual(feedback.pair_id(self.a,self.b),feedback.pair_id(self.b,self.a))

    def test_evaluation_and_assets(self):
        self.assertIsNone(self.request('GET','/evaluation').json()['models'][0]['evaluation'])
        for path in ['/','/static/style.css','/static/script.js','/static/charts.js','/static/vendor/d3.v5.min.js']:
            self.assertEqual(self.request('GET',path).status_code,200,path)


if __name__=='__main__': unittest.main()
