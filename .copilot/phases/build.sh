#!/usr/bin/env bash

set -ex

python -m pip install --upgrade pip
pip install -r requirements.txt

python manage.py makemigrations
npm install
npm run build
python manage.py collectstatic --no-input
