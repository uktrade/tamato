import time

import django.apps
from django.db import connection

from open_data.apps import APP_LABEL
from open_data.models.utils import LOOK_UP_VIEW


def update_all_tables(verbose=False):
    config = django.apps.apps.get_app_config(APP_LABEL)

    with connection.cursor() as cursor:
        cursor.execute(f"REFRESH MATERIALIZED VIEW {LOOK_UP_VIEW};")
        for m in config.get_models():
            if verbose:
                print(f'Starting update of "{m._meta.db_table}"')
                start_time = time.time()
            cursor.execute(f'TRUNCATE TABLE "{m._meta.db_table}"')
            cursor.execute(m.create_update_query())
            fk_query_list = m.create_update_fk_queries()
            if fk_query_list:
                for query in fk_query_list:
                    cursor.execute(query)
            if verbose:
                elapsed_time = time.time() - start_time
                print(
                    f'Completed update of "{m._meta.db_table}" in {elapsed_time} seconds',
                )
