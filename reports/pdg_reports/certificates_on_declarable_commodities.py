import csv

import os

print("Current directory:", os.getcwd())
from tamato.measures.models import MeasureCondition

def script_for_certificates():
    print('hello')
    measure_conditions_with_certificate = (
        MeasureCondition.objects
        .latest_approved()
        .filter(required_certificate__isnull=False)
    )
    print('working')

    result_array = []
    print('something')

    for measure_condition in measure_conditions_with_certificate:
        measure = measure_condition.dependent_measure.current_version
        print(measure)
        result_array.append({
            "commodity_code": measure.goods_nomenclature,
            "measure_type": measure.measure_type,
            "certificate": measure_condition.required_certificate,
            "measure_sid": measure.sid,
        })

        print(result_array)

    csv_file_path = 'certificates_on_declarable_commodities.csv'

    with open(csv_file_path, 'w', newline='') as csvfile:
        print('this is the thing')
        fieldnames = ["commodity_code", "measure_type", "certificate", "measure_sid"]

        csv_writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        print('we are at csv')

        csv_writer.writeheader()

        print('header has been written')

        csv_writer.writerows(result_array)

        print('eerrr')

    print(f"CSV file exported successfully to {csv_file_path}")