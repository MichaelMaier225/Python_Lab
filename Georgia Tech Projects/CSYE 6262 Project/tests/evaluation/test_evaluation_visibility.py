"""Evaluation-display changes must preserve saved results and prediction selectors."""
import copy
import unittest
from unittest.mock import patch

from website import main, registry


class EvaluationVisibilityTests(unittest.TestCase):
    def test_only_svm_evaluation_is_published_and_unchanged(self):
        entries = registry.entries()
        original = copy.deepcopy(entries)
        expected = next(e for e in entries if e['id'] == 'linear_svc_combined')
        result = main.evaluation()['models']
        self.assertEqual([e['id'] for e in result], ['linear_svc_combined'])
        self.assertEqual(result[0]['evaluation'], expected['evaluation'])
        self.assertEqual(registry.entries(), original)
        for model_id in ['logistic_regression_v1', 'random_forest_v1']:
            self.assertIsNotNone(next(e for e in entries if e['id'] == model_id)['evaluation'])

    def test_predictor_metadata_keeps_capabilities_and_hides_results(self):
        for adapter in ['logistic_pair_v1', 'random_forest_pair_v1']:
            info = {'available': True, 'capabilities': {'probability': True},
                    'evaluation': {'metrics': {'accuracy': 0.99}},
                    'integration_note': 'Evaluation details that should be hidden.'}
            with patch.object(main, 'model_info', return_value=copy.deepcopy(info)):
                visible = main.display_model_info({'adapter': adapter})
            self.assertNotIn('evaluation', visible)
            self.assertEqual(visible['capabilities'], info['capabilities'])
            self.assertTrue(visible['available'])
            self.assertNotIn('Evaluation details', visible['integration_note'])
