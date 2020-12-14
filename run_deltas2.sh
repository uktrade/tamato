set -e
echo running 12
python manage.py import_taric seed.xml --skip-split -f DIT200012.xml -d deltas2
echo running 13
python manage.py import_taric seed.xml --skip-split -f DIT200013.xml -d deltas2
echo running 14
python manage.py import_taric seed.xml --skip-split -f DIT200014.xml -d deltas2
echo running 15
python manage.py import_taric seed.xml --skip-split -f DIT200015.xml -d deltas2
echo running 16
python manage.py import_taric seed.xml --skip-split -f DIT200016.xml -d deltas2
echo running 17
python manage.py import_taric seed.xml --skip-split -f DIT200017.xml -d deltas2
echo running 18
python manage.py import_taric seed.xml --skip-split -f DIT200018.xml -d deltas2