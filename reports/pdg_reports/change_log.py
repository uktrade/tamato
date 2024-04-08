import csv

from datetime import datetime, timedelta
from tamato.workbaskets.models import WorkBasket

def script_for_certificates():
    wbs = WorkBasket.objects.filter(updated_at__date=datetime.datetime.today()-timedelta(days=1))

    csv_file_path = 'change_log_for_tariff.ods'

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