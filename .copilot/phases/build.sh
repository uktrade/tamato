#!/usr/bin/env bash

set -e

python manage.py makemigrations
npm run build
python manage.py collectstatic --no-input
