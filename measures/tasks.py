from common.celery import app
from measures.models import MeasuresBulkCreator


@app.task
def bulk_create_measures(measures_bulk_creator_pk: int) -> None:
    """Bulk create measures from serialized measures form data saved within an
    instance of MeasuresBulkCreator."""
    print(f"*** bulk_create_measures()")

    measures_bulk_creator = MeasuresBulkCreator.objects.get(pk=measures_bulk_creator_pk)
    measures = measures_bulk_creator.create_measures()

    print(f"*** measures_bulk_creator = {measures_bulk_creator}")
    print(f"*** Created measures {[m.pk for m in measures]}")
