# Deployment

The repository is configured for Render. The [Render guide](deployment-render.md) has the platform-specific setup and release checklist.

## Production layout

```mermaid
flowchart LR
    Visitor[Browser] --> Web[Render Docker web service<br/>Django and Gunicorn]
    Web --> DB[(Managed PostgreSQL)]
    Web --> Disk[(Persistent media disk)]
    Web --> Static[WhiteNoise static files]
    Web -. optional .-> Email[SMTP provider]
    Web -. optional .-> Gemini[Gemini API]
    Web -. optional .-> Pay[Razorpay]
```

The `render.yaml` Blueprint describes a Docker web service, a PostgreSQL database, and a persistent disk mounted at `/var/data`. Production settings are in `config/settings_production.py`. The container uses Python 3.13, installs `requirements.txt`, and starts with `scripts/entrypoint.sh`.

## What startup does

On each service start, the entrypoint applies database migrations, collects static files, and starts Gunicorn. The health check is `GET /health/`. Uploaded media is kept on the persistent disk so it survives a container restart or redeploy. Static files are served using WhiteNoise.

## Deploy with Render

1. Push the repository to a connected Git provider.
2. In Render, create a Blueprint from this repository and review the services described by `render.yaml`.
3. Provide any optional secrets you need, such as a Gemini key or SMTP credentials. Keep payments disabled unless the complete integration has been configured and checked.
4. Deploy and wait for the `/health/` check to pass.
5. Set any custom host in `DJANGO_ALLOWED_HOSTS` and its HTTPS origin in `DJANGO_CSRF_TRUSTED_ORIGINS`.
6. Check role registration, a test donation, media persistence, and email flows that you have configured.

The production settings require a secure `DJANGO_SECRET_KEY`, a PostgreSQL `DATABASE_URL`, and at least one allowed host. The Render-generated hostname is added automatically. Production runs with debug disabled and HTTPS protections enabled.

## Local container

A local production image requires a PostgreSQL URL and secure secret. For example:

```bash
docker build -t shareplate .
docker run --rm -p 8000:8000 \
  -e DATABASE_URL='postgresql://USER:PASSWORD@HOST:5432/DATABASE' \
  -e DJANGO_SECRET_KEY='replace-with-a-secure-secret' \
  -e DJANGO_ALLOWED_HOSTS=localhost \
  -v shareplate-media:/var/data \
  shareplate
```

This command connects to the PostgreSQL server named in the URL. For detailed payment sandbox setup, custom domains, and the first-release checklist, see [deployment-render.md](deployment-render.md).
