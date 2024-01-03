from common.celery import app
from measures.models import CreateMeasures


@app.task
def bulk_create_measures(create_measures_pk: int):
    print("*" * 80)
    print(create_measures_pk)
    print("*" * 80)
    measure = CreateMeasures.objects.get(id=create_measures_pk)
    print(measure)
    print("*" * 80)
