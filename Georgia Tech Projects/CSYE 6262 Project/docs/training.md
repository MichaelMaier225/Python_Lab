# Train and test

Put `all_train.zip`, `all_valid.zip`, and `all_gs.json.gz` in `data/`, or use
`--data-dir`. Run from the project folder. On Windows, use
`.\.venv\Scripts\python.exe` in place of `python`.

| What to run | Command |
| --- | --- |
| Train v4 by dataset size | `python -m models.svm.svm_v4.train_sizes` |
| Check the v5 feature | `python -m models.svm.svm_v5.train --audit-only` |
| Train v5 and compare with v4 | `python -m models.svm.svm_v5.train` |
| Score a saved model | `python -m scripts.evaluate_model` |

V4 saves under `trained_models/svm/v4_size_experiments/`. Use
`--sizes small medium` to pick sizes. V5 saves under `trained_models/svm/v5/`.
The v5 audit reads `data/feedback_rows.csv` if present. Both models train on WDC.

Exact and reversed gold pairs are excluded before fitting. Validation picks
the settings and threshold by F0.5, which gives precision more weight.
Some product IDs still overlap across WDC splits.

Use v5's `--fresh-test path/to/pairs.json.gz` for reviewed pairs in WDC JSON
Lines format. Include `id_left` and `id_right` or `pair_id=left#right`.
Pairs that share product IDs with WDC are skipped.

The saved-model evaluator defaults to the active model. Use `--model` to pick
an entry, `--data` to pick a dataset, or `--output` to change the report folder
from `reports/evaluation/`. For a fair comparison, score the same pairs.
Confusion matrix rows are actual labels and columns are predictions, with
`different` first. Record the feature schema, artifact path, SHA-256, version,
and runtime when adding a model to the registry.

## Tests

Backend, model, and evaluation tests run together. Browser tests run separately.

```bash
python -m unittest discover -s tests -v
node --check website/static/script.js
node --check website/static/charts.js
```

Run the LR test with the isolated Python environment:

```powershell
.\.venv-rf\Scripts\python.exe -m unittest discover -s tests -p test_logistic_features.py -v
```

For the browser smoke test, install Playwright and start the local app on port
8011. Run `python tests/browser/browser_smoke.py`. Set `CHROMIUM_PATH` for your
Chromium install or `PRODUCTMATCH_TEST_URL` for a different local URL.

## Results

- [V4 size experiments](evaluation/svm_sizes_20261104/)
- [Saved v4 benchmark](evaluation/svm_v4_20261104/)
- [Logistic Regression and Random Forest](evaluation/lr_rf_shared_gold_20261104/)
- [V5 feedback experiment](evaluation/svm_v5/)
