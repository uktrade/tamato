import time

import django.apps
from django.db import connection

from common.models.mixins.description import DescribedMixin
from common.models.transactions import Transaction
from common.models.utils import override_current_transaction
from open_data.apps import APP_LABEL
from open_data.commodities import save_commodities_parent
from open_data.geo_areas import save_geo_areas
from open_data.models.utils import LOOK_UP_VIEW
from open_data.models.utils import ReportModel


def add_description(model, verbose=True):
    if model.update_description:
        if issubclass(model.shadowed_model, DescribedMixin):
            queryset = model.objects.select_related(
                "trackedmodel_ptr",
            ).all()
            start = time.time()
            for row in queryset:
                description = model.shadowed_model.objects.get(
                    pk=row.trackedmodel_ptr_id,
                ).get_description()
                row.description = description.description
                row.save()
            if verbose:
                print(f"Elapsed time {model._meta.db_table} {time.time() - start}")


def update_model(model, cursor):
    cursor.execute(f'TRUNCATE TABLE "{model._meta.db_table}"')
    print("Delete data")
    print(f"{model.update_table=}")
    if model.update_table:
        cursor.execute(model.update_query())
        fk_query_list = model.update_fk_queries()
        # The foreign keys are updated from TAP database,
        # not from the reporting area, so they can be updated at any time
        if fk_query_list:
            for query in fk_query_list:
                cursor.execute(query)

        if model.remove_obsolete:
            # print(model.create_remove_obsolete_row_query())
            cursor.execute(model.remove_obsolete_row_query())

        extra_query_list = model.extra_queries()

        if extra_query_list:
            for sql_query in extra_query_list:
                # print(sql_query)
                cursor.execute(sql_query)

    print("Completed")


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
    # The following are changes specific to different table.
    # They update fields using Django routines, created specifically for the task.
    # Unless there is a current transaction, reading the latest description will fail in a misterious way
    # Because this is called in a command, there is no transaction set"""
    tx = Transaction.objects.last()
    with override_current_transaction(tx):
        for model in config.get_models():
            add_description(model)
        save_commodities_parent(verbose)
        save_geo_areas(verbose)


def update_single_model(model):
    print(f'Starting update of "{model._meta.db_table}"')
    start_time = time.time()
    with connection.cursor() as cursor:
        update_model(model, cursor)
    elapsed_time = time.time() - start_time
    print(
        f'Completed update of "{model._meta.db_table}" in {elapsed_time} seconds',
    )
    add_description(model)
