# Website setup

## Catalog

Put `products.db` in `data/`. To build it, put
`offers_corpus_all_v2_non_norm.json.gz` there and run:

```bash
python -m scripts.build_database --inspect
python -m scripts.build_database --limit 50000
```

The limit counts input rows. Check `/health` for the indexed count.
Use `PRODUCTMATCH_DATA_DIR` to change the catalog folder.

## Dashboard

Search, pick a pair, and run a prediction before voting. Search scores the
candidates it retrieves. The slider changes the candidate chart and price
summary. Official predictions use the saved threshold. API docs are at `/docs`.

The default is LinearSVC v4 (`linear_svc_combined`). LR and RF need
scikit-learn 1.9.1 in `.venv-rf`. SVM uses 1.8.0. The evaluation tab shows
v4. [LR and RF results](evaluation/lr_rf_shared_gold_20261104/)

## Render

| Setting | Value |
| --- | --- |
| Branch | `main` |
| Root directory | `Georgia Tech Projects/CSYE 6262 Project` |
| Python | `PYTHON_VERSION=3.12.14` |
| Build | `pip install -r requirements.txt && python prepare_assets.py` |
| Start | `uvicorn website.main:app --host 0.0.0.0 --port $PORT` |
| Health check | `/live` |

Set `DATABASE_URL` and `DATABASE_SHA256` to fetch the catalog during build.
[Catalog release](https://github.com/MichaelMaier225/Python_Lab/releases/download/productmatch-assets-v1/products.db)

V4 is bundled with its checksum. Use `ACTIVE_MODEL` to choose a registry
entry or `PRODUCTMATCH_MODEL_DIR` to change the artifact folder.
`MODEL_URL` and `MODEL_SHA256` are for the legacy Small V3 download.
After deploy, check `/health`, then try a search and a prediction.

## Supabase feedback

Set `SUPABASE_URL` to the project API URL and `SUPABASE_SECRET_KEY` to
the `sb_secret_` key in Render. For a new project, enable the Data API and
run this in Supabase SQL Editor:

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

Submit a vote and check **Table Editor → feedback**. `choice` is the vote
and `model_label` is the prediction. Save exports as `data/feedback_rows.csv`.

With both settings unset, votes go to `feedback.db` beside `products.db`.
Set `PRODUCTMATCH_FEEDBACK_DIR` to change that location or use a mounted disk.
Stop the app before copying an existing SQLite file. Render Free can clear
local files on spin-down or redeploy.
