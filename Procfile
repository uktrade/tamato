#web: gunicorn wsgi --bind 0.0.0.0:$PORT --timeout 1000 --worker-class=gevent --worker-connections=1000 --workers 9
web: sh -c "source ./scripts/web-worker-entrypoint.sh"
worker: celery -A common.celery worker -O fair -l info -Q standard
beat: celery -A common.celery beat
rule-check-worker: celery -A common.celery worker -O fair -l info -Q rule-check --concurrency 1
importer-worker: celery -A common.celery worker -O fair -l info -Q importer
bulk-create-worker: celery -A common.celery worker -O fair -l info -Q bulk-create --concurrency 1
