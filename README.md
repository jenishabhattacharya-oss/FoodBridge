# FoodBridge

FoodBridge is a role-based Django platform that helps donors, volunteers, and NGOs coordinate the safe collection and delivery of surplus food.

## Overview

The platform guides a food donation from submission through safety verification, collection, delivery, and confirmation. It gives each participant a focused workspace while maintaining clear handoff states, delivery evidence, and access controls.

| Role | What they can do |
| --- | --- |
| Donors | Create food listings, provide pickup details, track donation status, and manage eligible listings. |
| Volunteers | Find eligible pickups, share availability and location, collect food, and record delivery evidence. |
| NGOs | Review food safety, accept food for volunteer delivery, manage direct takeovers, and confirm receipt or delivery. |

## Key features

- Role-specific registration, authentication, profiles, dashboards, and permissions
- Food listings with quantity, food condition, preparation time, pickup windows, location, and photos
- Optional visual food-screening workflow with Gemini, plus NGO human review when screening is unavailable or inconclusive
- Controlled donation lifecycle from available food to NGO acceptance, volunteer collection, delivery, and confirmation
- NGO takeover workflow for situations where no eligible volunteer is available
- Pickup assignment rules that prevent volunteers from holding multiple active pickups
- Location search, mapped pickup and destination details, and volunteer location-sharing controls
- Required delivery proof and NGO receipt uploads for completed handoffs
- Optional Razorpay-based payment and volunteer payout workflow, disabled by default
- Safe, repeatable demo data through a dedicated management command

## Donation flow

```text
Donor submits food listing
        |
        v
Visual screening or NGO review
        |
        v
Approved listing becomes available
        |
        +--> NGO accepts -> Volunteer claims -> Collects -> Delivers -> NGO confirms
        |
        +--> No eligible volunteer -> NGO takeover -> NGO uploads receipt
```

## Technology

- Python 3.13
- Django 6
- SQLite for local development; PostgreSQL supported for deployment
- Pillow for image uploads
- Gemini Vision for optional food-photo screening
- Razorpay for optional payment and payout integration
- WhiteNoise and Gunicorn for production serving
- Docker and Render deployment configuration

## Getting started

### Prerequisites

- Python 3.13 or later
- `pip`

### Local setup

```bash
git clone <your-repository-url>
cd FoodBridge

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
python manage.py migrate
python manage.py runserver
```

Open `http://127.0.0.1:8000/` in your browser.

On Windows PowerShell, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
```

### Configuration

Copy `.env.example` to `.env` and set only the services you plan to use. The default configuration uses SQLite and a console email backend, so neither a database server nor email provider is required for initial local development.

| Variable | Purpose |
| --- | --- |
| `DJANGO_SECRET_KEY` | Required secure application secret outside local development. |
| `DJANGO_DEBUG` | Enables development mode when set to `true`. |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hosts accepted by Django. |
| `GEMINI_API_KEY` | Enables visual food screening. Without it, unavailable screening safely routes listings to human review. |
| `FOODBRIDGE_PAYMENTS_ENABLED` | Enables payment-related pages and actions; defaults to `false`. |
| `PAYMENT_ENCRYPTION_KEY` | Required before storing encrypted payout or provider credentials. |
| `DATABASE_URL` | PostgreSQL connection URL for production settings. |
| SMTP variables | Enable password-reset emails in production. |

Never commit `.env`, payment credentials, or real payout details.

## Demo data

Load the safe demonstration dataset to explore each role and major handoff state:

```bash
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

The command prints the demo-account password and refreshes only data associated with the `demo.` email prefix. It does not remove normal user records or call external payment, mapping, geocoding, or Gemini services.

See [docs/demo-presentation.md](docs/demo-presentation.md) for the account list and a guided walkthrough.

## Testing and quality checks

Run the project checks, confirm no model migrations are missing, and execute the test suite:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test -v 2
```

## Deployment

The repository includes a Dockerfile and a Render Blueprint (`render.yaml`) that provision a Docker web service, PostgreSQL database, and persistent media disk. Production settings are in `config.settings_production`.

For deployment steps, environment requirements, and a local production-container smoke test, see [docs/deployment-render.md](docs/deployment-render.md).

## Project structure

```text
accounts/       Custom user model, authentication, and role registration
donors/         Donor profiles and dashboard
donations/      Food listings, verification, lifecycle, and NGO workflows
volunteers/     Volunteer profiles, pickup assignment, and delivery tracking
ngos/           NGO profiles, approval, and dashboards
payments/       Optional payment connections and volunteer payout records
bridge/         Public pages, health check, and location endpoints
templates/      Shared, public, authentication, and role-specific templates
static/         Stylesheets, JavaScript, and image assets
docs/           Demonstration and deployment guides
```

## Health check

The application exposes `GET /health/`, which returns an `ok` status when the database connection is available. The Render configuration uses this endpoint to monitor the deployed service.

## Security notes

- Keep `DJANGO_DEBUG=false` in production and provide a strong `DJANGO_SECRET_KEY`.
- Configure `DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_TRUSTED_ORIGINS` for every production domain.
- Keep payment functionality disabled until Razorpay credentials, webhook handling, and the full payment flow have been tested.
- Treat uploaded food photos, receipts, delivery evidence, and payout information as sensitive data.

## Contributing

1. Create a focused branch for your change.
2. Keep role permissions and donation-state transitions consistent with existing workflows.
3. Run the quality checks before opening a pull request.
4. Describe the user workflow covered by the change and include relevant test results.
