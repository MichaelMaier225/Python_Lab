# ProductMatch

FastAPI website for searching historical WDC listings and comparing products
with the existing TF-IDF / LinearSVC model.

## Folder layout

```text
models/                        Algorithm source code
    svm/
        train.py               Train the existing SVM
        features.py            Shared SVM preprocessing and pair features
        scoring.py             Shared batch scoring for experiments/evaluation
    logistic_regression/       Teammate source goes here (still pending)
    decision_tree/             Teammate source goes here (not supplied yet)
trained_models/                Saved models, grouped by algorithm
    svm/                       Original SVM v2 and v3 joblib files
    logistic_regression/       Received LR v1 joblib (integration pending)
    registry.json              Version metadata, checksums and readiness
website/                       FastAPI backend and frontend files
    static/                    HTML, CSS, JavaScript and vendored D3
scripts/                       Dataset and deployment tools
    build_database.py          Import the original product corpus
    prepare_assets.py          Download and verify deployment assets
    evaluate_model.py          Evaluate a saved model without retraining
tests/                         Backend/model tests and browser checks
    fixtures/                  Frozen, synthetic feature regression data
data/                          Local datasets and SQLite files (Git-ignored)
docs/proposal/                 Proposal slides, requirements and planning figures
prepare_assets.py              Compatibility entry point for the live Render build
requirements.txt               Application dependencies
requirements-dev.txt           Additional test dependencies
```

Put future LR and Decision Tree training scripts in their named subfolders in
`models/` when their real source is available. Their fitted artifacts belong in separate `trained_models/`
subfolders. No placeholder algorithm implementations have been added.

From this project directory:

```bash
# Train SVM only when the original datasets are available:
python -m models.svm.train
# Inspect/import product data:
python -m scripts.build_database --inspect
python -m scripts.build_database --limit 50000
# Download configured deployment assets:
python -m scripts.prepare_assets
# Evaluate the saved SVM on data/all_gs.json.gz, without training:
python -m scripts.evaluate_model
# Run automated tests:
python -m unittest discover -s tests -v
# Start the website:
python -m uvicorn website.main:app --reload
```

The Render root directory, start command and database environment variables stay
the same. Its existing `python prepare_assets.py` build step delegates to
`scripts.prepare_assets`, so no immediate Render settings edit is needed.
The module command `python -m scripts.prepare_assets` is the preferred new entry
point. The small root wrapper is in use, not dead code.

The algorithm source folder used to contain the saved artifacts. After pulling
this reorganization, any older untracked copies of `.joblib` files may remain in
your local `models/` directory; inspect those against `trained_models/` before
removing your own copies. Local `data/` files are left in place. If you configured
`PRODUCTMATCH_MODEL_DIR`, it now points at the root containing the `svm/` and
`logistic_regression/` artifact subfolders.

## Run locally

Use Python 3.12. From this directory:

```bash
python -m venv .venv
```

Activate it with `source .venv/bin/activate` (macOS/Linux),
`.venv\Scripts\activate.bat` (Windows Command Prompt), or
`.venv\Scripts\Activate.ps1` (PowerShell), then run:

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

The v2 and v3 model artifacts are now committed in `trained_models/`. The v3 artifact's
SHA-256 is pinned in `trained_models/registry.json`; it loads successfully with the current
requirements. A regression check confirms identical scores from the original
training feature pipeline and the serving adapter on representative inputs.
This verifies compatibility, not test-set accuracy.

`data/products.db` is still ignored by Git and must be supplied separately. Without
a populated database, manual predictions can work but search returns no listings.
`/health` reports the indexed count, which must be nonzero for a catalog demo.

To build the database locally, place the original
`offers_corpus_all_v2_non_norm.json.gz` in `data/`, then run:

```bash
python -m scripts.build_database --inspect
python -m scripts.build_database --limit 50000
```

The limit counts input records; it does not guarantee that many inserted products.
The existing training script requires `data/all_train.zip`, `data/all_valid.zip`,
and `data/all_gs.json.gz`. Deployment does not retrain or replace the model.

Only load trusted joblib artifacts. The dependency versions in requirements.txt
match the verified development runtime for the committed v3 artifact. The original
training environment and evaluation results are not fully documented.

## Interactive dashboard

The workspace keeps search, candidate exploration and pair inspection side by side on desktop.
Model evaluation has its own tab; method details and manual editing can be expanded
when needed. The website connects four areas:

1. **Explorer:** search the SQLite FTS index, select a reference, and retrieve up
   to 40 lexical candidates. Candidate retrieval uses title tokens without using
   ground-truth cluster labels. These results are not exhaustive matches.
2. **Comparison:** select a chart point (mouse or keyboard) or a listing to fill
   the pair forms. Inspect an independent attribute agreement matrix or run an
   official model prediction. Manual inputs and the Fill Example action remain.
3. **Evaluation:** inspect version-specific, team-reviewed labeled results when
   supplied. Missing results have an explicit empty state.
4. **Feedback:** review an official prediction. Submissions retain listing
   contents, a stable content-based pair ID, model ID/version, original prediction
   and score, choice, and UTC timestamp in `data/feedback.db`.

A threshold slider changes exploratory candidate classifications, plot colors,
match counts and the lowest qualifying listed price. It does not retrain the
classifier or change the official prediction. An official prediction must be
requested before feedback is enabled. Editing pair fields invalidates that review.
Feedback is recomputed on the server and rejected if the active model version
changed. A request UUID makes repeated submissions idempotent; anonymous feedback
is still unverified, and this does not identify or prevent a determined spammer.

Select one currency to plot price against score and filter/sort prices. Without
one currency, the chart uses candidate position instead of mixing currencies.
Missing-price listings stay in the list; label-only models use the list without
inventing scores. Original listing links accept only HTTP(S). Product text is
rendered with DOM text nodes, not HTML insertion.

Attribute parsing intentionally requires explicit evidence: a brand field,
`model: ABC-123`, `16GB RAM`, `1TB SSD`, or `color: black`, for example. Ambiguous
or missing values stay unknown. Storage units use decimal conversion; these are
observations, not proof of configuration equivalence or explanations of model
weights. Actual dataset coverage needs measurement. The original ML text cleaning
and feature ordering have not been changed.

## Architecture and APIs

- `website/main.py`: bounded request schemas and HTTP routes.
- `website/database.py`: parameterized product lookup, search and retrieval.
- `models/svm/features.py`: unchanged baseline feature transformations.
- `website/registry.py`: trusted artifact loading, caching and model adapters.
- `website/attributes.py`: conservative, independent attribute comparison.
- `website/feedback.py`: SQLite review storage.
- `website/static/script.js`: shared UI state and linked interactions.
- `website/static/charts.js`: D3 v5 scatterplot and evaluation curve.
- `trained_models/registry.json`: versioned model metadata; the saved SVM and LR artifacts are tracked.

D3 5.16.0 is vendored from its npm distribution with its license so the deployed
site does not depend on a third-party script CDN. There is no frontend build step.

| Route | Purpose |
| --- | --- |
| `GET /live` | Process liveness, independent of model availability |
| `GET /health` | Model readiness and indexed product count |
| `GET /models` | Configured versions, availability and active model capabilities |
| `GET /search?q=...&limit=20` | Up to 50 lexical search results |
| `GET /candidates/{id}?limit=40` | Reference and up to 50 candidates scored in one batch |
| `POST /predict` | Official pair prediction, attributes, compatible price comparison |
| `POST /predict/batch` | `{"pairs":[{"product_a":...,"product_b":...}]}`; 1–50 pairs |
| `POST /compare` | Attribute comparison; works without a trained model |
| `POST /feedback` | Pair, `choice`, UUID `request_id`, `model_id`, `model_version` |
| `GET /evaluation` | Version-specific genuine evaluation data, if supplied |

FastAPI's `/docs` documents complete request/response usage. A product includes
`title`, optional `brand`, `description`, `price`, `currency`, `seller`, and
`source_id`. Prediction responses retain `is_match`, `prediction`,
`decision_score` and `threshold`, and add full-precision `raw_score`, optional
`probability`, `score_type`, `score_direction`, model identity, and attributes.
A missing/unusable model now returns **503** rather than the old generic 500.
Existing manual pair requests default to USD; dataset-driven inputs explicitly
send their recorded currency. Cross-currency comparisons are excluded.

## Model versions and teammate integration

The combined all-category SVM is now the default; original LinearSVC v3 remains a separate baseline. Existing
artifacts are never retrained or overwritten by application startup. Training
and serving now import the original feature calculations from
`models/svm/features.py`, removing the duplicate implementation. The registry
keeps one batch prediction implementation.

`trained_models/registry.json` keeps version metadata alongside the source. Each
version gets a unique ID and artifact path within `trained_models/`. Preserve old entries
and binaries. Record algorithm, adapter, status, dataset, feature schema, labels,
training configuration, original library versions, creation date, checksum and
reviewed evaluation data. Unknown original-run metadata stays null; the current
baseline record is not evidence of a completed evaluation or original environment.

The existing `tfidf_pair` adapter accepts a **trusted joblib dictionary** with:

- `model`: fitted binary sklearn classifier with classes `[0, 1]`.
- `title_vectorizer` and `description_vectorizer`: original fitted vectorizers.
- `threshold`: original decision threshold, when supported.

It uses exactly the existing feature pipeline. Models trained on different
features, embeddings or label encodings require a separate Python adapter in
`registry.py`; selecting the model then needs no frontend rewrite. Do not attach
an unrelated classifier to the SVM vectorizers.

Use `score_type: "decision_score"` for compatible `decision_function` outputs,
`"probability"` for legitimate `predict_proba` outputs, or null for labels only.
No score-to-probability conversion is performed. Probabilities are not claimed to
be calibrated just because `predict_proba` exists. Higher scores must mean label
1 for these adapters. A configured threshold is required to enable threshold
exploration. Otherwise labels come from the classifier's `predict` method.

Only entries with `status: "approved"` can serve predictions. New versions should
start as `experimental`. A human must review compatible preprocessing, split
integrity, runtime/memory behavior and evaluation before approval. Select an
approved version with Render variable `ACTIVE_MODEL=<id>`; default is
`linear_svc_combined`. There is no public model-upload or activation endpoint.

Joblib can execute code. Only use an artifact from a trusted producer, with its
SHA-256 configured in the registry (or `MODEL_SHA256` for the active model).
Checksums verify the expected file; they do not make an untrusted pickle safe.
Paths are constrained to the configured model directory. Loaded bundles are cached
by path, hash and file modification timestamp. sklearn version mismatch warnings
are treated as failures; match the original training library versions before
loading. A label-only adapter advertises no continuous-score capabilities.

## Provision existing artifacts on Render

The model now deploys from the committed `trained_models/` directory. Only the populated
product database needs transferring. For this public repository, use a Release asset:

1. Open the repository's Releases page and choose **Draft a new release**.
2. Create tag `productmatch-assets-v1` against `main`.
3. Attach your existing `data/products.db` using the binary attachment area, then
   publish the release. The asset will be publicly downloadable. Close any database
   importer before copying the file.
4. In Render, set these environment variables:

```text
DATABASE_URL=https://github.com/MichaelMaier225/Python_Lab/releases/download/productmatch-assets-v1/products.db
DATABASE_SHA256=<SHA-256 of the exact original products.db file>
```

Get the hash in Windows Command Prompt from your local repository root:

```bat
certutil -hashfile "Georgia Tech Projects\CSYE 6262 Project\data\products.db" SHA256
```

Copy only the hexadecimal hash line into `DATABASE_SHA256`. The model's expected
hash is already committed; no `MODEL_URL` or `MODEL_SHA256` variable is needed for
the bundled v3 artifact. The helper also supports optional `MODEL_URL` and
`MODEL_SHA256` if a future version is provisioned from a trusted HTTPS source.

Change the Render build command to:

```bash
pip install -r requirements.txt && python prepare_assets.py
```

Save the settings, then select **Manual Deploy → Deploy latest commit**. Build logs
should report `DATABASE: downloaded and verified.` Verify `/health` returns 200
with a nonzero product count, then try an actual search and prediction.

`scripts/prepare_assets.py` streams downloads into temporary files, verifies SHA-256,
checks the database schema/integrity and atomically installs verified files. An
incorrect download leaves existing files intact and fails the build. With no URLs,
it leaves existing files alone. It does not deserialize a model or train one.
Copy the database while no importer or writer is using it so it is a complete
SQLite file, not an incomplete WAL snapshot.

On Windows PowerShell, get the original file hashes from the project directory:

```powershell
Get-FileHash .\trained_models\svm\svm_small_v3.joblib -Algorithm SHA256
Get-FileHash .\data\products.db -Algorithm SHA256
Get-Item .\trained_models\svm\svm_small_v3.joblib, .\data\products.db | Select-Object Name, Length
```

For durable feedback, attach persistent storage and set `PRODUCTMATCH_DATA_DIR`
to its mounted directory. Set `PRODUCTMATCH_MODEL_DIR` only if models live outside
this project's `trained_models/`. A Render build may not have access to a runtime disk;
provision that disk separately before pointing runtime paths at it. Downloading
into build-local `data/` does not initialize an unrelated mounted directory.
Free-instance feedback is local and disposable. Do not enable a database refresh
against a live writable dataset. Choose a paid plan only after measuring the real
model's peak memory; 512 MB has not been validated for the original artifact.

## Evaluation data and methodology

The evaluation dashboard reads the optional `evaluation` value in each registry
entry. Add only results from an identified, genuine labeled run. Expected shape:

```json
{
  "dataset_id": "exact dataset version or content hash",
  "split": "held-out test",
  "procedure": "fixed model and threshold, no test-set tuning",
  "metrics": {"accuracy": 0.0, "precision": 0.0, "recall": 0.0, "f1": 0.0},
  "confusion_matrix": [[0, 0], [0, 0]],
  "thresholds": [{"threshold": 0.0, "precision": 0.0, "recall": 0.0, "fp": 0, "fn": 0}]
}
```

These zeros illustrate the schema only; **do not copy them as results**. The
committed baseline evaluation is null. Confusion matrix order is [[TN, FP],
[FN, TP]]. Threshold exploration displays precomputed labeled results, not metrics
inferred from unlabeled listings. The viewer switches between supplied model
versions; pair-level error differences are not implemented. Compare versions only
when dataset, split, label definitions and procedures match. Never tune on the
final test set or mix anonymous feedback into its labels.

Suggested evidence for the course report:

- Compare the original SVM against a title-similarity or Logistic Regression
  baseline on the same split; report precision, recall, F1 and errors by category.
- Check reversed/duplicate pairs across splits; characterize product/cluster
  overlap rather than relying only on pair-ID disjointness.
- Measure candidate retrieval recall separately: the classifier cannot recover
  a true match excluded by the lexical retrieval step.
- Measure latency and memory with the actual deployment artifacts and batch sizes.
- Compare the linked interface with the original form on review tasks: completion
  time, correctly detected configuration conflicts, and reviewer agreement.

The proposed visual contribution is the coordinated investigation of high-scoring
but attribute-conflicting candidates and threshold-sensitive listing choices.
This is a design hypothesis, not a proven innovation or measured improvement.
The supplied course requirements call for computation and visualization novelty;
adding standard charts alone does not establish that requirement.

## Verification

From the project directory, using an activated development environment:

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
node --check website/static/script.js
node --check website/static/charts.js
```

The backend suite checks the actual committed v3 artifact against scores recorded
before the organization change and a frozen synthetic feature matrix. Other tests train tiny, explicitly synthetic fixtures in temporary
folders, exercises real APIs, and checks training/inference feature parity,
batch predictions, class-only/probability adapters, checksums, path restrictions,
validation, missing artifacts, currency safety and feedback persistence. These
fixtures establish software behavior, not real-world accuracy.

Optional browser verification uses Python Playwright and an installed Chromium:

```bash
python -m pip install playwright
python -m uvicorn website.main:app --host 127.0.0.1 --port 8011
# In another terminal:
python tests/browser_smoke.py
```

The browser script defaults to `/usr/bin/chromium`; set `CHROMIUM_PATH` to your
installed Chromium executable and `PRODUCTMATCH_TEST_URL` if using another local
URL. Run it against a development server. It checks
the actual startup state first, then intercepts browser requests with
synthetic fixtures to test linked interactions. No fixture predictions are stored
in the production database. Tests do not deploy or change the active model.

## Received Logistic Regression v1

The original artifact is preserved in
`trained_models/logistic_regression/logistic_regression_v1.joblib`. The supplied
training source is now at `models/logistic_regression/train.py`, with only its
CSV and Excel input paths adjusted. It runs training at module scope, so the
website never imports it.

`models/logistic_regression/features.py` is a separate adapter reproducing the
original eight features and their order. Feature and prediction parity were
checked against the original source in a separate sklearn 1.9.1 environment.
The 1.8.0 website keeps the SVM working and does not load the incompatible LR
artifact. LR remains experimental pending runtime compatibility; no artifact was
retrained, overwritten, or silently re-exported. See the algorithm folder's README
for exact input files, missing-value semantics and remaining deployment choices.
No real LR accuracy results have been supplied or inferred from these checks.

## Troubleshooting local Windows tests

Use an isolated environment with the pinned development requirements. The SVM
artifact was saved with scikit-learn 1.8.0; the reported local installation of
1.7.2 cannot load it under the version checks. From this project directory:

```bat
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements-dev.txt
python -c "import sklearn; print(sklearn.__version__)"
python -m unittest discover -s tests -v
```

The verified Render runtime uses Python 3.12.14. To match it locally, use an
installed Python 3.12 interpreter to create the environment (`py -3.12 -m venv
.venv`). An existing environment retains the Python version used to create it.

SQLite connections must be closed explicitly: its transaction context manager
commits or rolls back but does not close the file. Product queries, feedback,
asset validation and test fixtures now close connections deterministically.
Regression checks verify the downloaded database is closed before replacement,
and that feedback connections close on success, duplicate returns and errors.
This addresses the Windows WinError 32 file locks rather than hiding cleanup errors.

`No module named models.svm.train` means the source reorganization is not present in
your checkout, or you are outside the project root. Get the published update first;
`git pull` cannot retrieve changes that only exist in the cloud workspace.


## Evaluate the existing SVM (no retraining)

Keep `all_gs.json.gz` compressed in `data/`. From this project directory:

```bat
python -m scripts.evaluate_model
```

It prints match precision, recall, F1, accuracy and the confusion matrix using the
original saved threshold. It writes `evaluation.json`, `predictions.csv` and
`errors.csv` under `reports/evaluation/` (Git-ignored). `--data` selects another
labeled gzip JSON-lines file and `--output` chooses another report folder. There
is no fitting or threshold-search step. It does not update the website registry
or push results. Training/test separation still needs checking against the original
training data. LR remains unavailable until its exact preprocessing is supplied.

To train the SVM intentionally, use `python -m models.svm.train`. This is separate
from evaluation and saves to `trained_models/svm/`; it retains the existing training
script's behavior of replacing the selected version's output file. Preserve any
version you need before deliberately training again.


## Train SVM on every size and the combined data

With the virtual environment active, run from this project directory:

```bat
python -m models.svm.train_sizes
```

This loops over Small, Medium, Large and Extra Large, then trains a fifth model
using their combined unique pairs. It now uses versioned SVM v4 features and
validation F0.5 selection. The currently deployed combined artifact and registry
are not modified. This is a local experiment, not a Render build step.

Inputs in `data/`: `all_train.zip`, `all_valid.zip`, and `all_gs.json.gz`. Archives
stay compressed on disk. Runs are sequential to limit peak memory. Larger sets
can still require substantial RAM and training time; actual duration is unknown
until run on your computer. The union retains only the fields used by the SVM,
and does not keep four complete original dataframes in memory.

Each run creates a fresh timestamped folder under
`trained_models/svm/v4_size_experiments/` containing:

- `svm_small.joblib`, `svm_medium.joblib`, `svm_large.joblib`, `svm_xlarge.joblib`,
  and `svm_combined.joblib`.
- `comparison.csv`: validation/test metrics and training times for all five.
- `results.json`: selected settings, row/duplicate counts, source archive hashes,
  runtime versions, validation-based recommendation and completion status.
- `validation_pairs.csv`: the common holdout IDs.
- `quarantined_gold_overlap.csv` and `split_audit.json`: excluded test-overlap
  pairs, their source sizes, exclusion counts and original archive hashes.
- `errors_<size>.csv`: incorrect gold-test decisions for each model.

Generated experiments are Git-ignored. Existing runs are not overwritten. Copy an
approved version into the normal artifact folder and update the registry only
after reviewing it; the experiment does not activate a model automatically.

For a shorter first run:

```bat
python -m models.svm.train_sizes --sizes small medium
```

That trains Small, Medium and their union. Runs using different `--sizes` choices
can have different common validation cohorts, so keep comparisons within the same
run. There is no automatic checkpoint/resume; already saved models remain in the
partial run folder if interrupted.

### Comparison safeguards

- Validation IDs from all selected sizes define one common holdout, excluded from
  every training set, including the combined model. Parameters and threshold are
  selected on this common validation set. Its scores are tuning scores, not a
  second independent test.
- The new experimental models are not refitted on the held-out validation pairs.
  This differs from the old single-size command's final train+validation refit.
- Duplicate and reversed product pairs count once in training/validation.
  Inconsistent duplicate labels or modeled input features stop the run.
- Training/test pair overlap, including reversed pairs, is quarantined from
  every training set and the validation holdout before fitting. The gold test
  stays unchanged. Counts and excluded pairs are saved for audit. To stop instead,
  add `--overlap-policy error`. This does not establish product/cluster-disjoint
  generalization; shared individual products across different pairs still need
  separate investigation.
- All models and thresholds are fixed before gold-test results are calculated.
  The v4 recommendation uses validation F0.5 (precision breaks ties), not gold-test results.
- If subsets overlap completely, the combined union may equal XL. This is reported
  explicitly; combining repeated pairs does not create extra independent data.
- No benchmark performance is claimed from synthetic test fixtures. Full training
  archives were not available in the cloud workspace for a genuine five-model run.


### Switching SVM and Random Forest

The workspace's **Matching model** dropdown selects the actual feature pipeline and classifier. Switching re-scores the reference's candidates, resets the exploratory threshold, and clears stale pair predictions/reviews. Search retrieval and independent attribute comparisons remain shared. Each browser chooses its model independently; the combined SVM is the default. LR remains disabled pending its integration.

From the project folder, install the RF runtime once:

```bat
python -m scripts.setup_rf_runtime
python -m uvicorn website.main:app --reload
```

The existing Render build command (`pip install -r requirements.txt && python prepare_assets.py`) now installs RF's isolated runtime too. The start command stays the same. RF's original artifact is committed at `trained_models/RF/random_forest_v1.joblib`; its notebook is `models/RF/random_forest.ipynb`. Training inputs belong in `data/`. See `models/RF/README.md` for scope and missing-specification limitations. No model has been retrained.

API callers can pass `model_id` on `/predict` and `/predict/batch`, or as a query parameter on `/candidates/{id}`. `/feedback` recomputes the selected model's official prediction and stores its ID/version.


## Combined SVM default

The default model ID is `linear_svc_combined`, artifact `trained_models/svm/svm_combined.joblib`, saved threshold **+0.25**. The individual size experiments and original baseline remain saved for reproducibility, but only the combined model appears as **SVM** in the website selectors. Their test metrics and confusion matrices are populated in Model evaluation and independently reproduced on the 4,398 gold pairs. The training/audit handoff is in `docs/evaluation/svm_sizes_20261104/`.

If Render has `ACTIVE_MODEL` set to an older ID, change it to `linear_svc_combined` (or remove it to use the registry default). Legacy `MODEL_URL` and `MODEL_SHA256` still refer to the original `svm_small_v3.joblib`; they do not replace or change the combined artifact. Combined uses its committed SHA, with an optional scoped `SVM_COMBINED_SHA256` override. Keep the existing database download variables and build/start commands.

The combined model improves measured test precision to 79.34%, but still makes the two reported iPhone accessory false matches. See the documented examples before treating higher scores as proof of product identity. Threshold selection used validation F1, not these examples or the gold test. No model was retrained in this integration.


## Retrain SVM v4 (identity-aware features)

From the project folder in PowerShell:

```powershell
git pull --ff-only origin main
.\.venv\Scripts\python.exe -m models.svm.train_sizes
```

Keep `all_train.zip`, `all_valid.zip`, and `all_gs.json.gz` in `data/`. The command prints Small, Medium, Large, XL, and Combined results, then saves all five artifacts and comparison/audit reports under `trained_models/svm/v4_size_experiments/<timestamp>/`. It does not overwrite or activate the current website model. `python -m models.svm.train` now delegates to the same maintained workflow instead of the older refit-and-overwrite path.

V4 preserves single-character tokens, separates capacity/color/type/model evidence, represents title differences, and replaces the legacy generic number/model flags. Thresholds are selected from validation scores using **F0.5**, emphasizing precision over recall. This can reduce recall and does not guarantee a precision target. Training and validation metrics, shared product-ID counts, and the previously reported browser failures are printed. The known browser examples are diagnostics only, never training/tuning data and not a fresh test set. Gold-test scores still do not establish general phone/accessory accuracy.

New artifacts declare `feature_schema=tfidf_pair_v4`; future approved registry entries must use adapter `tfidf_pair_v4`. Old saved models keep their original feature adapter. Feature-code hashes, dataset hashes, and training/validation metrics are saved with the new artifacts. Review genuine held-out results and website examples before promoting a new artifact. Unknown or ambiguous product types are not automatically rejected; these are learned features, not hard-coded prediction overrides.
