#!/bin/sh -e

# Django Migrations
python manage.py makemigrations
python manage.py migrate
npm run build
python manage.py collectstatic --no-input
WORKER_COMMAND="gunicorn wsgi --bind 0.0.0.0:${PORT} --timeout 1000 --worker-class=gevent --worker-connections=1000 --workers 9"

echo "Starting worker using the command: ${WORKER_COMMAND}"

eval ${WORKER_COMMAND}
