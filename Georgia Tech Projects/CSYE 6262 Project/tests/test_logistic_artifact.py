"""Keep the received model intact and prevent incomplete preprocessing from serving."""
import hashlib
import unittest
from unittest.mock import patch

from website import registry
from website.main import evaluation


class LogisticArtifactTests(unittest.TestCase):
    def test_received_artifact_and_pending_status(self):
        entry = registry.model_entry('logistic_regression_v1')
        path = registry.artifact_path(entry)
        with path.open('rb') as file:
            checksum = hashlib.file_digest(file, 'sha256').hexdigest()
        self.assertEqual(checksum, 'f29f363006fa685333e4726a41508bf1f393b6992b3de451e92e74bb05efce89')
        self.assertEqual(checksum, entry['sha256'])
        self.assertEqual(entry['library_versions']['scikit-learn'], '1.9.1')
        self.assertEqual(len(entry['feature_schema']), 8)
        with patch.object(registry, 'read_bundle') as load:
            with self.assertRaises(registry.ModelUnavailable):
                registry.load_bundle(entry)
            load.assert_not_called()
        self.assertFalse(registry.model_info(entry)['available'])
        self.assertIsNone(entry['evaluation'])
        listed = next(item for item in evaluation()['models'] if item['id'] == entry['id'])
        self.assertIn('not enabled', listed['integration_note'])


if __name__ == '__main__':
    unittest.main()
