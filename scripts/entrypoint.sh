#!/bin/sh
set -eu

python manage.py migrate --noinput

# Render's lower tiers do not provide an interactive Shell. Set
# SEED_DEMO_DATA=true for the first deployment to create the demo records.
# The existence check keeps normal restarts from resetting the demo workflow.
# It also verifies the demo photo files are still on disk: the free tier
# stores media in /tmp, which is wiped on every restart/redeploy, and the
# bundled photos are re-seeded so listings do not show broken images.
if [ "${SEED_DEMO_DATA:-false}" = "true" ]; then
  if ! python manage.py shell -c "
from accounts.models import User
from donations.models import Donation
from django.contrib.auth.hashers import check_password
from bridge.management.commands.seed_demo import DEMO_PASSWORD
users = list(User.objects.filter(email__startswith='demo.'))
users_ok = len(users) == 4 and all(check_password(DEMO_PASSWORD, user.password) for user in users)
photos_ok = all(
    donation.food_photo_overview.storage.exists(donation.food_photo_overview.name)
    for donation in Donation.objects.filter(donor__email__startswith='demo.').exclude(food_photo_overview='')
)
raise SystemExit(0 if users_ok and photos_ok else 1)"; then
    python manage.py seed_demo --allow-production
  fi
fi

python manage.py collectstatic --noinput

exec gunicorn config.wsgi:application \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers "${WEB_CONCURRENCY:-2}" \
  --timeout 60 \
  --access-logfile - \
  --error-logfile -
