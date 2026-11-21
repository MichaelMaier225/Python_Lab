# Training, evaluation, and tests

Run these commands from the project root with the Python 3.12 environment
active. On Windows, `.\.venv\Scripts\python.exe` can be used in place of
`python`.

## 1. Put the training data in place

Place `all_train.zip`, `all_valid.zip`, and `all_gs.json.gz` under `data/` or
pass `--data-dir`. The trainers reuse the official validation IDs and exclude
exact or reversed gold-test pairs before fitting. Validation selects the SVM
settings and threshold using F0.5, which emphasizes precision. Some individual
products can appear in more than one split.

## 2. Choose a training workflow

| Goal | Command | Output |
| --- | --- | --- |
| Reproduce the v4 size experiments | `python -m models.svm.svm_v4.train_sizes` | `trained_models/svm/v4_size_experiments/<run>/` |
| Check how often the v5 feature fires | `python -m models.svm.svm_v5.train --audit-only` | Coverage counts and examples in the terminal |
| Fit v5 and compare against saved v4 | `python -m models.svm.svm_v5.train` | `trained_models/svm/v5/<run>/` |

V4's command fits Small, Medium, Large, XL, and Combined models. Choose a
subset with `--sizes small medium`. V5 fits one combined model. Its coverage
audit also checks `data/feedback_rows.csv` if present. This feedback helped
design the feature. Both trainers fit using the WDC inputs.

V5's `--fresh-test path/to/pairs.json.gz` accepts independently verified pairs
in gzipped WDC JSON Lines format, using `id_left` and `id_right` or
`pair_id=left#right`. The command excludes pairs that share product IDs with
the WDC splits. Both saved v4 and candidate v5 are scored on the retained pairs.

## 3. Evaluate a saved model

```bash
python -m scripts.evaluate_model
```

The evaluator uses the model's saved threshold and defaults to the active
registry entry. Use `--model` for another supported entry, `--data` for
another labeled file, and `--output` to change the report directory. Reports
default to `reports/evaluation/`. Keep version-specific benchmark results
with their data provenance. Compare metrics only when the models were scored
on the same pairs. In a confusion matrix, rows are actual labels and columns
are predictions, with `different` first.

- [V4 size experiments](evaluation/svm_sizes_20261104/)
- [Saved v4 benchmark](evaluation/svm_v4_20261104/)
- [Logistic Regression and Random Forest benchmark](evaluation/lr_rf_shared_gold_20261104/)
- [V5 feedback experiment and decision](evaluation/svm_v5/)

The trained artifacts and adapters must use the same feature schema. When a
candidate is ready, record its artifact path, SHA-256, version, runtime, and
evaluation in the registry. The active site currently uses the bundled v4
artifact. Training writes to separate output directories.

## 4. Verify the code and the website

```bash
python -m unittest discover -s tests -v
node --check website/static/script.js
node --check website/static/charts.js
```

The original Logistic Regression parity test needs the isolated runtime.
Run that test module with the Python executable inside `.venv-rf`:

```bash
python -m unittest discover -s tests -p test_logistic_features.py -v
```

For the optional browser smoke test, install Playwright, start the local app on
port 8011, and run `python tests/browser_smoke.py` in another terminal.
`CHROMIUM_PATH` selects an installed Chromium executable, and
`PRODUCTMATCH_TEST_URL` can point the test at a different local port.
