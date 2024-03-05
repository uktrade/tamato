import datetime

import pytest

from common.models.utils import override_current_transaction
from common.tests import factories
from common.util import TaricDateRange
from geo_areas.validators import AreaCode
from measures.models import Measure
from quotas.models import QuotaOrderNumberOriginExclusion
from reports.reports.quotas_cannot_be_used import Report


@pytest.fixture
def quota_order_number(db):
    return factories.QuotaOrderNumberFactory.create()


@pytest.fixture
def country1(date_ranges):
    return factories.GeographicalAreaFactory.create(
        area_code=AreaCode.COUNTRY,
        valid_between=date_ranges.no_end,
    )


class TestQuotasCannotBeUsedReport:
    @pytest.mark.parametrize(
        "test_input",
        [
            "test_quotas_without_definitions_appear_in_report",
            "test_quota_definitions_with_no_end_date_appear_in_report",
            "test_quotas_without_measures_appear_in_report",
            "test_quotas_with_measure_with_matching_exclusion_do_not_appear_in_report",
            "test_quotas_with_measures_without_matching_exclusion_appear_in_report",
        ],
    )
    def test_quotas_report_logic(
        self,
        test_input,
        quota_order_number,
        approved_transaction,
        country1,
        date_ranges,
    ):
        test_function = getattr(self, test_input)
        test_function(quota_order_number, approved_transaction, country1, date_ranges)

    def test_quotas_without_definitions_appear_in_report(
        self,
        quota_order_number,
        approved_transaction,
        country1,
        date_ranges,
    ):
        with override_current_transaction(approved_transaction):
            assert quota_order_number.definitions.current().count() == 0

        assert len(Report().query()) == 1
        assert Report().query()[0].reason == "Definition period has not been set"

    def test_quota_definitions_with_no_end_date_appear_in_report(
        self,
        quota_order_number,
        approved_transaction,
        country1,
        date_ranges,
    ):
        quota_definition = factories.QuotaDefinitionFactory.create(
            order_number=quota_order_number,
            transaction=approved_transaction,
        )
        assert quota_definition.valid_between.upper is None

        with override_current_transaction(approved_transaction):
            assert quota_order_number.definitions.current().count() == 1

        assert len(Report().query()) == 1

    def test_quotas_without_measures_appear_in_report(
        self,
        quota_order_number,
        approved_transaction,
        country1,
        date_ranges,
    ):
        quota_order_number.valid_between = TaricDateRange(
            datetime.date.today(),
            datetime.date.today(),
        )
        assert quota_order_number.valid_between.upper == datetime.date.today()

        quota_definition = factories.QuotaDefinitionFactory.create(
            order_number=quota_order_number,
            transaction=approved_transaction,
        )
        quota_definition.valid_between = TaricDateRange(
            datetime.date.today(),
            datetime.date.today(),
        )
        assert quota_definition.valid_between.upper == datetime.date.today()

        with override_current_transaction(approved_transaction):
            assert quota_order_number.definitions.current().count() == 1
            assert (
                not Measure.objects.latest_approved()
                .filter(order_number=quota_order_number.order_number)
                .exists()
            )

        assert len(Report().query()) == 1

    def test_quotas_with_measure_with_matching_exclusion_do_not_appear_in_report(
        self,
        quota_order_number,
        approved_transaction,
        country1,
        date_ranges,
    ):
        with override_current_transaction(approved_transaction):
            quota_order_number.valid_between = date_ranges.normal
            factories.QuotaDefinitionFactory.create(
                order_number=quota_order_number,
                transaction=approved_transaction,
                valid_between=date_ranges.normal,
            )

            geo_group = factories.GeographicalAreaFactory.create(area_id="BAAA")
            origin = factories.QuotaOrderNumberOriginFactory.create(
                order_number=quota_order_number,
                transaction=approved_transaction,
                geographical_area=geo_group,
                valid_between=TaricDateRange(
                    datetime.date.today(),
                    datetime.date.today(),
                ),
            )
            factories.QuotaOrderNumberOriginExclusionFactory.create(
                transaction=approved_transaction,
                excluded_geographical_area=country1,
                origin=origin,
            )

            geo_membership_no_end_date = factories.GeographicalMembershipFactory.create(
                valid_between=TaricDateRange(
                    datetime.date.today(),
                    datetime.date.today(),
                ),
                geo_group=geo_group,
                member=country1,
            )

            measure = factories.MeasureFactory.create(
                order_number=quota_order_number,
                valid_between=TaricDateRange(
                    datetime.date.today(),
                    datetime.date.today(),
                ),
                geographical_area=geo_group,
            )

            geographical_area = factories.MeasureExcludedGeographicalAreaFactory.create(
                modified_measure=measure,
                excluded_geographical_area=geo_membership_no_end_date.member,
                # modified_measure__valid_between=TaricDateRange(datetime.date.today(), datetime.date.today()),
            )

            factories.QuotaOrderNumberOriginFactory.create(
                order_number=measure.order_number,
                valid_between=TaricDateRange(
                    datetime.date.today(),
                    datetime.date.today(),
                ),
            )
            assert quota_order_number.definitions.current().count() == 1

            assert (
                Measure.objects.latest_approved()
                .filter(order_number=quota_order_number)
                .count()
                == 1
            )

            retrieved_geo_exclusion = (
                QuotaOrderNumberOriginExclusion.objects.latest_approved().get(
                    origin_id=origin.pk,
                )
            )
            assert (
                retrieved_geo_exclusion.excluded_geographical_area
                == geographical_area.excluded_geographical_area
            )

        assert len(Report().query()) == 0

    def test_quotas_with_measures_without_matching_exclusion_appear_in_report(
        self,
        quota_order_number,
        approved_transaction,
        country1,
        date_ranges,
    ):
        with override_current_transaction(approved_transaction):
            quota_order_number.valid_between = date_ranges.normal
            factories.QuotaDefinitionFactory.create(
                order_number=quota_order_number,
                transaction=approved_transaction,
                valid_between=date_ranges.normal,
            )

            geo_group = factories.GeographicalAreaFactory.create(area_id="BAAA")
            origin = factories.QuotaOrderNumberOriginFactory.create(
                order_number=quota_order_number,
                transaction=approved_transaction,
                geographical_area=geo_group,
                valid_between=TaricDateRange(
                    datetime.date.today(),
                    datetime.date.today(),
                ),
            )
            factories.QuotaOrderNumberOriginExclusionFactory.create(
                transaction=approved_transaction,
                origin=origin,
            )

            geo_membership_no_end_date = factories.GeographicalMembershipFactory.create(
                valid_between=TaricDateRange(
                    datetime.date.today(),
                    datetime.date.today(),
                ),
                geo_group=geo_group,
                member=country1,
            )

            measure = factories.MeasureFactory.create(
                order_number=quota_order_number,
                valid_between=TaricDateRange(
                    datetime.date.today(),
                    datetime.date.today(),
                ),
                geographical_area=geo_group,
            )

            geographical_area = factories.MeasureExcludedGeographicalAreaFactory.create(
                modified_measure=measure,
                excluded_geographical_area=geo_membership_no_end_date.member,
                # modified_measure__valid_between=TaricDateRange(datetime.date.today(), datetime.date.today()),
            )

            factories.QuotaOrderNumberOriginFactory.create(
                order_number=measure.order_number,
                valid_between=TaricDateRange(
                    datetime.date.today(),
                    datetime.date.today(),
                ),
            )
            assert quota_order_number.definitions.current().count() == 1

            assert (
                Measure.objects.latest_approved()
                .filter(order_number=quota_order_number)
                .count()
                == 1
            )

            retrieved_geo_exclusion = (
                QuotaOrderNumberOriginExclusion.objects.latest_approved().get(
                    origin_id=origin.pk,
                )
            )
            assert (
                retrieved_geo_exclusion.excluded_geographical_area
                != geographical_area.excluded_geographical_area
            )

            assert len(Report().query()) == 1
            assert (
                Report().query()[0].reason
                == "Geographical area/exclusions data does not have any measures with matching data"
            )
