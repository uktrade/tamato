import logging
from datetime import date
from datetime import timedelta
from tempfile import NamedTemporaryFile

import apsw

from exporter.quotas_sqlite import utils
from exporter.quotas_sqlite.utils import get_api_query_date
from geo_areas.models import GeographicalAreaDescription
from quotas.models import QuotaDefinition
from quotas.models import QuotaOrderNumberOrigin

logger = logging.getLogger(__name__)


def normalise_loglevel(loglevel):
    """
    Attempt conversion of `loglevel` from a string integer value (e.g. "20") to
    its loglevel name (e.g. "INFO").

    This function can be used after, for instance, copying log levels from
    environment variables, when the incorrect representation (int as string
    rather than the log level name) may occur.
    """
    try:
        return logging._levelToName.get(int(loglevel))
    except:
        return loglevel


class QuotaSqliteExport:
    """Runs the export command against TAP data to extract quota data to SQLite."""

    def __init__(self, target_file: NamedTemporaryFile):
        self.target_file = target_file

    @staticmethod
    def column_names():
        """
        Produces a list of headers for the CSV.

        Returns:
            list: list of header names
        """
        quota_headers = [
            "quota_definition__sid",
            "quota__order_number",
            "quota__geographical_areas",
            "quota__headings",
            "quota__commodities",
            "quota__measurement_unit",
            "quota__monetary_unit",
            "quota_definition__description",
            "quota_definition__validity_start_date",
            "quota_definition__validity_end_date",
            # 'quota_definition__suspension_periods', from HMRC data
            # 'quota_definition__blocking_periods', from HMRC data
            # 'quota_definition__status', from HMRC data
            # 'quota_definition__last_allocation_date', from HMRC data
            "quota_definition__initial_volume",
            # 'quota_definition__balance', from HMRC data
            # 'quota_definition__fill_rate', from HMRC data
            "api_query_date",  # used to query the HMRC API
        ]

        return quota_headers

    def run(self):
        """
        Produces data for the quota export SQLite, from the TAP database.

        Returns:
            None: Operations performed and stored within the NamedTemporaryFile
        """

        quotas = QuotaDefinition.objects.latest_approved().filter(
            sid__gte=20000,
            valid_between__startswith__lte=date.today() + timedelta(weeks=52 * 3),
        )

        sqlite_conn = apsw.Connection(":memory:")
        sqlite_cursor = sqlite_conn.cursor()

        # create tables
        self.create_tables(sqlite_cursor)

        # populate tables
        self.populate_tables(sqlite_cursor, quotas)

        final_output_connection = apsw.Connection(self.target_file.name)
        with final_output_connection.backup("main", sqlite_conn, "main") as backup:
            backup.step()  # copy whole database in one go

        final_output_connection.close()
        sqlite_conn.close()


    def create_tables(self, sqlite_cursor):
        self.create_quotas_table(sqlite_cursor)
        self.create_geographical_areas_table(sqlite_cursor)
        self.create_quota_headings_table(sqlite_cursor)
        self.create_quota_commodities_table(sqlite_cursor)
        self.create_quota_definition_suspension_periods_table(sqlite_cursor)
        self.create_quota_definition_blocking_periods_table(sqlite_cursor)
        self.create_reports_table(sqlite_cursor)

    def populate_tables(self, sqlite_cursor, quotas):
        for quota in quotas:
            self.insert_quota_record(sqlite_cursor, quota)
            self.insert_geographical_areas_records(sqlite_cursor, quota)
            self.insert_quota_heading_records(sqlite_cursor, quota)
            self.insert_quota_commodities_records(sqlite_cursor, quota)
            self.insert_quota_suspension_period_records(sqlite_cursor, quota)
            self.insert_quota_blocking_period_records(sqlite_cursor, quota)

        # only one record in _reports - the sql to get the report
        self.insert_report_record(sqlite_cursor)

    def create_quotas_table(self, sqlite_cursor):
        sql = '''
        CREATE TABLE quotas (
            quota_definition__sid INTEGER NOT NULL,
            quota__order_number TEXT NOT NULL,
            quota__measurement_unit TEXT NOT NULL,
            quota__monetary_unit TEXT,
            quota_definition__description TEXT,
            quota_definition__validity_start_date DATE NOT NULL,
            quota_definition__validity_end_date DATE NOT NULL,
            quota_definition__status TEXT NOT NULL,
            quota_definition__last_allocation_date DATE,
            quota_definition__initial_volume REAL NOT NULL,
            quota_definition__balance REAL,
            quota_definition__fill_rate REAL,
            api_query_date DATE,
            PRIMARY KEY (quota_definition__sid)
        );
        
        CREATE UNIQUE INDEX idx__quotas__quota__order_number__quota_definition__validity_start_date
        ON quotas(quota__order_number, quota_definition__validity_start_date);
        
        CREATE INDEX idx__quotas__quota_definition__validity_start_date
        ON quotas(quota_definition__validity_start_date);
        
        CREATE INDEX idx__quotas__quota_definition__validity_end_date
        ON quotas(quota_definition__validity_end_date);
        
        CREATE INDEX idx__quotas__quota_definition__status
        ON quotas(quota_definition__status);
        
        CREATE INDEX idx__quotas__quota_definition__last_allocation_date
        ON quotas(quota_definition__last_allocation_date);'''
        sqlite_cursor.execute(sql)

    def create_geographical_areas_table(self, sqlite_cursor):
        sql = '''
        CREATE TABLE quota__geographical_areas (
            quota_definition__sid INTEGER NOT NULL,
            idx NOT NULL,
            geographical_area TEXT NOT NULL,
            PRIMARY KEY(quota_definition__sid, idx)
            FOREIGN KEY(quota_definition__sid) REFERENCES quotas(quota_definition__sid)
        );
        CREATE INDEX idx__quota__geographical_areas__geographical_area
        ON quota__geographical_areas(geographical_area);'''
        sqlite_cursor.execute(sql)

    def create_quota_headings_table(self, sqlite_cursor):
        sql = '''
        CREATE TABLE quota__headings (
            quota_definition__sid INTEGER,
            idx NOT NULL,
            heading TEXT NOT NULL,
            PRIMARY KEY(quota_definition__sid, idx)
            FOREIGN KEY(quota_definition__sid) REFERENCES quotas(quota_definition__sid)
        );
        CREATE INDEX idx__quota__headings__heading
        ON quota__headings(heading);
        '''
        sqlite_cursor.execute(sql)

    def create_quota_commodities_table(self, sqlite_cursor):
        sql = '''
        CREATE TABLE quota__commodities (
            quota_definition__sid INTEGER NOT NULL,
            idx NOT NULL,
            commodity TEXT NOT NULL,
            PRIMARY KEY(quota_definition__sid, idx)
            FOREIGN KEY(quota_definition__sid) REFERENCES quotas(quota_definition__sid)
        );
        CREATE INDEX idx__quota__commodities__commoditiy
        ON quota__commodities(commodity);
        '''
        sqlite_cursor.execute(sql)

    def create_quota_definition_suspension_periods_table(self, sqlite_cursor):
        sql = '''
        CREATE TABLE quota_definition__suspension_periods (
            quota_definition__sid INTEGER NOT NULL,
            idx NOT NULL,
            suspension_period_start DATE NOT NULL,
            suspension_period_end DATE NOT NULL,
            PRIMARY KEY(quota_definition__sid, idx)
            FOREIGN KEY(quota_definition__sid) REFERENCES quotas(quota_definition__sid)
        );
        CREATE INDEX idx__quota_definition__suspension_periods__suspension_period_start
        ON quota_definition__suspension_periods(suspension_period_start);
        CREATE INDEX idx_suspension_periods_suspension_period_end
        ON quota_definition__suspension_periods(suspension_period_end);'''
        sqlite_cursor.execute(sql)

    def create_quota_definition_blocking_periods_table(self, sqlite_cursor):
        sql = '''
        CREATE TABLE quota_definition__blocking_periods (
            quota_definition__sid INTEGER NOT NULL,
            idx NOT NULL,
            blocking_period_start DATE NOT NULL,
            blocking_period_end DATE NOT NULL,
            PRIMARY KEY(quota_definition__sid, idx)
            FOREIGN KEY(quota_definition__sid) REFERENCES quotas(quota_definition__sid)
        );
        CREATE INDEX idx__quota_definition__blocking_periods__blocking_period_start
        ON quota_definition__blocking_periods(blocking_period_start);
        CREATE INDEX idx__quota_definition__blocking_periods__blocking_period_end
        ON quota_definition__blocking_periods(blocking_period_end);'''
        sqlite_cursor.execute(sql)

    def create_reports_table(self, sqlite_cursor):
        sql = '''
        CREATE TABLE _reports (
            name TEXT PRIMARY_KEY,
            script TEXT NOT NULL
        );'''
        sqlite_cursor.execute(sql)

    def insert_quota_record(self, sqlite_cursor, quota):
        if quota.monetary_unit:
            quota_monetary_unit = quota.monetary_unit.description
        else:
            quota_monetary_unit = None

        sqlite_cursor.execute(
            '''
              INSERT INTO quotas(
                  quota_definition__sid,
                  quota__order_number,
                  quota__measurement_unit,
                  quota__monetary_unit,
                  quota_definition__description,
                  quota_definition__validity_start_date,
                  quota_definition__validity_end_date,
                  quota_definition__status,
                  quota_definition__last_allocation_date,
                  quota_definition__initial_volume,
                  quota_definition__balance,
                  quota_definition__fill_rate,
                  api_query_date
              ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                quota.sid,
                quota.order_number.order_number,
                quota.measurement_unit.abbreviation,
                quota_monetary_unit,
                quota.description,
                str(quota.valid_between.lower),
                str(quota.valid_between.upper),
                'Unknown',
                None,
                int(quota.initial_volume),
                None,
                None,
                get_api_query_date(quota)
            ),
        )

    def insert_geographical_areas_records(self, sqlite_cursor, quota):
        # get geo areas
        order_number_tracked_model_ids = quota.order_number.get_versions().values_list('trackedmodel_ptr_id', flat=True)
        origins = QuotaOrderNumberOrigin.objects.latest_approved().filter(order_number__trackedmodel_ptr_id__in=order_number_tracked_model_ids)

        i = 0
        for origin in origins:
            geo_area = origin.geographical_area.current_version
            if geo_area:
                geo_area_description_obj = GeographicalAreaDescription.objects.latest_approved().filter(described_geographicalarea=geo_area).order_by('-validity_start').first()
                if geo_area_description_obj is None:
                    geo_area_description = ''
                else:
                    geo_area_description = geo_area_description_obj.description
            else:
                geo_area_description = None
            i += 1
            sqlite_cursor.execute(
                '''
              INSERT INTO "quota__geographical_areas"(
                  "quota_definition__sid",
                  "idx",
                  "geographical_area"
              ) VALUES (?, ?, ?)
          ''',
                (
                    quota.sid,
                    i,
                    geo_area_description
                ),
            )

    def insert_quota_heading_records(self, sqlite_cursor, quota):
        i = 1
        item_ids = utils.get_goods_nomenclature_item_ids(quota)
        for heading in utils.get_goods_nomenclature_headings(item_ids):
            sqlite_cursor.execute(
                '''
              INSERT INTO "quota__headings"(
                  "quota_definition__sid",
                  "idx",
                  "heading"
              ) VALUES (?, ?, ?)
          ''',
                (quota.sid, i, heading),
            )
            i += 1

    def insert_quota_commodities_records(self, sqlite_cursor, quota):
        i = 1
        for commoditiy in utils.get_goods_nomenclature_item_ids(quota):
            sqlite_cursor.execute(
                '''
              INSERT INTO "quota__commodities"(
                  "quota_definition__sid",
                  "idx",
                  "commodity"
              ) VALUES (?, ?, ?)
          ''',
                (quota.sid, i, commoditiy),
            )
            i += 1

    def insert_quota_suspension_period_records(self, sqlite_cursor, quota):
        i = 1

        for suspension_dates in utils.get_suspension_periods_dates(quota):
            start_date = suspension_dates[0]
            end_date = suspension_dates[1]

            sqlite_cursor.execute(
                '''
              INSERT INTO "quota_definition__suspension_periods"(
                  "quota_definition__sid",
                  "idx",
                  "suspension_period_start",
                  "suspension_period_end"
              ) VALUES (?, ?, ?, ?)
          ''',
                (quota.sid, i, start_date, end_date),
            )
            i += 1

    def insert_quota_blocking_period_records(self, sqlite_cursor, quota):
        i = 1
        for blocking_dates in utils.get_blocking_periods_dates(quota):
            start_date = blocking_dates[0]
            end_date = blocking_dates[1]

            sqlite_cursor.execute(
                '''
              INSERT INTO "quota_definition__blocking_periods"(
                  "quota_definition__sid",
                  "idx",
                  "blocking_period_start",
                  "blocking_period_end"
              ) VALUES (?, ?, ?, ?)
          ''',
                (quota.sid, i, start_date, end_date),
            )
            i += 1

    def insert_report_record(self, sqlite_cursor):
        report_value = '''
        SELECT
            q.quota_definition__sid,
            q.quota__order_number,
            (
                SELECT
                    group_concat(g.geographical_area, '|')
                FROM
                    quota__geographical_areas g
                WHERE
                    g.quota_definition__sid = q.quota_definition__sid
                ORDER BY
                    g.idx
            ) AS quota__geographical_areas,
            (
                SELECT
                    group_concat(h.heading, '|')
                FROM
                    quota__headings h
                WHERE
                    h.quota_definition__sid = q.quota_definition__sid
                ORDER BY
                    h.idx
            ) AS quota__headings,
            (
                SELECT
                    group_concat(c.commodity, '|')
                FROM
                    quota__commodities c
                WHERE
                    c.quota_definition__sid = q.quota_definition__sid
                ORDER BY
                    c.idx
            ) AS quota__commodities,
            q.quota__measurement_unit,
            q.quota__monetary_unit,
            q.quota_definition__description,
            q.quota_definition__validity_start_date,
            q.quota_definition__validity_end_date,
            (
                SELECT
                    group_concat(s.suspension_period_start || ';' || s.suspension_period_end, '|')
                FROM
                    quota_definition__suspension_periods s
                WHERE
                    s.quota_definition__sid = q.quota_definition__sid
                ORDER BY
                    s.idx
            ) AS quota_definition__suspension_periods,
            (
                SELECT
                    group_concat(b.blocking_period_start || ';' || b.blocking_period_end, '|')
                FROM
                    quota_definition__blocking_periods b
                WHERE
                    b.quota_definition__sid = q.quota_definition__sid
                ORDER BY
                    b.idx
            ) AS quota_definition__blocking_periods,
            q.quota_definition__status,
            q.quota_definition__last_allocation_date,
            q.quota_definition__initial_volume,
            q.quota_definition__balance,
            q.quota_definition__fill_rate
        FROM
            quotas q
        ORDER BY
            q.quota__order_number, q.quota_definition__validity_start_date;'''

        sqlite_cursor.execute(
            '''
              INSERT INTO _reports(name, script) VALUES (?, ?)
            ''', ('quotas_including_current_volumes', report_value), )

