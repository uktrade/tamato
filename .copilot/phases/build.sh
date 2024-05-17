#!/usr/bin/env bash

set -ex

python manage.py makemigrations
npm install
npm run build
python manage.py collectstatic --no-input
