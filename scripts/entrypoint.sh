#!/bin/sh
set -eu

python manage.py migrate --noinput

# Render's lower tiers may not provide an interactive Shell. Set
# SEED_DEMO_DATA=true for the first deployment to create the demo records.
# The existence check keeps normal restarts from resetting the demo workflow.
if [ "${SEED_DEMO_DATA:-false}" = "true" ]; then
  if ! python manage.py shell -c "from accounts.models import User; from django.contrib.auth.hashers import check_password; from bridge.management.commands.seed_demo import DEMO_PASSWORD; users=list(User.objects.filter(email__startswith='demo.')); raise SystemExit(0 if len(users) == 4 and all(check_password(DEMO_PASSWORD, user.password) for user in users) else 1)"; then
    python manage.py seed_demo
  fi
fi

python manage.py collectstatic --noinput

exec gunicorn config.wsgi:application \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers "${WEB_CONCURRENCY:-2}" \
  --timeout 60 \
  --access-logfile - \
  --error-logfile -
