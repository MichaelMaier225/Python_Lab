# Random Forest

The model was trained on Computers XL. `random_forest.ipynb` keeps the
original notebook outputs. Its data paths, output path, and saved feature key
were adjusted. The website uses `features.py` and the [original saved model](../../trained_models/RF/random_forest_v1.joblib).

Run `python -m scripts.setup_rf_runtime` for scikit-learn 1.9.1.
Render runs it during build. Set `PRODUCTMATCH_RF_PYTHON` to use another
interpreter. The website uses the saved model's `predict` label. It accepts
`specTableContent` through the API. Catalog rows lack that field.

See the [shared benchmark](../../docs/evaluation/lr_rf_shared_gold_20261104/)
and [stopwords credit](STOPWORDS_README.txt). Feature code sources are
[WDC](https://github.com/wbsg-uni-mannheim/wdc-lspc-v2) and
[py_entitymatching](https://github.com/anhaidgroup/py_entitymatching).
