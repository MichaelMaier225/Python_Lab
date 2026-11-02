# ProductMatch

FastAPI website for searching historical WDC listings and comparing products
with the existing TF-IDF / LinearSVC model.

## Run locally

Use Python 3.12. From this directory:

```bash
python -m venv .venv
```

Activate it with `source .venv/bin/activate` (macOS/Linux) or
`.venv\Scripts\Activate.ps1` (Windows PowerShell), then run:

```bash
python -m pip install -r requirements.txt
python -m uvicorn website.main:app --reload
```

## Deploy on Render

Create a Python 3 Web Service connected to `MichaelMaier225/Python_Lab`:

| Setting | Value |
| --- | --- |
| Branch | `main` |
| Root Directory | `Georgia Tech Projects/CSYE 6262 Project` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn website.main:app --host 0.0.0.0 --port $PORT` |
| Environment variable | `PYTHON_VERSION=3.12.14` |
| Health Check Path (Advanced) | `/live` |

The free instance can be used to deploy and inspect the website shell. Its
filesystem is ephemeral: local database changes do not survive replacement or
redeployment. Do not depend on it for persistent feedback or uploaded data.
Model and dataset memory usage must be measured before choosing a final plan.

`/live` checks that the API process responds. `/health` separately checks model
loading and reports the indexed product count. A successful `/live` response
does not establish that prediction or populated search works.

## Required data and model

These files are ignored by Git and are not supplied by installing dependencies:

- `models/svm_small_v3.joblib`: trusted original model and fitted vectorizers.
- `data/products.db`: populated SQLite product database.

Without them, the page still loads, search returns no listings, `/health`
returns 503, and `/predict` returns 500. Provision these artifacts on Render
before claiming the complete application works. No artifact download source is
configured yet. Do not upload the full WDC corpus to GitHub.

To build the database locally, place the original
`offers_corpus_all_v2_non_norm.json.gz` in `data/`, then run:

```bash
python build_database.py --inspect
python build_database.py --limit 50000
```

The limit counts input records; it does not guarantee that many inserted products.
The existing training script requires `data/all_train.zip`, `data/all_valid.zip`,
and `data/all_gs.json.gz`. Deployment does not retrain or replace the model.

Only load trusted joblib artifacts. The dependency versions in requirements.txt
match the inspected development runtime; compatibility with the original trained
artifact still needs verification against its training environment.
