# Deploy FoodBridge MVP on Render

This deployment uses a Docker web service, managed PostgreSQL, and a one-gigabyte persistent disk for private food and delivery evidence. The blueprint uses Singapore for lower latency in India.

## Before deployment

1. Commit the production files and push the repository to GitHub or GitLab.
2. Keep `.env` out of the repository. Production secrets are supplied by Render.
3. The blueprint provisions a `starter` web service and `basic-256mb` Postgres database. Review Render's current pricing before creating the Blueprint.

## Create the service

1. In Render, choose **New > Blueprint** and select this repository.
2. Render detects [`render.yaml`](../render.yaml) and proposes the web service, database, and persistent media disk.
3. Supply the prompted optional secrets:
   - `GEMINI_API_KEY` to enable automatic food-photo screening. Without it, submissions safely enter human review when screening is unavailable.
   - SMTP values to enable password-reset e-mail. Until configured, do not advertise password reset as a production capability.
4. Create the Blueprint and wait for the `/health/` health check to pass.
5. Open the generated `onrender.com` URL. It is automatically accepted as an allowed host and trusted CSRF origin by `config.settings_production`.

### Load demo data without a Render Shell

If your Render plan does not include an interactive Shell, add this environment variable to the web service in Render:

```text
SEED_DEMO_DATA=true
```

Redeploy the service. The container runs `python manage.py seed_demo` after migrations on its first startup. It checks for the existing `demo.` users first, so later restarts do not recreate or reset the demo records. The command and the bundled food photographs are part of the Docker image, while uploaded images are written to the configured media directory.

After the first successful deployment, you can remove `SEED_DEMO_DATA` or set it to `false`; the seeded records remain in PostgreSQL.

## First release checks

1. Register a non-demo account for each role and verify role-based access.
2. Submit a small test donation, confirm its photos remain visible after a redeploy, then delete the test record if desired.
3. Verify password reset only after SMTP is configured.
4. Keep `FOODBRIDGE_PAYMENTS_ENABLED=false` until Razorpay OAuth, webhook, payout credentials, and payment testing are complete.

## Custom domain

After adding a custom domain in Render, add its hostname to `DJANGO_ALLOWED_HOSTS` and its HTTPS origin to `DJANGO_CSRF_TRUSTED_ORIGINS`, then redeploy.

## Local production-container smoke test

Set a real PostgreSQL `DATABASE_URL`, a secure `DJANGO_SECRET_KEY`, and `DJANGO_ALLOWED_HOSTS=localhost`, then run:

```bash
docker build -t foodbridge .
docker run --rm -p 8000:8000 \
  -e DATABASE_URL \
  -e DJANGO_SECRET_KEY \
  -e DJANGO_ALLOWED_HOSTS \
  -v foodbridge-media:/var/data \
  foodbridge
```
