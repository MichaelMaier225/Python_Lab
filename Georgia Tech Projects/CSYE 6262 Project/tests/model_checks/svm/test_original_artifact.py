"""Compatibility checks for the actual committed baseline, not accuracy estimates."""
import unittest

import numpy as np

from website import registry


class OriginalArtifactTests(unittest.TestCase):
    @unittest.skipUnless((registry.ROOT / 'trained_models' / 'svm' / 'svm_small_v3.joblib').exists(), 'Original artifact is not installed')
    def test_original_scores_preserved_after_organization(self):
        entry = next(e for e in registry.entries() if e['id'] == 'linear_svc_v3')
        bundle = registry.load_bundle(entry)
        products = [
            {'title':'Samsung 990 PRO 1TB SSD','brand':'Samsung','description':'1TB NVMe SSD'},
            {'title':'Samsung 990 PRO 2TB SSD','brand':'Samsung','description':'2TB NVMe SSD'},
            {'title':'Lenovo ThinkPad T14 Gen 5','brand':'Lenovo','description':''},
            {'title':'','brand':'','description':''},
        ]
        pairs = [(products[0],products[0]), (products[0],products[1]),
                 (products[0],products[2]), (products[2],products[3])]
        # Recorded from the original, pre-organization feature code and model.
        expected = np.array([1.2597878032904417, 0.8872527909719772,
                             -1.0329692546660636, -0.5431122447755886])
        actual = registry.predict_pairs(pairs,'linear_svc_v3')
        np.testing.assert_allclose([r['raw_score'] for r in actual],expected,rtol=1e-12,atol=1e-12)
        self.assertEqual([r['is_match'] for r in actual],(expected>=bundle['threshold']).tolist())
        self.assertTrue(all(r['probability'] is None for r in actual))


if __name__ == '__main__': unittest.main()
