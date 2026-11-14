# Deploy SharePlate MVP on Render

This deployment uses a Docker web service and managed PostgreSQL. The blueprint uses Singapore for lower latency in India. The current [`render.yaml`](../render.yaml) targets Render's **free tier**: the web service sleeps after 15 minutes of inactivity (about a minute to wake), and the free database expires 30 days after creation. Uploads live in `/tmp/media` and are lost on restart or redeploy. For real production use, change the service plan to `starter`, the database plan to `basic-256mb`, and add the persistent disk as described in the blueprint comments.

To keep the free service awake, `config/keepalive.py` runs a background thread in every gunicorn worker that pings the service's own `/health/` endpoint every 4 minutes (Render sets `RENDER_EXTERNAL_URL`, so no configuration is needed; disable with `KEEPALIVE_ENABLED=false`). A scheduled GitHub Actions workflow, `.github/workflows/keep-alive.yml`, pings `/health/` every 5 minutes as a fallback and visibility check — it needs a `SITE_URL` repository variable (see the workflow header) and is best-effort only, since GitHub can delay or drop scheduled runs.

## Before deployment

1. Commit the production files and push the repository to GitHub or GitLab.
2. Keep `.env` out of the repository. Production secrets are supplied by Render.
3. The blueprint provisions a `free` web service and `free` Postgres database (one per workspace). Review Render's current pricing before creating the Blueprint.

## Create the service

1. In Render, choose **New > Blueprint** and select this repository.
2. Render detects [`render.yaml`](../render.yaml) and proposes the web service and database.
3. Supply the prompted optional secrets:
   - `GEMINI_API_KEY` to enable automatic food-photo screening. Without it, submissions safely enter human review when screening is unavailable.
   - SMTP values to enable password-reset e-mail. Until configured, do not advertise password reset as a production capability.
4. Create the Blueprint and wait for the `/health/` health check to pass.
5. Open the generated `onrender.com` URL. It is automatically accepted as an allowed host and trusted CSRF origin by `config.settings_production`.

### Demo data

The blueprint sets `SEED_DEMO_DATA=true`, so a **fresh** production database is seeded automatically with the demo accounts and `[DEMO]` listings (shared password `FoodBridgeDemo123!`, printed in the deploy logs). The startup check only seeds when the demo users are missing, so normal restarts do not reset anything. Once the demo is no longer wanted, set `SEED_DEMO_DATA=false` in the Render dashboard and redeploy.

## First release checks

1. Register a non-demo account for each role and verify role-based access.
2. Submit a small test donation, confirm its photos remain visible after a redeploy, then delete the test record if desired.
3. Verify password reset only after SMTP is configured.
4. Keep `FOODBRIDGE_PAYMENTS_ENABLED=false` while configuring Razorpay sandbox credentials. Set `RAZORPAY_MODE=test`, use test Checkout keys, OAuth app credentials, the exact HTTPS OAuth callback URL, a sandbox webhook secret, and the RazorpayX test account number. Keep `PAYMENT_ENCRYPTION_KEY` stable: changing it makes previously stored OAuth and payout details unreadable.
5. Configure the webhook URL as `https://<your-domain>/payments/webhooks/razorpay/` and subscribe to `payment.captured`, `payment.failed`, `order.paid`, `payout.processed`, `payout.failed`, `payout.reversed`, and `payout.rejected`. Keep payments disabled until the complete sandbox walkthrough below succeeds.

### Razorpay sandbox verification

1. Register the OAuth callback URL in the Razorpay application and set the same value in `RAZORPAY_OAUTH_REDIRECT_URI`.
2. Enable `FOODBRIDGE_PAYMENTS_ENABLED=true` only in the sandbox environment after all credentials are configured.
3. Connect a test NGO account, create a delivered volunteer pickup, and confirm it from the NGO account. Verify the fixed ₹500 Checkout order uses the test key and completes with Razorpay's test payment method.
4. Confirm the app remains payment-pending after the browser callback and becomes payout-ready only after a valid captured-payment webhook.
5. Configure a volunteer test UPI or bank destination, submit the payout, and verify it reaches its final state through the payout webhook. Also exercise a failed payment, failed or reversed payout, invalid webhook signature, and repeated webhook delivery.
6. Disable payments again after testing. Do not place live credentials in local files committed to the repository.

## Custom domain

After adding a custom domain in Render, add its hostname to `DJANGO_ALLOWED_HOSTS` and its HTTPS origin to `DJANGO_CSRF_TRUSTED_ORIGINS`, then redeploy.

## Local production-container smoke test

Set a real PostgreSQL `DATABASE_URL`, a secure `DJANGO_SECRET_KEY`, and `DJANGO_ALLOWED_HOSTS=localhost`, then run:

```bash
docker build -t shareplate .
docker run --rm -p 8000:8000 \
  -e DATABASE_URL \
  -e DJANGO_SECRET_KEY \
  -e DJANGO_ALLOWED_HOSTS \
  -v shareplate-media:/var/data \
  shareplate
```
