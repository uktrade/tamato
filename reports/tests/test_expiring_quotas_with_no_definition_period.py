import pytest
import datetime
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from common.tests import factories
from common.util import TaricDateRange
from reports.reports.expiring_quotas_with_no_definition_period import Report
from quotas.models import QuotaDefinition


@pytest.fixture
def quota_order_number(db):
    return factories.QuotaOrderNumberFactory.create()


@pytest.fixture
def expired_quota_definition(quota_order_number):
    return factories.QuotaDefinitionFactory.create(
        order_number=quota_order_number,
        valid_between=TaricDateRange(
            datetime.datetime.today().date() + relativedelta(weeks=-2),
            datetime.datetime.today().date() + relativedelta(weeks=-1),
        ),
    )


@pytest.fixture
def expiring_soon_quota_definition(quota_order_number):
    return factories.QuotaDefinitionFactory.create(
        order_number=quota_order_number,
        valid_between=TaricDateRange(
            datetime.datetime.today().date() + relativedelta(weeks=1),
            datetime.datetime.today().date() + relativedelta(weeks=2),
        ),
    )


@pytest.fixture
def future_quota_definition(quota_order_number):
    return factories.QuotaDefinitionFactory.create(
        order_number=quota_order_number,
        valid_between=TaricDateRange(
            datetime.datetime.today().date() + relativedelta(weeks=3),
            datetime.datetime.today().date() + relativedelta(weeks=4),
        ),
    )


@pytest.mark.django_db
class TestQuotasExpiringSoonReport:
    def test_quotas_expiring_soon_report_logic(
        self,
        quota_order_number,
        expired_quota_definition,
        expiring_soon_quota_definition,
        future_quota_definition,
    ):
        report = Report()
        quotas = report.query()

        assert len(quotas) == 1

        assert future_quota_definition in quotas

        assert expiring_soon_quota_definition not in quotas

        assert expired_quota_definition not in quotas

    def test_quotas_expiring_soon_report_row(
        self, quota_order_number, expiring_soon_quota_definition
    ):
        report = Report()
        row_data = report.row(expiring_soon_quota_definition)

        assert len(row_data) == 3

        # Check if the correct columns are present
        assert {"text": expiring_soon_quota_definition.valid_between.lower} in row_data
        assert {"text": expiring_soon_quota_definition.valid_between.upper} in row_data
