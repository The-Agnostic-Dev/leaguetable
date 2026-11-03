FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LEAGUETABLE_DB_PATH=/data/leaguetable.sqlite3

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /data && LEAGUETABLE_DEBUG=0 python manage.py collectstatic --noinput

EXPOSE 5118

# One worker: SQLite, and the league table is cached in process memory.
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py seed_demo && exec gunicorn config.wsgi --bind 0.0.0.0:5118 --workers 1 --threads 4"]
