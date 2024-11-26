import time

import django.apps
from django.db import connection

from open_data.apps import APP_LABEL
from open_data.commodities import save_commodities_parent
from open_data.models.utils import LOOK_UP_VIEW
from open_data.models.utils import ReportModel


def update_model(model, cursor):
    cursor.execute(f'TRUNCATE TABLE "{model._meta.db_table}"')
    # print(model.create_update_query())
    cursor.execute(model.create_update_query())
    fk_query_list = model.create_update_fk_queries()
    if fk_query_list:
        for query in fk_query_list:
            cursor.execute(query)
    extra_query_list = model.extra_queries()

    if extra_query_list:
        for sql_query in extra_query_list:
            # print(sql_query)
            cursor.execute(sql_query)


def update_all_tables(verbose=False):
    config = django.apps.apps.get_app_config(APP_LABEL)

    with connection.cursor() as cursor:
        cursor.execute(f"REFRESH MATERIALIZED VIEW {LOOK_UP_VIEW};")
        for model in config.get_models():
            if issubclass(model, ReportModel):
                if verbose:
                    print(f'Starting update of "{model._meta.db_table}"')
                    start_time = time.time()
                update_model(model, cursor)
                if verbose:
                    elapsed_time = time.time() - start_time
                    print(
                        f'Completed update of "{model._meta.db_table}" in {elapsed_time} seconds',
                    )

    save_commodities_parent(verbose)


def update_single_model(model):
    print(f'Starting update of "{model._meta.db_table}"')
    start_time = time.time()
    with connection.cursor() as cursor:
        update_model(model, cursor)
    elapsed_time = time.time() - start_time
    print(
        f'Completed update of "{model._meta.db_table}" in {elapsed_time} seconds',
    )
