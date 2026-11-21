# Catalog, website, and feedback

## Prepare the catalog

Put the catalog at `data/products.db`. To build it from the original WDC
corpus, put `offers_corpus_all_v2_non_norm.json.gz` in `data/`. From the project
root, with the Python environment active:

```bash
python -m scripts.build_database --inspect
python -m scripts.build_database --limit 50000
```

The limit applies to input records. Check `/health` for the final indexed count.
`PRODUCTMATCH_DATA_DIR` selects a different catalog directory.

## Use the dashboard

Search for a product, select a reference, and explore its scored candidates.
The list and chart cover retrieved candidates. Search uses lexical similarity
and may miss matches elsewhere in the catalog. Select a candidate to inspect
its attributes or run an official prediction. The exploratory slider changes
candidate classifications and price summaries. Official predictions use the
model's saved threshold. Run a prediction before voting on the pair.

The default model is Combined LinearSVC v4, registered as
`linear_svc_combined`. The picker also supports Logistic Regression and Random
Forest if their shared scikit-learn 1.9.1 runtime is installed. SVM uses
scikit-learn 1.8.0. The dashboard's evaluation tab currently shows v4's saved
benchmark; LR and RF results are available in [the evaluation archive](evaluation/lr_rf_shared_gold_20261104/).

## Deploy on Render

| Setting | Value |
| --- | --- |
| Branch | `main` |
| Root directory | `Georgia Tech Projects/CSYE 6262 Project` |
| Python | `PYTHON_VERSION=3.12.14` |
| Build command | `pip install -r requirements.txt && python prepare_assets.py` |
| Start command | `uvicorn website.main:app --host 0.0.0.0 --port $PORT` |
| Health check path | `/live` |

The root `prepare_assets.py` is Render's entry point. It prepares the catalog
and installs the isolated model runtime. Configure `DATABASE_URL` and
`DATABASE_SHA256` to download and verify a catalog during build. The current
release asset is [products.db](https://github.com/MichaelMaier225/Python_Lab/releases/download/productmatch-assets-v1/products.db).
The bundled v4 model already has a trusted checksum in the registry.
`ACTIVE_MODEL` can select a registered model. `PRODUCTMATCH_MODEL_DIR` selects
a different artifact directory. The legacy `MODEL_URL` and `MODEL_SHA256`
download settings are for Small V3.

After deployment, check `/health` for a loaded model and a nonzero catalog
count. Try a search and a prediction on the live site. FastAPI documents
request formats at `/docs`.

## Store and export feedback

ProductMatch stores the user's vote in `choice` and saves the two listings,
model prediction, and model version with it. On the live site, Render sends the
review to Supabase when both server-side settings are configured:

- `SUPABASE_URL` uses the project's `https://<project-ref>.supabase.co` URL.
- `SUPABASE_SECRET_KEY` uses an `sb_secret_` key from Supabase API Keys. Keep
  this value in Render's environment settings.

For a new Supabase project, enable the Data API and run this in SQL Editor:

```sql
create table if not exists public.feedback (
    request_id uuid primary key,
    pair_id text not null,
    model_id text not null,
    model_version text not null,
    choice text not null check (choice in ('match', 'different', 'unsure')),
    record jsonb not null,
    created_at timestamptz not null default now()
);

alter table public.feedback
    add column if not exists model_label text generated always as (
        case record #>> '{prediction,is_match}'
            when 'true' then 'match'
            when 'false' then 'different'
        end
    ) stored;

alter table public.feedback enable row level security;
revoke all on table public.feedback from public, anon, authenticated;
grant select, insert on table public.feedback to service_role;
```

Submit a vote and confirm it in **Supabase → Table Editor → feedback**.
Export CSV there and save it locally as `data/feedback_rows.csv`.

With both Supabase settings unset, the app creates `feedback.db` beside
`products.db` on the first vote. Set `PRODUCTMATCH_FEEDBACK_DIR` to place it
elsewhere. For a persistent SQLite deployment, point that variable to a
mounted disk. To move existing SQLite feedback, stop the app before copying
the database. Render's Free instance storage can be cleared on redeploy or
spin-down. Supabase keeps live feedback outside that filesystem.
