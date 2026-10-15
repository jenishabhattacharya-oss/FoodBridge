# Development

## Requirements and setup

Install Python 3.13 or later. From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

Visit <http://127.0.0.1:8000/>. The default local configuration uses SQLite and console email. Third-party credentials are optional. On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1`.

## Configuration

Django reads local values from `.env`; production uses the hosting provider's environment settings. Do not commit real secrets. The full list of optional integration settings is in `.env.example`.

| Setting | What it controls |
| --- | --- |
| `DJANGO_DEBUG`, `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS` | Django development mode and core security settings. |
| `DATABASE_URL` | PostgreSQL URL used by production settings. |
| `GEMINI_API_KEY` | Optional food photo screening. Without it, use the human review flow. |
| `FOODBRIDGE_PAYMENTS_ENABLED` | Optional payment and payout routes; defaults to `false`. |
| `RAZORPAY_*`, `PAYMENT_ENCRYPTION_KEY` | Credentials and encryption key for the optional Razorpay integration. |
| `DJANGO_EMAIL_*` | SMTP configuration for production email, such as password resets. |
| `GEOCODING_*`, `MAP_TILE_*` | Location lookup and map tile configuration. |

## Demo data

To load sample records for a local walkthrough:

```bash
python manage.py seed_demo
```

The command prints the demo password and refreshes only the demonstration accounts whose email starts with `demo.` and linked sample records. Do not use sample accounts in a live environment. See the [demo walkthrough](demo-presentation.md) for steps.

## Useful commands

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

Use the test suite when changing application behavior. To deploy the project, follow the [deployment guide](deployment.md).
