#!/bin/sh -e

if [ -n "${COPILOT_ENVIRONMENT_NAME}" ]; then
    echo "Running in DBT Platform"
    opentelemetry-instrument gunicorn wsgi --bind 0.0.0.0:$PORT --timeout 1000 --worker-class=gevent --worker-connections=1000 --workers 9
else
    echo "Running in Cloud Foundry"
    gunicorn wsgi --bind 0.0.0.0:$PORT --timeout 1000 --worker-class=gevent --worker-connections=1000 --workers 9
fi