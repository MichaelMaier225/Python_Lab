"""Keep the received LR artifact intact and verify approved runtime routing."""
import hashlib
import unittest

from website import registry
from website.main import evaluation


class LogisticArtifactTests(unittest.TestCase):
    def test_received_artifact_and_approved_status(self):
        entry = registry.model_entry('logistic_regression_v1')
        path = registry.artifact_path(entry)
        with path.open('rb') as file:
            checksum = hashlib.file_digest(file, 'sha256').hexdigest()
        self.assertEqual(checksum, 'f29f363006fa685333e4726a41508bf1f393b6992b3de451e92e74bb05efce89')
        self.assertEqual(checksum, entry['sha256'])
        self.assertEqual(entry['library_versions']['scikit-learn'], '1.9.1')
        self.assertEqual(len(entry['feature_schema']), 8)
        self.assertEqual(entry['status'], 'approved')
        self.assertEqual(entry['adapter'], 'logistic_pair_v1')
        self.assertEqual(entry['evaluation']['pair_count'], 4397)
        self.assertEqual(entry['evaluation']['overlap_audit']['excluded_pairs'], 1)
        self.assertNotIn(entry['id'], {item['id'] for item in evaluation()['models']})



if __name__ == '__main__':
    unittest.main()
