web: gunicorn wsgi --bind 0.0.0.0:$PORT --timeout 1000 --worker-class=gevent --worker-connections=1000 --workers 9
worker: celery -A common.celery worker -O fair -l info
beat: celery -A common.celery beat
flower: celery flower --basic_auth=$FLOWER_AUTH_USER:$FLOWER_AUTH_PASSWORD
