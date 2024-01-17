import pytest
import datetime
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from common.tests import factories
from common.util import TaricDateRange
from reports.reports.expiring_quotas_with_no_definition_period import Report
from quotas.models import QuotaDefinition, QuotaBlocking, QuotaSuspension


@pytest.mark.django_db
class TestQuotasExpiringSoonReport:
    def test_find_quota_definitions_expiring_soon(self, quota_order_number):
        report = Report()
        expiring_quota_definition = factories.QuotaDefinitionFactory.create(
            order_number=quota_order_number,
            valid_between=TaricDateRange(
                datetime.datetime.today().date() + relativedelta(weeks=1),
                datetime.datetime.today().date() + relativedelta(weeks=2),
            ),
        )

        result = report.find_quota_definitions_expiring_soon()

        assert expiring_quota_definition in result

    def test_find_quotas_without_future_definition(self, quota_order_number):
        report = Report()
        expiring_quota_definition = factories.QuotaDefinitionFactory.create(
            order_number=quota_order_number,
            valid_between=TaricDateRange(
                datetime.datetime.today().date() + relativedelta(weeks=1),
                datetime.datetime.today().date() + relativedelta(weeks=2),
            ),
        )

        result = report.find_quotas_without_future_definition(
            [expiring_quota_definition]
        )

        assert expiring_quota_definition in result

    def test_find_quota_blocking_without_future_definition(self, quota_order_number):
        report = Report()
        expiring_quota_definition = factories.QuotaDefinitionFactory.create(
            order_number=quota_order_number,
            valid_between=TaricDateRange(
                datetime.datetime.today().date() + relativedelta(weeks=1),
                datetime.datetime.today().date() + relativedelta(weeks=2),
            ),
        )
        blocking = factories.QuotaBlockingFactory.create(
            quota_definition=expiring_quota_definition
        )

        result = report.find_quota_blocking_without_future_definition(
            [expiring_quota_definition]
        )

        assert expiring_quota_definition in result
        assert blocking in expiring_quota_definition.quotablocking_set.all()

    def test_find_quota_suspension_without_future_definition(self, quota_order_number):
        report = Report()
        expiring_quota_definition = factories.QuotaDefinitionFactory.create(
            order_number=quota_order_number,
            valid_between=TaricDateRange(
                datetime.datetime.today().date() + relativedelta(weeks=1),
                datetime.datetime.today().date() + relativedelta(weeks=2),
            ),
        )
        suspension = factories.QuotaSuspensionFactory.create(
            quota_definition=expiring_quota_definition
        )

        result = report.find_quota_suspension_without_future_definition(
            [expiring_quota_definition]
        )

        assert expiring_quota_definition in result
        assert suspension in expiring_quota_definition.quotasuspension_set.all()
