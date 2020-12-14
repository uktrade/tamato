set -e
echo running 9
python manage.py import_taric seed.xml --skip-split -f DIT200009.xml -d deltas
echo running 10
python manage.py import_taric seed.xml --skip-split -f DIT200010.xml -d deltas
echo running 11
python manage.py import_taric seed.xml --skip-split -f DIT200011.xml -d deltas
echo running 12
python manage.py import_taric seed.xml --skip-split -f DIT200012.xml -d deltas
echo running 13
python manage.py import_taric seed.xml --skip-split -f DIT200013.xml -d deltas
echo running 14
python manage.py import_taric seed.xml --skip-split -f DIT200014.xml -d deltas
echo running 15
python manage.py import_taric seed.xml --skip-split -f DIT200015.xml -d deltas
echo running 16
python manage.py import_taric seed.xml --skip-split -f DIT200016.xml -d deltas
echo running 17
python manage.py import_taric seed.xml --skip-split -f DIT200017.xml -d deltas
echo running 18
python manage.py import_taric seed.xml --skip-split -f DIT200018.xml -d deltas