import time

from django.db import connection

from common.models.transactions import Transaction
from common.models.utils import override_current_transaction
from open_data.models import ReportMeasure
from open_data.models import ReportMeasureCondition


def update_measure_components(verbose):
    # Unless there is a current transaction, reading the latest description will fail in a misterious way
    # Because this is called in a command, there is no transaction set"""
    counter = 0
    tx = Transaction.objects.last()
    start = time.time()
    if verbose:
        print("Updating measure components")
    with override_current_transaction(tx):
        measures_qs = (
            ReportMeasure.objects.filter(sid__gte=20000000)
            .only("trackedmodel_ptr")
            .select_related("trackedmodel_ptr")
        )
        component_list = []
        for measure in measures_qs:
            counter += 1
            if counter % 1000 == 0:
                print(f"Measure count {counter}")
            # comp_counter = 0
            for (
                component
            ) in (
                measure.trackedmodel_ptr.conditions.latest_approved().with_reference_price_string()
            ):
                # comp_counter += 1
                # print(f"    Condition count {comp_counter}")
                component_list.append(
                    ReportMeasureCondition(
                        trackedmodel_ptr_id=component.trackedmodel_ptr_id,
                        sid=component.sid,
                        component_sequence_number=component.component_sequence_number,
                        duty_amount=component.duty_amount,
                        action_id=component.action_id,
                        condition_code_id=component.condition_code_id,
                        condition_measurement_id=component.condition_measurement_id,
                        dependent_measure_id=measure.trackedmodel_ptr_id,
                        monetary_unit_id=component.monetary_unit_id,
                        required_certificate_id=component.required_certificate_id,
                        reference_price=component.reference_price_string,
                    ),
                )

    ReportMeasureCondition.objects.bulk_create(component_list)
    print("Completed Measure condition creation")
    #     The required_certificate_id is not updated when the certificate is updated
    #     In the UI it works because the certificate is selected using the SID and
    #     'approved to last Transaction'. In data workspace works because when a
    #     certificate is updated, only the validity is changed so even if the data is not read from the latest,
    #     the SID is correct. I am not sure what is the best way to fix this!!!
    #     I'll try patching the required_certificate_id and hope for the best
    fk_query_list = ReportMeasureCondition.update_fk_queries()
    if fk_query_list:
        with connection.cursor() as cursor:
            for query in fk_query_list:
                cursor.execute(query)

    if verbose:
        print(f"Elapsed time {time.time() - start}")


def update_measure(verbose):
    # Unless there is a current transaction, reading the latest description will fail in a misterious way
    # Because this is called in a command, there is no transaction set"""
    tx = Transaction.objects.last()
    start = time.time()
    if verbose:
        print("Updating measure")

    with override_current_transaction(tx):
        measures_qs = (
            ReportMeasure.objects.filter(sid__gte=20000000)
            .only("trackedmodel_ptr", "duty_sentence")
            .select_related("trackedmodel_ptr")
        )
        for measure in measures_qs:
            duty_sentence = measure.trackedmodel_ptr.duty_sentence
            if duty_sentence:
                measure.duty_sentence = duty_sentence
                measure.save()

    if verbose:
        print(f"Elapsed time {time.time() - start}")
