#!/bin/sh
set -e

python manage.py migrate --noinput

if [ -n "$GREENSHEET_OPERATOR_EMAIL" ]; then
  python manage.py ensure_operator "$GREENSHEET_OPERATOR_EMAIL"
fi

if [ "$GREENSHEET_SEED" = "1" ]; then
  python manage.py seed
fi

# Daily summaries: a small loop in the same container, once a day at
# GREENSHEET_DIGEST_HOUR in GREENSHEET_TZ. Set the hour to -1 to disable.
if [ "${GREENSHEET_DIGEST_HOUR:-7}" != "-1" ]; then
  python manage.py digest_loop &
fi

exec gunicorn config.wsgi:application \
  --bind "0.0.0.0:${PORT:-8080}" \
  --workers "${GREENSHEET_WORKERS:-2}" \
  --access-logfile - \
  --error-logfile -
