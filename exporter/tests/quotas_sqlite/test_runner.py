from datetime import date
from datetime import timedelta
from tempfile import NamedTemporaryFile
import apsw

import pytest

from common.tests import factories
from common.util import TaricDateRange
from exporter.quotas_sqlite.runner import QuotaSqliteExport
from exporter.quotas_sqlite import utils


pytestmark = pytest.mark.django_db


@pytest.mark.exporter
class TestQuotaSqliteExport:
    target_class = QuotaSqliteExport

    def get_target(self):
        ntf = NamedTemporaryFile()
        return self.target_class(ntf)

    def test_init(self):
        ntf = NamedTemporaryFile()
        target = self.target_class(ntf)
        assert target.target_file == ntf

    def test_column_names(self):
        target = self.get_target()
        assert len(target.column_names()) == 13

    def test_run(self):
        quota = factories.QuotaDefinitionFactory(
            valid_between=TaricDateRange(
                date.today() + timedelta(days=-365),
                date.today() + timedelta(days=10),
            ),
            sid=20001,
            order_number__order_number="056789",
        )

        factories.MeasureFactory(
            order_number=quota.order_number,
            valid_between=TaricDateRange(
                date.today() + timedelta(days=-365),
            ),
            goods_nomenclature__description__description="gggg",
            goods_nomenclature__item_id="0102030405",
        )

        factories.MeasureFactory(
            order_number=quota.order_number,
            valid_between=TaricDateRange(
                date.today() + timedelta(days=-365),
            ),
            goods_nomenclature__description__description="hhhh",
            goods_nomenclature__item_id="0102778899",
        )

        factories.GoodsNomenclatureFactory(
            item_id="0102000000",
            description__description="zzz",
        )

        with NamedTemporaryFile() as ntf:
            target = self.target_class(ntf)
            target.run()
            sqlite_conn = apsw.Connection(ntf.name)
            sqlite_cursor = sqlite_conn.cursor()
            quotas = sqlite_cursor.execute('SELECT * FROM quotas').fetchall()
            headings = sqlite_cursor.execute('SELECT * FROM quota__headings').fetchall()
            commodities = sqlite_cursor.execute('SELECT * FROM quota__commodities').fetchall()

            assert len(quotas) == 1
            assert len(headings) == 1
            assert len(commodities) == 2
