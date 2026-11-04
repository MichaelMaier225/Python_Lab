"""Small synthetic archives exercise the full loop, not real benchmark performance."""
import gzip
import io
import json
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout
from pathlib import Path

import joblib
import pandas as pd

from models.svm.train import read_validation_ids
from models.svm.train_sizes import SIZES, deduplicate, prepare_pairs, run


def pair(number, label):
    return {'pair_id':f'{10000+number}#{20000+number}',
            'id_left':10000+number,'id_right':20000+number,'label':label,
            'title_left':'Samsung 990 SSD', 'brand_left':'Samsung','description_left':'Fast storage drive',
            'title_right':'Samsung 990 SSD' if label else 'Canon camera lens',
            'brand_right':'Samsung' if label else 'Canon',
            'description_right':'Fast storage drive' if label else 'Zoom camera lens'}


def archives(folder):
    validation=[pair(100,1),pair(101,0),pair(102,1)]
    with zipfile.ZipFile(folder/'all_train.zip','w') as train, zipfile.ZipFile(folder/'all_valid.zip','w') as valid:
        for size,count in zip(SIZES,[4,6,8,10]):
            rows=[pair(i,i%2) for i in range(count)]+validation
            reverse=dict(rows[0])
            reverse['pair_id']=f"{reverse['id_right']}#{reverse['id_left']}"
            reverse['id_left'],reverse['id_right']=reverse['id_right'],reverse['id_left']
            for field in ['title','brand','description']:
                a,b=f'{field}_left',f'{field}_right'
                reverse[a],reverse[b]=reverse[b],reverse[a]
            rows.append(reverse)
            content=pd.DataFrame(rows).to_json(orient='records',lines=True).encode()
            train.writestr(f'all_train/all_train_{size}.json.gz',gzip.compress(content))
            ids=[r['pair_id'] for r in validation[:3 if size=='xlarge' else 2]]
            valid.writestr(f'all_valid/all_valid_{size}.json',json.dumps(ids))
    pd.DataFrame([pair(1000,0),pair(1001,1)]).to_json(folder/'all_gs.json.gz',orient='records',lines=True,compression='gzip')


class SizeExperimentTests(unittest.TestCase):
    def test_all_five_models_saved_and_shared_validation_excluded(self):
        with tempfile.TemporaryDirectory() as folder, redirect_stdout(io.StringIO()):
            root=Path(folder)
            archives(root)
            output,report=run(root,root/'runs')
            self.assertEqual(report['status'],'complete')
            self.assertEqual([r['size'] for r in report['results']],[*SIZES,'combined'])
            self.assertEqual(report['common_validation_pairs'],3)
            self.assertEqual(report['combined_equivalent_to'],['xlarge'])
            self.assertEqual(report['audit']['combined']['unique_pairs'],13)
            self.assertEqual([r['training_pairs'] for r in report['results']],[4,6,8,10,10])
            summary=pd.read_csv(output/'comparison.csv')
            self.assertEqual(len(summary),5)
            for result in report['results']:
                bundle=joblib.load(output/result['artifact'])
                self.assertFalse(bundle['validation_refit'])
                self.assertEqual(bundle['size'],result['size'])
                self.assertEqual(bundle['validation_pairs'],3)
                self.assertEqual(sum(map(sum,result['test']['confusion_matrix'])),2)
                self.assertTrue((output/f"errors_{result['size']}.csv").is_file())
            validation=pd.read_csv(output/'validation_pairs.csv')
            self.assertEqual(set(validation['pair_id']),{pair(i,0)['pair_id'] for i in [100,101,102]})
            self.assertEqual((output/'results.json').read_text(),json.dumps(report,indent=2)+'\n')
            self.assertEqual(len(list(output.glob('*.joblib'))),5)

    def test_large_and_xlarge_validation_files_are_distinct(self):
        with tempfile.TemporaryDirectory() as folder, redirect_stdout(io.StringIO()):
            root=Path(folder);archives(root)
            self.assertEqual(len(read_validation_ids('large',root)),2)
            self.assertEqual(len(read_validation_ids('xlarge',root)),3)

    def test_conflicting_duplicate_is_rejected(self):
        frame=prepare_pairs(pd.DataFrame([pair(1,1),pair(1,0)]))
        with self.assertRaises(ValueError): deduplicate(frame)

    def test_reversed_gold_overlap_is_rejected_before_training(self):
        with tempfile.TemporaryDirectory() as folder, redirect_stdout(io.StringIO()):
            root=Path(folder);archives(root)
            original=pair(0,0)
            original['id_left'],original['id_right']=original['id_right'],original['id_left']
            original['pair_id']=f"{original['id_left']}#{original['id_right']}"
            pd.DataFrame([original]).to_json(root/'all_gs.json.gz',orient='records',lines=True,compression='gzip')
            with self.assertRaisesRegex(ValueError,'overlapping or reversed'):
                run(root,root/'runs')
            self.assertFalse((root/'runs').exists())


if __name__=='__main__': unittest.main()
