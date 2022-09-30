from datetime import datetime

from django.db.transaction import atomic


def delete_measures():
    wb = WorkBasket.objects.prefetch_related("transactions").get(pk="418")
    tx = wb.transactions.last()
    measure_1 = Measure.objects.approved_up_to_transaction(tx).get(sid="20100104")
    measure_2 = Measure.objects.approved_up_to_transaction(tx).get(sid="20191713")
    for transaction in wb.transactions.all():
        if measure_1 in transaction.tracked_models.all():
            for model in transaction.tracked_models.all():
                if model != measure_1:
                    model.delete()
                    print("deleting models related to measure 1")

            transaction.tracked_models.all().delete()
            print("deleting measure 1")

            continue

        if measure_2 in transaction.tracked_models.all():
            for model in transaction.tracked_models.all():
                if model != measure_2:
                    model.delete()
                    print("deleting models related to measure 2")

            transaction.tracked_models.all().delete()
            print("deleting measure 2")


@atomic
def run_script():
    print("Starting to run scripts at ", datetime.now())
    delete_measures()
    print("Finished running scripts at", datetime.now())
