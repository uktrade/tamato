#!/usr/bin/env bash

set -e

python manage.py makemigrations
npm install
npm run build
python manage.py collectstatic --no-input
