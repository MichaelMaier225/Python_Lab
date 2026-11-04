# Random Forest (Computers XL)

- `random_forest.ipynb`: received training notebook; only data/output paths and the saved feature-key mismatch were adjusted. Its displayed outputs are the teammate's existing outputs, not a new run.
- `features.py`: inference functions copied from that notebook. The English NLTK stopwords are vendored alongside their source README, avoiding runtime downloads.
- `../../trained_models/RF/random_forest_v1.joblib`: original received artifact, unchanged.
- The artifact uses `feature_columns`; the original notebook save cell used `feature_names`. The adapter accepts either and checks the exact feature order.

RF uses scikit-learn 1.9.1 in `.venv-rf`, while SVM stays on 1.8.0. From the project folder, run `python -m scripts.setup_rf_runtime` once. Render's existing `python prepare_assets.py` build step also installs this runtime. `PRODUCTMATCH_RF_PYTHON` optionally selects its interpreter.

The website uses the saved classifier's `predict` result, including its class-0 decision at a probability tie. The exploratory slider does not alter that official result. Probabilities have not been calibrated. RF was trained on computers only. The existing catalog lacks specification-table text, so that input is missing for catalog predictions; the API accepts `specTableContent` when available.

Original feature code credits: https://github.com/wbsg-uni-mannheim/wdc-lspc-v2 and https://github.com/anhaidgroup/py_entitymatching. Stopwords source: https://github.com/nltk/nltk_data/tree/gh-pages/packages/corpora (English stopwords; see STOPWORDS_README.txt).
