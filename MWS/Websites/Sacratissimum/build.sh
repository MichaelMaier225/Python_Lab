#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

python -m pip install -r requirements.txt
python manage.py check
python manage.py collectstatic --noinput
# SQLite is initialized at runtime, not in the disposable build environment.
