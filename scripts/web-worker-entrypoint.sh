#!/bin/sh -e

WORKER_COMMAND="gunicorn wsgi --bind 0.0.0.0:$PORT --timeout 1000 --worker-class=gevent --worker-connections=1000 --workers 9"

if [ -n "${COPILOT_ENVIRONMENT_NAME}" ]; then
    echo "Running in DBT Platform"
    WORKER_COMMAND="opentelemetry-instrument ${WORKER_COMMAND}
fi

eval $WORKER_COMMAND
