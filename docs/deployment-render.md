# Deploy SharePlate MVP on Render

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

### Demo data

Production startup never seeds demo accounts. Use `python manage.py seed_demo` only in an isolated development environment, and do not deploy its accounts or credentials.

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
