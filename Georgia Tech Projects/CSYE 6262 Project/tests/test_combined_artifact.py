"""Actual saved-model/default checks, including legacy deployment variable isolation."""
import os
import unittest
from unittest.mock import patch

from website import registry


class CombinedArtifactTests(unittest.TestCase):
    def test_default_saved_threshold_and_legacy_checksum_isolation(self):
        with patch.dict(os.environ, {'MODEL_SHA256': '0' * 64}):
            with patch.dict(os.environ):
                os.environ.pop('ACTIVE_MODEL', None)
                os.environ.pop('SVM_COMBINED_SHA256', None)
                entry = registry.model_entry()
                self.assertEqual(entry['id'], 'linear_svc_combined')
                self.assertEqual(entry['sha256'], '5f55d72fa195e917a76abeff413d578df6345a0533b2e008b6ba50d739047c9f')
                bundle = registry.load_bundle(entry)
                self.assertEqual(bundle['threshold'], 0.25)
                self.assertEqual(bundle['size'], 'combined')
                self.assertEqual(bundle['training_pairs'], 201457)
                self.assertFalse(bundle['validation_refit'])
                self.assertEqual(entry['evaluation']['confusion_matrix'], [[2937, 263], [188, 1010]])
                product = {'title': 'Samsung laptop', 'brand': 'Samsung', 'description': ''}
                prediction = registry.predict_pairs([(product, product)])[0]
                self.assertEqual(prediction['model_id'], 'linear_svc_combined')
                self.assertEqual(prediction['threshold'], 0.25)

    def test_only_combined_svm_is_listed_on_website(self):
        from website.main import models, evaluation
        visible = models()['models']
        self.assertEqual([x['id'] for x in visible if x['algorithm'] == 'LinearSVC'], ['linear_svc_combined'])
        self.assertEqual(next(x['name'] for x in visible if x['id'] == 'linear_svc_combined'), 'SVM')
        listed = {x['id'] for x in evaluation()['models']}
        self.assertNotIn('linear_svc_v3', listed)
        self.assertIn('linear_svc_combined', listed)
        self.assertTrue(registry.artifact_path(registry.model_entry('linear_svc_v3')).is_file())
