#!/usr/bin/env bash
# custom initialisation tasks
# ref - https://docs.cloudfoundry.org/devguide/deploy-apps/deploy-app.html

echo "---- RUNNING release tasks (.profile) ------"

if [[ "$MAINTENANCE_MODE" != "True" && "$MAINTENANCE_MODE" != "true" ]] ; then
  echo "---- Apply Migrations ------"
  python manage.py migrate
else
  echo "---- Skip Applying Migrations (Maintenance Mode) ------"
fi

echo "---- Collect Static Files ------"
OUTPUT=$(python manage.py collectstatic --noinput --clear)
mkdir -p ~/logs
echo ${OUTPUT} > ~/logs/collectstatic.txt
echo ${OUTPUT##*$'\n'}
echo "NOTE: the full output of collectstatic has been saved to ~/logs/collectstatic.txt"
echo "---- FINISHED release tasks (.profile) ------"
