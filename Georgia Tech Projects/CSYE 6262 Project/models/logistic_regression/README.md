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

The artifact was saved with scikit-learn **1.9.1**. Its probabilities and labels
were verified against the original source in an isolated 1.9.1 environment.
The current website/SVM environment remains on **1.8.0**, and both original
artifacts remain unchanged. LR therefore stays experimental and unavailable on
the live site until the deployment versions are reconciled. Do not disable
version checks or simply upgrade the shared requirements: the SVM artifact needs
its own verified version too.

A straightforward next option is for the teammate to train/export LR in the same
1.8.0 environment as the SVM, keeping this original v1 artifact as historical
work and giving the new export its own version. Otherwise, supporting separate
runtimes needs an explicit deployment change. Neither was performed here.

Evaluation results and exact dataset/split provenance still need to be supplied.
