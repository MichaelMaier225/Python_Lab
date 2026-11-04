# Logistic Regression

`train.py` is the teammate's supplied `LogisticR Model.py`. Only its two input
paths were changed to resolve under the project's `data/` directory:

- `Computers_XL_Training.csv`
- `Gold_Standard.xlsx`

Every other statement, function, model setting, comment and notebook cell marker
is preserved. The script runs training at module scope: **do not import it into
the website**. The supplied script does not include a joblib export step; the
existing fitted artifact remains separately preserved, without re-exporting it.
No training run was performed because the CSV and Excel files were not supplied.
Excel loading also needs `openpyxl` in the original training environment.

`features.py` is a separate serving adapter. Its feature order matches the saved
bundle's `feature_columns`. It uses the original fitted vectorizers and the same
TF-IDF products, availability rules, category equality, description-token Jaccard
features, and brand comparison. Tests execute only the original feature-building
statements to check parity; they do not execute its training or file-loading cells.

At the website boundary, empty description/brand/category fields represent absent
CSV cells and become missing values. The feature function itself preserves the
original distinction between an empty string and a missing value. Catalog
categories are forwarded to pair prediction; manual pairs without a known category
keep it missing. Official labels use the original classifier's `predict` method,
including its tie behavior. Probabilities come from `predict_proba`, not from a
conversion of SVM scores; calibration is not claimed.

## Runtime status

LR is enabled through the same isolated scikit-learn **1.9.1** runtime already used by RF (`.venv-rf`). SVM stays on **1.8.0**. The shared JSON prediction worker is `models/sklearn_worker.py`. The original artifact and teammate training source remain unchanged.

From the project folder, `python -m scripts.setup_rf_runtime` installs the shared RF/LR runtime. Render's existing `python prepare_assets.py` build step already does this. The model selector changes actual feature extraction, candidate scores, official predictions, and feedback model IDs. LR uses its original classifier decision with a 0.5 probability boundary; calibration is not claimed.

`data/computers_train.zip` was inspected: it contains normalized Small, Medium, Large, and XL JSON.gz files. XL has 68,461 pairs (58,771 different, 9,690 match). The data folder is ignored by Git. This establishes the supplied archive contents, not exact equivalence to the teammate's `Computers_XL_Training.csv` or the provenance of `Gold_Standard.xlsx`. No conversion or retraining was silently performed. Source feature parity and saved-artifact prediction parity are tested separately from real-world matching quality.

Evaluation is populated from the documented shared 4,397-pair broader benchmark, with one known training pair excluded against the supplied archive. See docs/evaluation/lr_rf_shared_gold_20261104/. Original CSV preparation/full training provenance is still unverified; this is not certified unseen-product or website-retrieval performance. No retraining or threshold changes were performed.
