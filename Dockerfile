FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings_production

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . ./
RUN chmod +x scripts/entrypoint.sh && \
    mkdir -p /var/data/media /app/staticfiles && \
    chown -R app:app /app /var/data

USER app
EXPOSE 8000

CMD ["./scripts/entrypoint.sh"]
