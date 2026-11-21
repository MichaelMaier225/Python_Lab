# ProductMatch

ProductMatch searches a catalog of historical product listings, compares two
listings with a trained model, and saves user feedback on the prediction.
The website uses **LinearSVC v4** by default. V5 is a separate experiment
inspired by feedback about false matches.

# Follow the project

| Step | Folder | What's inside |
| 1. Get the data | `data/`, `scripts/` | Local datasets, the SQLite catalog, feedback exports, and tools to prepare them |
| 2. Train the model | `models/` | Feature extraction and training code |
| 3. Save the result | `trained_models/` | Fitted models and the registry the website uses to find them |
| 4. Run the app and collect feedback | `website/` | FastAPI, catalog search, the dashboard, and Supabase feedback |
| 5. Check and explain the results | `tests/`, `docs/`, `reports/` | Automated checks, project documentation, and locally generated reports |

The SVM source is divided into `models/svm/svm_v4/` for the deployed version,
`models/svm/svm_v5/` for the experiment, and `models/svm/shared/` for shared
scoring and legacy feature code. The saved v4 artifact lives at
`trained_models/svm/v4/svm_combined.joblib`.

# Run on Windows

From the `CSYE 6262 Project` folder in PowerShell, use Python 3.12:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m scripts.setup_rf_runtime
.\.venv\Scripts\python.exe -m uvicorn website.main:app --reload
```

Create the virtual environment once. The runtime setup enables the optional
Random Forest and Logistic Regression models. Place `products.db` in `data/`
for catalog search. Manual comparisons are available with the bundled model.
Open `http://127.0.0.1:8000` for the dashboard and append `/docs` for the API.

# Keep going

- [Catalog, website, deployment, and feedback](docs/website.md)
- [Training, evaluation, and test commands](docs/training.md)
- [V5 experiment and why v4 stayed live](docs/evaluation/svm_v5/README.md)
- [Original proposal and project requirements](docs/proposal/)
