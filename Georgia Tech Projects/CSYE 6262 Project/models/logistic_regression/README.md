# Logistic Regression

- `train.py` is the original training script with two input path changes.
  It runs training on import, so keep it out of website imports.
- `features.py` builds the eight features in the saved model's order. Blank
  description, brand, and category fields are treated as missing at the website.
- The saved model uses its original `predict` labels and `predict_proba` scores.

Run `python -m scripts.setup_rf_runtime` for the shared RF/LR environment
with scikit-learn 1.9.1. The Render build does this too.

To run the original trainer, you need `data/Computers_XL_Training.csv`,
`data/Gold_Standard.xlsx`, and `openpyxl`. The script has no model export
step. The supplied `computers_train.zip` has 68,461 XL pairs, but its
equivalence to the original CSV is unverified.

See the [shared benchmark](../../docs/evaluation/lr_rf_shared_gold_20261104/).
