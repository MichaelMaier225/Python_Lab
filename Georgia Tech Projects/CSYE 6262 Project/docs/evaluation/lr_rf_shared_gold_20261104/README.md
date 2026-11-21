# Logistic Regression and Random Forest results

Both saved models were scored with their original settings in scikit-learn
1.9.1. One known Computers XL training pair was excluded, leaving **4,397
pairs** (3,200 different and 1,197 match). The main v4 benchmark used 4,398
pairs, so the model scores use slightly different sets.

Both models trained on computers. This benchmark covers more categories.
Product IDs can still overlap across splits, and the original LR CSV
conversion is unverified. RF used specification text when available in
the benchmark. The website catalog lacks that field.

From the project folder:

```bash
python -m scripts.evaluate_model --model logistic_regression_v1 --exclude-training data/computers_train.zip --output reports/evaluation/logistic_regression_v1
python -m scripts.evaluate_model --model random_forest_v1 --exclude-training data/computers_train.zip --output reports/evaluation/random_forest_v1
```
