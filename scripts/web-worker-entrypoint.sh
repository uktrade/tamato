#!/bin/sh -e

WORKER_COMMAND="gunicorn wsgi --bind 0.0.0.0:${PORT} --timeout 4000 --worker-class=gevent --worker-connections=1000 --workers 3"

echo "Starting worker using the command: ${WORKER_COMMAND}"

eval ${WORKER_COMMAND}
