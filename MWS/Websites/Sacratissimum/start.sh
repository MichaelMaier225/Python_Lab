#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# Run before Gunicorn accepts requests, including after free-instance restarts.
python manage.py migrate --noinput
if [[ "${SACRATISSIMUM_PREVIEW:-false}" == "true" ]]; then
    python manage.py load_demo_products --publish
fi
# One modest process fits the free preview; no Celery, Redis, disk or database service.
exec gunicorn config.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers 1 --threads 2 --timeout 60 \
    --access-logfile - --error-logfile -
