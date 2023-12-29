from common.celery import app
from measures.models import CreateMeasures


@app.task()
def bulk_create_measures(create_measures_pk: int):
    measure = CreateMeasures.objects.get(pk=create_measures_pk)
