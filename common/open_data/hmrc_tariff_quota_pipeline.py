import time
import datetime

from requests.exceptions import ChunkedEncodingError

from additional_codes.models import AdditionalCode
from certificates.models import Certificate
from commodities.models import GoodsNomenclature
from common.business_rules import BusinessRule
from common.business_rules import BusinessRuleViolation
from quotas.models import QuotaDefinition, QuotaOrderNumber, QuotaOrderNumberOrigin, QuotaSuspension, QuotaBlocking
import requests

HMRC_QUOTAS_API = 'https://www.trade-tariff.service.gov.uk/api/v2/quotas/search'
MAX_REQUEST_RETRIES = 5

# This takes over responsibility from data flow : HMRCTariffsPipeline to provide the same result into data workspace.

# 1: get all live quota definitions
quota_definitions = QuotaDefinition.objects.latest_approved()


# 2: query HMRC for each quota

# 3: construct dataset

# 4: write dataset to CSV

# 5: upload to S3

# 6: ?? sent notification to DW? or should pipeline



def fetch_data_from_api_hmrc(
    target_db: str, table_name: str, source_url: str, **kwargs
):
    # From HMRC's point of view, a quota is active on a date that is
    #
    # - between its validity_start and validity_end dates
    # - and has at least one active measure, i.e. the date is between the measure's validity_start
    #   and validity_end dates
    #
    # Note the measures don't have to end on the end date of the quota, but at least one measure
    # does have to coincide with the start of the quota. So, we don't need to use measures to
    # determine the start of a quota, but we do to work out its effective end.
    #
    # Also, before a quota is active, i.e. before its validity_start, we don't want to query HMRC's
    # API for it, since it could return the balance for a previous definition

    # query quota definitions
    # where
    #  - quota definition valid between start date >= todays date
    #  - quota definition sid => 20000

    quotas_sql = '''
        SELECT
          dbt.tariff__quota_definitions.sid,
          current_order_number as order_number,
          CASE
            WHEN CURRENT_DATE < dbt.tariff__quota_definitions.validity_start THEN
              NULL
            ELSE
              LEAST(
                dbt.tariff__quota_definitions.validity_end,
                MAX(LEAST(measures.validity_end, 'infinity'::date)) FILTER (WHERE measures.validity_start <= CURRENT_DATE),
                CURRENT_DATE
              )
          END AS query_date
        FROM
          dbt.tariff__quota_definitions
          INNER JOIN dbt.tariff__common_tracked_models AS definition_tracked_models ON dbt.tariff__quota_definitions.trackedmodel_ptr_id = definition_tracked_models.id
          INNER JOIN dbt.tariff__common_version_groups AS definition_version_groups ON dbt.tariff__quota_definitions.trackedmodel_ptr_id = definition_version_groups.current_version_id
          INNER JOIN (
              SELECT dbt.tariff__quota_order_numbers.trackedmodel_ptr_id as original_order_number_id,
                     current_order_number.trackedmodel_ptr_id as current_order_number_id,
                     dbt.tariff__quota_order_numbers.order_number as current_order_number,
                     order_number_tracked_models.update_type as order_number_tracked_models_update_type

              FROM dbt.tariff__quota_order_numbers
              INNER JOIN dbt.tariff__common_tracked_models AS order_number_tracked_models ON dbt.tariff__quota_order_numbers.trackedmodel_ptr_id = order_number_tracked_models.id
              INNER JOIN dbt.tariff__common_version_groups AS order_number_version_groups ON order_number_tracked_models.version_group_id = order_number_version_groups.id
              INNER JOIN dbt.tariff__quota_order_numbers AS current_order_number ON current_order_number.trackedmodel_ptr_id = order_number_version_groups.current_version_id
          ) original_to_current_order_number on dbt.tariff__quota_definitions.order_number_id = original_to_current_order_number.original_order_number_id
          -- LEFT OUTER rather than INNER since quotas we want to include may not have a measure
          LEFT OUTER JOIN (
            SELECT
              order_number_id,
              validity_start,
              validity_end
            FROM
              dbt.tariff__measures
              INNER JOIN dbt.tariff__common_tracked_models AS measure_tracked_models ON dbt.tariff__measures.trackedmodel_ptr_id = measure_tracked_models.id
              INNER JOIN dbt.tariff__common_version_groups AS measure_version_groups ON dbt.tariff__measures.trackedmodel_ptr_id = measure_version_groups.current_version_id
            WHERE
              NOT measure_tracked_models.update_type = 2
          ) measures ON original_order_number_id = measures.order_number_id
        WHERE
          dbt.tariff__quota_definitions.sid >= 20000
          AND NOT definition_tracked_models.update_type = 2
          AND NOT order_number_tracked_models_update_type = 2
        GROUP BY
          dbt.tariff__quota_definitions.sid,
          current_order_number,
          dbt.tariff__quota_definitions.validity_start,
          dbt.tariff__quota_definitions.validity_end
        ORDER BY
          current_order_number
    '''

    quotas = query_results(target_db, quotas_sql)
    balances = balances_iter(source_url, quotas)
    pages = paginate(balances)

    s3 = S3Data(table_name, kwargs["ts_nodash"])
    for page_num, page in enumerate(pages, start=1):
        s3.write_key(f"{page_num:010}.json", page, jsonify=True)

def query_results(target_db, sql):
    connection = None
    try:
        connection = PostgresHook(postgres_conn_id=target_db).get_conn()
        with connection.cursor() as cursor:
            cursor.execute(sql)
            yield from cursor
    finally:
        if connection is not None:
            connection.close()

def paginate(rows):
    page = []
    for row in rows:
        page.append(row)
        if len(page) == 1000:
            yield page
            page = []
    if page:
        yield page

def query_results_tap():
    # query quota definitions
    # where
    #  - quota definition valid between start date >= today's date
    #  - quota definition sid => 20000
    quota_definitions = QuotaDefinition.objects.latest_approved().filter(
        sid__gte=20000,
        valid_between__startswith__lte=datetime.date.today()
    ).values_list(
        'sid', 'order_number__order_number', 'valid_between__startswith',
    )

    return quota_definitions


def hmrc_api_rows_iter(url, params):
    page_number = 0
    while True:
        page_number += 1
        # handle flaky ConnectionResetError by retrying
        tries = 0
        while True:
            try:
                response = requests.get(url, params={**params, "page": page_number})
                if response.status_code == 500 and tries < MAX_REQUEST_RETRIES:
                    tries += 1
                    time.sleep(1)
                    continue
                break
            except (ChunkedEncodingError, ConnectionError):
                if tries < MAX_REQUEST_RETRIES:
                    tries += 1
                    time.sleep(1)
                    continue
                raise

        # HMRC's API can return a 500 for some order numbers. The best we can do
        # is return a dummy row without data so it still ends up in the database
        if response.status_code == 500:
            body = {
                'data': [
                    {
                        'attributes': {
                            'last_allocation_date': None,
                            'balance': None,
                        }
                    }
                ]
            }
        else:
            assert response.status_code == 200
            body = response.json()

        # Final page
        if not body['data']:
            break

        for row in body['data']:
            yield row['attributes']


def balances_iter(url, quotas):
    for quota in quotas:
        sid, order_number, query_date = quota
        if query_date is None:
            yield {
                'quota_definition_sid': sid,
                'last_allocation_date': None,
                'balance': None,
            }
            continue

        year, month, day = str(query_date).split('-')
        rows = hmrc_api_rows_iter(
            url,
            {
                'order_number': order_number,
                'year': year,
                'month': month,
                'day': day,
            },
        )
        for row in rows:
            yield {
                'quota_definition_sid': sid,
                'last_allocation_date': row['last_allocation_date'],
                'balance': row['balance'],
            }


def paginate(rows):
    page = []
    for row in rows:
        page.append(row)
        if len(page) == 1000:
            yield page
            page = []
    if page:
        yield page

