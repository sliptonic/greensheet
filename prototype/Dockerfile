# Greensheet. One process, one SQLite file under /data, listens on 8080.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GREENSHEET_DEBUG=0 \
    GREENSHEET_DATA=/data \
    GREENSHEET_DB=/data/greensheet.sqlite3 \
    GREENSHEET_SITE_URL=http://localhost:8080 \
    GREENSHEET_DIGEST_HOUR=7 \
    PORT=8080

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN python manage.py collectstatic --noinput \
 && chmod +x docker/entrypoint.sh \
 && mkdir -p /data

VOLUME ["/data"]
EXPOSE 8080

ENTRYPOINT ["docker/entrypoint.sh"]
