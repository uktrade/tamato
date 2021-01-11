web: gunicorn wsgi --bind 0.0.0.0:$PORT
worker: celery -A common.celery worker -l info
beat: celery -A common.celery beat