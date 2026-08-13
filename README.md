# FoodBridge

> A role-based platform for coordinating safe surplus-food redistribution between donors, volunteers, and NGOs.

FoodBridge gives each participant a focused workspace for moving surplus food from a donor to a receiving NGO. It combines food-listing verification, pickup coordination, live volunteer location sharing, proof of delivery, and an optional payment workflow in one Django application.

## The flow

```text
Donor lists food
      |
Visual screening or NGO review
      |
Approved NGO accepts delivery
      |
Volunteer claims, collects, and delivers
      |
NGO confirms receipt and delivery
```

## Highlights

- Role-specific registration, authentication, profiles, and dashboards
- Food listings with photos, pickup windows, location details, storage notes, and allergen notes
- Visual food-screening workflow with approved, rejected, and human-review outcomes
- NGO approval gates for managing food listings and food-safety reviews
- Volunteer availability, service areas, location-sharing consent, and active-pickup protection
- Pickup lifecycle tracking: open, claimed, collected, delivered, cancelled
- Delivery and NGO receipt evidence uploads with access controls
- NGO takeover and release-to-queue paths when volunteer delivery is unavailable
- Optional Razorpay-oriented payment and volunteer payout models, disabled by default
- Docker, managed PostgreSQL, persistent uploads, health checks, and production security settings

## Built with

| Layer | Technology |
| --- | --- |
| Application | Django 6, Python |
| Database | SQLite for local development, PostgreSQL for production |
| Media | Pillow image validation and persistent media storage |
| Serving | Gunicorn and WhiteNoise |
| Deployment | Docker and Render Blueprint |

## Run locally

### 1. Create an environment and install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On Windows PowerShell, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
```

### 2. Configure local environment variables

```bash
cp .env.example .env
```

Local development uses SQLite by default. The application runs without payment credentials; leave `FOODBRIDGE_PAYMENTS_ENABLED=false` until a complete Razorpay integration has been configured and tested.

### 3. Migrate and start the application

```bash
python manage.py migrate
python manage.py runserver
```

Open <http://127.0.0.1:8000>.

## Demonstration data

Load an isolated, repeatable demonstration dataset:

```bash
python manage.py seed_demo
```

The command creates or refreshes only accounts whose e-mail begins with `demo.` and their linked records. Existing non-demo data remains unchanged.

| Role | E-mail |
| --- | --- |
| Donor | `demo.donor@foodbridge.local` |
| Volunteer | `demo.volunteer@foodbridge.local` |
| Approved NGO | `demo.ngo@foodbridge.local` |
| Pending NGO | `demo.pending-ngo@foodbridge.local` |

The command prints the shared local demo password and direct links to featured records. See the complete [manual demonstration guide](docs/demo-presentation.md).

## Production deployment

FoodBridge includes a minimal production configuration for Render:

- `Dockerfile` builds a non-root Gunicorn image.
- `config.settings_production` requires a secure secret, PostgreSQL, allowed hosts, HTTPS cookies, HSTS, and static-file compression.
- `render.yaml` provisions a web service, managed PostgreSQL, a persistent media disk, and the `/health/` health check.

For the full setup and release checklist, see [Deploy FoodBridge MVP on Render](docs/deployment-render.md).

### Required production variables

```text
DJANGO_SETTINGS_MODULE=config.settings_production
DJANGO_SECRET_KEY=<long random secret>
DATABASE_URL=<managed PostgreSQL internal URL>
DJANGO_ALLOWED_HOSTS=<your public hostname>
```

Add `DJANGO_CSRF_TRUSTED_ORIGINS=https://your-domain.example` when using a custom domain. Keep payment features disabled until the external payment provider is fully configured.

## Quality checks

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test -v 2
```

## Project layout

```text
accounts/     Authentication, roles, registration, and access control
donors/       Donor profiles and dashboard
donations/    Food listings, screening, NGO management, and receipts
volunteers/   Pickup assignment, delivery workflow, and location sharing
ngos/         NGO profile approval and dashboard
payments/     Optional payment and payout workflow
bridge/       Public pages, health endpoint, utilities, and demo command
config/       Django and production settings
```

## Safety notes

- FoodBridge’s visual screening is an assistance mechanism, not a food-safety guarantee.
- Uploaded food, delivery, and receipt evidence should be treated as private data.
- Do not commit `.env`, payment secrets, SMTP credentials, or production database URLs.
- Do not enable real payments before completing provider setup, webhook validation, and end-to-end testing.
