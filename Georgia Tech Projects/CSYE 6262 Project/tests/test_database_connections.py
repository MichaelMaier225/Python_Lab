"""Verify file handles close explicitly, including errors and early returns."""
from contextlib import closing
import hashlib
import io
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import prepare_assets
from website import database, feedback


class Response(io.BytesIO):
    url = 'https://example.com/products.db'


class ConnectionTests(unittest.TestCase):
    def assert_closed(self, connections):
        self.assertTrue(connections)
        for conn in connections:
            with self.assertRaises(sqlite3.ProgrammingError):
                conn.execute('SELECT 1')

    def test_product_queries_close_connections(self):
        connections = []
        original = database.connect
        def tracked():
            conn = original()
            connections.append(conn)
            return conn
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(database, 'DB_PATH', Path(folder) / 'products.db'), \
                 patch.object(database, 'connect', side_effect=tracked):
                self.assertEqual(database.count_products(), 0)
                self.assertEqual(database.search_products('Samsung'), [])
                self.assertIsNone(database.get_product(1))
                self.assertEqual(database.candidates({'id':1,'title':'Samsung'}), [])
                self.assert_closed(connections)

    def test_feedback_closes_on_success_duplicate_and_error(self):
        connections = []
        original = sqlite3.connect
        def tracked(*args, **kwargs):
            conn = original(*args, **kwargs)
            connections.append(conn)
            return conn
        prediction = {'model_id':'fixture','model_version':'1','is_match':True,'raw_score':1.0}
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(feedback, 'DB_PATH', Path(folder) / 'products.db'), \
                 patch.object(feedback.sqlite3, 'connect', side_effect=tracked):
                feedback.save_feedback({'title':'a'}, {'title':'b'}, prediction, 'unsure', 'test-request')
                self.assertTrue(feedback.save_feedback({'title':'a'}, {'title':'b'}, prediction, 'unsure', 'test-request')['duplicate'])
                with self.assertRaises(ValueError):
                    feedback.save_feedback({'title':'a'}, {'title':'b'}, prediction, 'match', 'test-request')
                self.assert_closed(connections)

    def test_asset_validation_closes_before_replace(self):
        connections = []
        original = sqlite3.connect
        def tracked(*args, **kwargs):
            conn = original(*args, **kwargs)
            connections.append(conn)
            return conn
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'source.db'
            with closing(original(source)) as conn, conn:
                conn.execute('CREATE TABLE products (id INTEGER, title TEXT)')
                conn.execute('CREATE VIRTUAL TABLE product_search USING fts5(title)')
            content = source.read_bytes()
            target = Path(folder) / 'products.db'
            replace = Path.replace
            def checked_replace(path, destination):
                self.assert_closed(connections)
                return replace(path, destination)
            env = {'DATABASE_URL':'https://example.com/products.db', 'DATABASE_SHA256':hashlib.sha256(content).hexdigest()}
            with patch.dict(os.environ, env), \
                 patch.object(prepare_assets, 'urlopen', return_value=Response(content)), \
                 patch.object(prepare_assets.sqlite3, 'connect', side_effect=tracked), \
                 patch.object(Path, 'replace', checked_replace):
                prepare_assets.download('DATABASE', target)
            self.assertEqual(target.read_bytes(), content)


if __name__ == '__main__':
    unittest.main()
