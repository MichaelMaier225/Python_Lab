# Free Render preview for Tanner

This is a disposable showcase, not a live shop. No cloud resources have been created by this configuration. The staged commerce features remain disabled in disposable preview mode; see [COMMERCE.md](COMMERCE.md). Use the included `onrender.com` hostname, a **Free** Python web service, and temporary SQLite. Do not add a database service, persistent disk, Redis, paid instance, custom domain or any add-on.

## Manual setup in Render (after merging these files into GitHub)

1. In Render, choose **New → Web Service**, connect `MichaelMaier225/Python_Lab`, and select the branch containing this change (normally `main` after you merge).
2. Set the following service fields:

   | Setting | Value |
   | --- | --- |
   | Name | `sacratissimum-preview` (or another available name) |
   | Runtime | Python |
   | Root Directory | `MWS/Websites/Sacratissimum` |
   | Build Command | `bash build.sh` |
   | Start Command | `bash start.sh` |
   | Instance Type | **Free** |
   | Health Check Path | `/` |
   | Auto-Deploy | **Off** (manual deploys only) |

3. Set these environment variables in Render, never in Git:

   | Variable | Value |
   | --- | --- |
   | `PYTHON_VERSION` | `3.12.14` |
   | `DJANGO_DEBUG` | `false` |
   | `DJANGO_SECRET_KEY` | A new, securely generated secret of at least 50 characters; keep it private. |
   | `SACRATISSIMUM_PREVIEW` | `true` |
   | `SACRATISSIMUM_DB_PATH` | `/tmp/sacratissimum-preview.sqlite3` |

   You can generate the secret locally with the following command and paste its output directly into Render's **secret environment variable** field. Do not put it in a commit, screenshot, chat, or public log:

   ```bash
   python -c "from secrets import token_urlsafe; print(token_urlsafe(64))"
   ```

   Render supplies `PORT`, `RENDER=true` and `RENDER_EXTERNAL_HOSTNAME` itself. **Do not manually override them.** `DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_TRUSTED_ORIGINS` can be left unset: the app automatically adds only the exact Render-assigned hostname and its HTTPS origin, including any suffix Render adds. Do not use `*` or `.onrender.com` as an allowed host. No API keys, payment keys or email credentials are needed.

4. Review the configuration and confirm the instance type is **Free** before choosing Render's deployment action. Nothing in this repository performs that action for you.
5. After the build and startup finish, use the **actual HTTPS `onrender.com` URL shown by Render**. The requested name is not a guarantee that a particular hostname is available. Open the homepage, collection and a demo product, then share that assigned URL with Tanner.

Free instances can sleep when idle and take time to wake. The preview is subject to Render's free usage limits. Keep the service on Free; no upgrade is necessary for this configuration.

## Optional Blueprint instead of manual entry

The repository-root `render.yaml` describes the same single free service with the correct root directory, scripts and variables. It generates a secret with Render's `generateValue` mechanism, not a committed value. It declares **no disks, databases or other services** and disables automatic deploys. You can review this file in a future Render Blueprint setup instead of creating the service manually. Do not create both services.

## Exactly what runs

Build (`bash build.sh`):

1. Install `requirements.txt` (including pinned Gunicorn and WhiteNoise).
2. Run Django system checks.
3. Run `collectstatic --noinput` with the compressed manifest backend in production.

Start (`bash start.sh`, on each new process/container):

1. `python manage.py migrate --noinput`
2. `python manage.py load_demo_products --publish` when `SACRATISSIMUM_PREVIEW=true`.
3. `exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --workers 1 --threads 2 --timeout 60 --access-logfile - --error-logfile - --access-logformat '%(m)s %(s)s %(b)s %(L)s'`

The demo loader uses stable unique slugs and preserves existing records, so repeat starts do not duplicate products or variants. If the ephemeral SQLite file disappears, the next start recreates the schema and three labeled demo products with fifteen variants. Neither script creates an admin user or default password. Production admin requires an enrolled authenticator. Customer signup, bag and checkout return an unavailable page in disposable preview mode; no customer information should be stored there. No pre-deploy command or paid persistent disk is needed.

`SACRATISSIMUM_PREVIEW` defaults to false outside the preview. Running Django locally does not automatically publish demo content or require a production secret.

## Static artwork and disposable data

- All demo artwork is already in `store/static/store/images/`: `campaign-charcoal.webp` (optimized for phones; original PNG also retained), `campaign-ivory.svg`, `concept-sacred.svg`, `concept-walk.svg`, and `concept-abide.svg`. It is committed, not fetched from a third party or uploaded through admin at deploy time.
- Demo cards and detail pages refer to these static assets. WhiteNoise serves the collected, hashed files with `DEBUG=False`, including CSS, JavaScript, favicon and Django admin assets.
- Demo records are labeled fictional concepts with illustrative prices. There is no checkout.
- SQLite lives at `/tmp/sacratissimum-preview.sqlite3`. Assume all runtime database changes and uploaded files can disappear during restarts/redeploys. Do not store valuable data or customer information in this preview.
- WhiteNoise is for static files, not user uploads. Production `/media/` serving is intentionally not enabled. Do not replace the bundled demo artwork with admin uploads for Tanner's preview.
- There is no public demo administrator. If you later deliberately create an admin account, use a private unique password and expect the account and its edits to be lost when storage resets. Admin access is not required to share or browse this preview.

## HTTPS and deployment checks

Production requires `DJANGO_SECRET_KEY`; the app fails closed without it. Render cannot start with `DJANGO_DEBUG=true`. The exact assigned hostname is allowed, HTTPS is enforced, secure cookies are enabled, and Render's `X-Forwarded-Proto` header is trusted only when `RENDER=true` to avoid redirect loops behind its TLS proxy.

`python manage.py check --deploy` reports one deliberate advisory, **security.W004**, because HSTS/preloading is not enabled for this disposable preview. HTTPS redirects and secure cookies remain enabled. The warning is not silenced. HSTS can be evaluated separately when configuring a permanent production site.

## Validation without deploying

Normal local checks (no production variables needed):

```bash
python -m pip install -r requirements.txt
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

For a production-like integration check on Linux/macOS/WSL with Bash and the project's venv activated:

```bash
python scripts/verify_render_preview.py
```

This runs the **actual build and start scripts** locally, with `DEBUG=False`, a temporary random secret (never printed), temporary SQLite databases and a local Gunicorn port. It checks all pages, collected/hash-named CSS/JavaScript and both hero/demo images through WhiteNoise, CSS gzip compression, host rejection, HTTP-to-HTTPS redirects, 404 handling, and the absence of default accounts. It starts twice against the same database to check idempotency, then deletes that test database and starts again to verify recovery from lost free-instance storage. Only the processes and temporary database it owns are removed. It does not call Render, provision resources, deploy, or contact Tanner.

Validation in Render itself remains a future step after you choose to deploy. Render's account/plan availability and control-panel behavior cannot be established by the local smoke test.
