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


class Response(io.BytesIO):
    url = 'https://example.com/test-artifact'


class AssetTests(unittest.TestCase):
    def test_verified_download_and_repeat(self):
        content = b'trusted fixture, not an executable model'
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'models' / 'fixture.joblib'
            values = {'MODEL_URL': 'https://example.com/model', 'MODEL_SHA256': hashlib.sha256(content).hexdigest()}
            with patch.dict(os.environ, values), patch.object(prepare_assets, 'urlopen', return_value=Response(content)) as fetch:
                prepare_assets.download('MODEL', target)
                self.assertEqual(target.read_bytes(), content)
                prepare_assets.download('MODEL', target)
                self.assertEqual(fetch.call_count, 1)

    def test_hash_failure_preserves_existing_file(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'model.joblib'
            target.write_bytes(b'original')
            with patch.dict(os.environ, {'MODEL_URL': 'https://example.com/model', 'MODEL_SHA256': '0'*64}), \
                 patch.object(prepare_assets, 'urlopen', return_value=Response(b'wrong content')):
                with self.assertRaises(ValueError): prepare_assets.download('MODEL', target)
            self.assertEqual(target.read_bytes(), b'original')
            self.assertEqual(list(Path(folder).iterdir()), [target])

    def test_http_and_missing_checksum_rejected(self):
        with patch.dict(os.environ, {'MODEL_URL': 'http://example.com/model', 'MODEL_SHA256': '0'*64}):
            with self.assertRaises(ValueError): prepare_assets.download('MODEL', Path('/unused'))
        with patch.dict(os.environ, {'MODEL_URL': 'https://example.com/model', 'MODEL_SHA256': ''}):
            with self.assertRaises(ValueError): prepare_assets.download('MODEL', Path('/unused'))

    def test_database_download_schema(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'source.db'
            with closing(sqlite3.connect(source)) as conn, conn:
                conn.execute('CREATE TABLE products (id INTEGER, title TEXT)')
                conn.execute('CREATE VIRTUAL TABLE product_search USING fts5(title)')
            content = source.read_bytes()
            target = Path(folder) / 'data' / 'products.db'
            values = {'DATABASE_URL': 'https://example.com/products.db', 'DATABASE_SHA256': hashlib.sha256(content).hexdigest()}
            with patch.dict(os.environ, values), patch.object(prepare_assets, 'urlopen', return_value=Response(content)):
                prepare_assets.download('DATABASE', target)
            self.assertEqual(target.read_bytes(), content)


if __name__ == '__main__': unittest.main()
