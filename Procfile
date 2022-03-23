web: gunicorn wsgi --bind 0.0.0.0:$PORT --timeout 1000
worker: celery -A common.celery worker -l info
beat: celery -A common.celery beat
