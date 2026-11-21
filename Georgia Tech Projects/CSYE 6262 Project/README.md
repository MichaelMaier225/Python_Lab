# ProductMatch

Search for products, compare two listings, and vote on whether they match.
The website uses LinearSVC v4. V5 is the feedback experiment.

| Folder | What's in it |
| --- | --- |
| `data/` | Catalog, WDC datasets, and feedback CSV |
| `models/` | Feature and training code |
| `trained_models/` | Saved models and the model registry |
| `scripts/` | Tools to build the catalog and score models |
| `website/` | Dashboard, API, and feedback |
| `tests/`, `docs/`, `reports/` | Tests, project notes, and local results |

SVM code is under `models/svm/`. Open `svm_v4/` for v4, `svm_v5/` for v5,
or `shared/` for common code.

## Run on Windows

From the project folder, create `.venv` once. Put `products.db` in `data/`
if you want catalog search.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn website.main:app --reload
```

Open <http://127.0.0.1:8000>. For Logistic Regression and Random Forest,
run `.\.venv\Scripts\python.exe -m scripts.setup_rf_runtime` before starting the app.

- [Catalog, Render, and Supabase](docs/website.md)
- [Training and tests](docs/training.md)
- [V5 results](docs/evaluation/svm_v5/README.md)
- [Proposal](docs/proposal/)
