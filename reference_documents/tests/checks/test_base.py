from datetime import date, timedelta

import pytest

from commodities.models.dc import CommodityTreeSnapshot
from common.tests.factories import QuotaOrderNumberFactory, GeographicalAreaFactory, GoodsNomenclatureFactory, QuotaDefinitionFactory, MeasureFactory, QuotaAssociationFactory, QuotaSuspensionFactory, \
    SimpleGoodsNomenclatureFactory, GeographicalAreaDescriptionFactory
from common.util import TaricDateRange
from geo_areas.models import GeographicalAreaDescription
from quotas import validators
from reference_documents.check.base import BaseCheck, BaseQuotaDefinitionCheck, BaseOrderNumberCheck, BaseQuotaSuspensionCheck, BaseRateCheck
from reference_documents.models import AlignmentReportCheckStatus
from reference_documents.tests import factories

pytestmark = pytest.mark.django_db


@pytest.mark.reference_documents
class TestBaseCheck:
    def test_init(self):
        with pytest.raises(TypeError) as e:
            BaseCheck()
        assert "Can't instantiate abstract class BaseCheck with abstract method run_check" in str(e)

    def test_run_check(self):
        class Target(BaseCheck):
            def run_check(self) -> (AlignmentReportCheckStatus, str):
                super().run_check()

        target = Target()

        assert target.run_check() is None


@pytest.mark.reference_documents
class TestBaseQuotaDefinitionCheck:
    class Target(BaseQuotaDefinitionCheck):
        def run_check(self):
            pass

    def test_init(self):
        ref_quota_definition = factories.RefQuotaDefinitionFactory.create()
        target = self.Target(ref_quota_definition)
        assert target.dependent_on_passing_check is None
        assert target.ref_quota_definition == ref_quota_definition
        assert target.ref_order_number == ref_quota_definition.ref_order_number
        assert target.reference_document_version == ref_quota_definition.ref_order_number.reference_document_version
        assert target.reference_document == ref_quota_definition.ref_order_number.reference_document_version.reference_document

    def test_order_number_no_match(self):
        pref_quota = factories.RefQuotaDefinitionFactory.create()
        target = self.Target(pref_quota)
        assert target.tap_order_number() is None

    def test_order_number_match(self):
        tap_order_number = QuotaOrderNumberFactory.create()
        pref_quota = factories.RefQuotaDefinitionFactory.create(
            ref_order_number__order_number=tap_order_number.order_number,
            ref_order_number__valid_between=tap_order_number.valid_between,
        )
        target = self.Target(pref_quota)
        assert target.tap_order_number() == tap_order_number

    def test_geo_area_no_match(self):
        pref_quota = factories.RefQuotaDefinitionFactory.create()
        target = self.Target(pref_quota)
        assert target.geo_area() is None

    def test_geo_area_match(self):
        tap_geo_area = GeographicalAreaFactory.create()
        pref_quota = factories.RefQuotaDefinitionFactory.create(
            ref_order_number__reference_document_version__reference_document__area_id=tap_geo_area.area_id
        )
        target = self.Target(pref_quota)
        assert target.geo_area() == tap_geo_area

    def test_geo_area_description_match(self):
        tap_geo_area = GeographicalAreaFactory.create()
        pref_quota = factories.RefQuotaDefinitionFactory.create(
            ref_order_number__reference_document_version__reference_document__area_id=tap_geo_area.area_id
        )
        target = self.Target(pref_quota)

        description = (
            GeographicalAreaDescription.objects.latest_approved()
            .filter(described_geographicalarea=target.geo_area())
            .last()
        )

        assert target.geo_area_description() == description.description

    def test_geo_area_description_no_match(self):
        pref_quota = factories.RefQuotaDefinitionFactory.create(
            ref_order_number__reference_document_version__reference_document__area_id=''
        )
        target = self.Target(pref_quota)
        assert target.geo_area() is None

    def test_commodity_code_no_match(self):
        pref_quota = factories.RefQuotaDefinitionFactory.create()
        target = self.Target(pref_quota)
        assert target.commodity_code() is None

    def test_commodity_code_match(self):
        comm_code_start_date = date.today() + timedelta(days=-365)
        comm_code = GoodsNomenclatureFactory.create(
            valid_between=TaricDateRange(comm_code_start_date)
        )

        # quota definition needs to start on or after comm code start date
        pref_quota = factories.RefQuotaDefinitionFactory.create(
            commodity_code=comm_code.item_id,
            valid_between=TaricDateRange(comm_code_start_date + timedelta(days=200), comm_code_start_date + timedelta(days=300))
        )
        target = self.Target(pref_quota)
        assert target.commodity_code() == comm_code

    def test_commodity_code_exact_validity_match(self):
        comm_code_start_date = date.today() + timedelta(days=-365)
        comm_code_end_date = date.today() + timedelta(days=365)
        comm_code = GoodsNomenclatureFactory.create(
            valid_between=TaricDateRange(comm_code_start_date)
        )

        # quota definition needs to start on or after comm code start date
        pref_quota = factories.RefQuotaDefinitionFactory.create(
            commodity_code=comm_code.item_id,
            valid_between=TaricDateRange(comm_code_start_date, comm_code_end_date)
        )
        target = self.Target(pref_quota)
        assert target.commodity_code() == comm_code

    def test_commodity_code_no_match_validity_out_of_range(self):
        comm_code_start_date = date.today() + timedelta(days=-365)
        comm_code_end_date = date.today() + timedelta(days=-10)
        comm_code = GoodsNomenclatureFactory.create(
            valid_between=TaricDateRange(comm_code_start_date, comm_code_end_date)
        )

        # quota definition needs to start on or after comm code start date
        pref_quota = factories.RefQuotaDefinitionFactory.create(
            commodity_code=comm_code.item_id,
            valid_between=TaricDateRange(date.today(), date.today() + timedelta(days=10))
        )
        target = self.Target(pref_quota)
        assert target.commodity_code() is None

    def test_commodity_code_no_match_validity_intersecting_ranges(self):
        comm_code_start_date = date.today() + timedelta(days=-365)
        comm_code_end_date = date.today() + timedelta(days=-10)
        comm_code = GoodsNomenclatureFactory.create(
            valid_between=TaricDateRange(comm_code_start_date, comm_code_end_date)
        )

        # quota definition needs to start on or after comm code start date
        pref_quota = factories.RefQuotaDefinitionFactory.create(
            commodity_code=comm_code.item_id,
            valid_between=TaricDateRange(date.today() + timedelta(days=-100), date.today() + timedelta(days=10))
        )
        target = self.Target(pref_quota)
        assert target.commodity_code() is None

    def test_quota_definition_match(self):
        tap_quota_definition = QuotaDefinitionFactory.create(
            initial_volume=1200,
            valid_between=TaricDateRange(date.today(), date.today() + timedelta(days=10)),
            order_number__order_number='054123',
            order_number__valid_between=TaricDateRange(date.today() + timedelta(days=-1000)),
        )
        ref_quota_definition = factories.RefQuotaDefinitionFactory.create(
            ref_order_number__order_number=tap_quota_definition.order_number.order_number,
            ref_order_number__valid_between=TaricDateRange(date.today() + timedelta(days=-1000)),
            volume=tap_quota_definition.volume,
            valid_between=tap_quota_definition.valid_between,
        )
        target = self.Target(ref_quota_definition)
        assert target.ref_quota_definition.ref_order_number.order_number == tap_quota_definition.order_number.order_number
        assert target.ref_quota_definition.volume == tap_quota_definition.volume
        assert target.ref_quota_definition.valid_between == tap_quota_definition.valid_between
        assert target.quota_definition() == tap_quota_definition

    def test_quota_definition_no_match(self):
        tap_quota_definition = QuotaDefinitionFactory.create(
            initial_volume=1200,
            valid_between=TaricDateRange(date.today(), date.today() + timedelta(days=10)),
            order_number__order_number='054123',
            order_number__valid_between=TaricDateRange(date.today() + timedelta(days=-1000)),
        )
        ref_quota_definition = factories.RefQuotaDefinitionFactory.create(
            ref_order_number__order_number=tap_quota_definition.order_number.order_number,
            ref_order_number__valid_between=TaricDateRange(date.today() + timedelta(days=-1000)),
            volume=tap_quota_definition.initial_volume,
            valid_between=TaricDateRange(date.today() + timedelta(days=-100), date.today() + timedelta(days=-50)),
        )
        target = self.Target(ref_quota_definition)
        assert target.ref_quota_definition.valid_between != tap_quota_definition.valid_between
        assert target.quota_definition() is None

    def test_measures_match_single_measure(self):
        comm_code = '0101010101'

        tap_quota_definition = QuotaDefinitionFactory.create(
            initial_volume=1200,
            valid_between=TaricDateRange(date.today(), date.today() + timedelta(days=10)),
            order_number__order_number='054123',
            order_number__valid_between=TaricDateRange(date.today() + timedelta(days=-1000)),
        )
        ref_quota_definition = factories.RefQuotaDefinitionFactory.create(
            ref_order_number__order_number=tap_quota_definition.order_number.order_number,
            ref_order_number__valid_between=TaricDateRange(date.today() + timedelta(days=-1000)),
            volume=tap_quota_definition.initial_volume,
            valid_between=tap_quota_definition.valid_between,
            commodity_code=comm_code,
            ref_order_number__reference_document_version__reference_document__area_id=tap_quota_definition.order_number.origins.first().area_id
        )

        tap_measure = MeasureFactory.create(
            goods_nomenclature__item_id=comm_code,
            goods_nomenclature__valid_between=TaricDateRange(date.today() + timedelta(days=-100)),
            order_number=tap_quota_definition.order_number,
            valid_between=TaricDateRange(date.today(), date.today() + timedelta(days=10)),
            geographical_area=tap_quota_definition.order_number.origins.first(),
            measure_type__sid=143
        )

        target = self.Target(ref_quota_definition)

        assert tap_measure in target.measures()
        assert len(target.measures()) == 1

    def test_measures_match_multiple_measures(self):
        comm_code = '0101010101'

        tap_quota_definition = QuotaDefinitionFactory.create(
            initial_volume=1200,
            valid_between=TaricDateRange(date.today(), date.today() + timedelta(days=20)),
            order_number__order_number='054123',
            order_number__valid_between=TaricDateRange(date.today() + timedelta(days=-1000)),
        )

        ref_quota_definition = factories.RefQuotaDefinitionFactory.create(
            ref_order_number__order_number=tap_quota_definition.order_number.order_number,
            ref_order_number__valid_between=TaricDateRange(date.today() + timedelta(days=-1000)),
            volume=tap_quota_definition.initial_volume,
            valid_between=tap_quota_definition.valid_between,
            commodity_code=comm_code,
            ref_order_number__reference_document_version__reference_document__area_id=tap_quota_definition.order_number.origins.first().area_id
        )

        tap_measure_1 = MeasureFactory.create(
            goods_nomenclature__item_id=comm_code,
            goods_nomenclature__valid_between=TaricDateRange(date.today() + timedelta(days=-100)),
            order_number=tap_quota_definition.order_number,
            valid_between=TaricDateRange(date.today(), date.today() + timedelta(days=10)),
            geographical_area=tap_quota_definition.order_number.origins.first(),
            measure_type__sid=143
        )

        tap_measure_2 = MeasureFactory.create(
            goods_nomenclature=tap_measure_1.goods_nomenclature,
            order_number=tap_quota_definition.order_number,
            valid_between=TaricDateRange(date.today() + timedelta(days=11), date.today() + timedelta(days=20)),
            geographical_area=tap_measure_1.geographical_area,
            measure_type__sid=143
        )

        target = self.Target(ref_quota_definition)

        assert tap_measure_1 in target.measures()
        assert tap_measure_2 in target.measures()
        assert len(target.measures()) == 2

    @pytest.mark.parametrize("test_name, measure_date_ranges,expected_measure_count", [
        (
                "within quota definition validity",
                [{
                    "start": date.today() + timedelta(days=-5),
                    "end": date.today() + timedelta(days=5),
                }],
                1
        ),
        (
                "one in one out quota definition validity",
                [{
                    "start": date.today() + timedelta(days=-5),
                    "end": date.today() + timedelta(days=5),
                },
                    {
                        "start": date.today() + timedelta(days=-500),
                        "end": date.today() + timedelta(days=-490),
                    }
                ],
                1
        ),
        (
                "before start of quota definition validity end within",
                [{
                    "start": date.today() + timedelta(days=-500),
                    "end": date.today() + timedelta(days=5),
                }],
                1
        ),
        (
                "after end of quota definition validity start within",
                [{
                    "start": date.today() + timedelta(days=0),
                    "end": date.today() + timedelta(days=500),
                }],
                1
        ),
        (
                "before start and after end of quota definition",
                [{
                    "start": date.today() + timedelta(days=-500),
                    "end": date.today() + timedelta(days=500),
                }],
                1
        ),
        (
                "before start of quota definition",
                [{
                    "start": date.today() + timedelta(days=-500),
                    "end": date.today() + timedelta(days=-490),
                }],
                0
        ),
        (
                "after end of quota definition",
                [{
                    "start": date.today() + timedelta(days=500),
                    "end": date.today() + timedelta(days=510),
                }],
                0
        )
    ])
    def test_measures_return_values(self, test_name, measure_date_ranges, expected_measure_count):
        comm_code = '0101010101'

        quota_definition_validity = TaricDateRange(date.today() + timedelta(days=-10), date.today() + timedelta(days=10))

        tap_quota_definition = QuotaDefinitionFactory.create(
            initial_volume=1200,
            valid_between=quota_definition_validity,
            order_number__order_number='054123',
            order_number__valid_between=TaricDateRange(date.today() + timedelta(days=-1000)),
        )

        ref_quota_definition = factories.RefQuotaDefinitionFactory.create(
            ref_order_number__order_number=tap_quota_definition.order_number.order_number,
            ref_order_number__valid_between=TaricDateRange(date.today() + timedelta(days=-1000)),
            volume=tap_quota_definition.initial_volume,
            valid_between=quota_definition_validity,
            commodity_code=comm_code,
            ref_order_number__reference_document_version__reference_document__area_id=tap_quota_definition.order_number.origins.first().area_id
        )

        tap_comm_code = GoodsNomenclatureFactory.create(
            item_id=comm_code,
            valid_between=TaricDateRange(date.today() + timedelta(days=-100), date.today() + timedelta(days=100))
        )

        for date_range in measure_date_ranges:
            MeasureFactory.create(
                goods_nomenclature=tap_comm_code,
                order_number=tap_quota_definition.order_number,
                valid_between=TaricDateRange(date_range['start'], date_range['end']),
                geographical_area=tap_quota_definition.order_number.origins.first(),
                measure_type__sid=143
            )

        target = self.Target(ref_quota_definition)

        assert len(target.measures()) == expected_measure_count

    def test_association_exists_matches(self):
        ref_main_quota_definition = factories.RefQuotaDefinitionFactory.create(
            ref_order_number__valid_between=TaricDateRange(date(2022, 1, 1), date(2022, 12, 31)),
            valid_between=TaricDateRange(date(2022, 1, 1), date(2022, 6, 1))
        )

        ref_sub_quota_definition = factories.RefQuotaDefinitionFactory.create(
            ref_order_number__main_order_number=ref_main_quota_definition.ref_order_number,
            ref_order_number__coefficient=1.2,
            ref_order_number__relation_type=validators.SubQuotaType.EQUIVALENT,
            ref_order_number__valid_between=ref_main_quota_definition.ref_order_number.valid_between,
            valid_between=ref_main_quota_definition.valid_between
        )

        tap_main_quota_definition = QuotaDefinitionFactory.create(
            order_number__order_number=ref_main_quota_definition.ref_order_number.order_number,
            order_number__valid_between=ref_main_quota_definition.ref_order_number.valid_between,
            valid_between=ref_main_quota_definition.valid_between,
            volume=ref_main_quota_definition.volume,
        )

        tap_sub_quota_definition = QuotaDefinitionFactory.create(
            order_number__order_number=ref_sub_quota_definition.ref_order_number.order_number,
            order_number__valid_between=ref_sub_quota_definition.ref_order_number.valid_between,
            valid_between=ref_sub_quota_definition.valid_between,
            volume=ref_sub_quota_definition.volume,
        )

        QuotaAssociationFactory.create(
            main_quota=tap_main_quota_definition,
            sub_quota=tap_sub_quota_definition,
            sub_quota_relation_type=validators.SubQuotaType.EQUIVALENT,
            coefficient=1.2
        )

        target = self.Target(ref_sub_quota_definition)

        assert target.tap_association_exists()

    def test_association_exists_fails_main_order_number_does_not_exist(self):
        ref_main_quota_definition = factories.RefQuotaDefinitionFactory.create(
            ref_order_number__valid_between=TaricDateRange(date(2022, 1, 1), date(2022, 12, 31)),
            valid_between=TaricDateRange(date(2022, 1, 1), date(2022, 6, 1))
        )

        ref_sub_quota_definition = factories.RefQuotaDefinitionFactory.create(
            ref_order_number__main_order_number=ref_main_quota_definition.ref_order_number,
            ref_order_number__coefficient=1.2,
            ref_order_number__relation_type=validators.SubQuotaType.EQUIVALENT,
            ref_order_number__valid_between=ref_main_quota_definition.ref_order_number.valid_between,
            valid_between=ref_main_quota_definition.valid_between
        )

        target = self.Target(ref_sub_quota_definition)

        assert not target.tap_association_exists()

    def test_association_exists_fails_main_quota_definition_does_not_exist(self):
        ref_main_quota_definition = factories.RefQuotaDefinitionFactory.create(
            ref_order_number__valid_between=TaricDateRange(date(2022, 1, 1), date(2022, 12, 31)),
            valid_between=TaricDateRange(date(2022, 1, 1), date(2022, 6, 1))
        )

        ref_sub_quota_definition = factories.RefQuotaDefinitionFactory.create(
            ref_order_number__main_order_number=ref_main_quota_definition.ref_order_number,
            ref_order_number__coefficient=1.2,
            ref_order_number__relation_type=validators.SubQuotaType.EQUIVALENT,
            ref_order_number__valid_between=ref_main_quota_definition.ref_order_number.valid_between,
            valid_between=ref_main_quota_definition.valid_between
        )

        QuotaOrderNumberFactory.create(
            order_number=ref_main_quota_definition.ref_order_number.order_number,
            valid_between=ref_main_quota_definition.ref_order_number.valid_between,
        )

        QuotaDefinitionFactory.create(
            order_number__order_number=ref_sub_quota_definition.ref_order_number.order_number,
            order_number__valid_between=ref_sub_quota_definition.ref_order_number.valid_between,
            valid_between=ref_sub_quota_definition.valid_between,
            volume=ref_sub_quota_definition.volume,
        )

        target = self.Target(ref_sub_quota_definition)

        assert not target.tap_association_exists()

    def test_tap_association_exists_fails_association_does_not_exist(self):
        ref_main_quota_definition = factories.RefQuotaDefinitionFactory.create(
            ref_order_number__valid_between=TaricDateRange(date(2022, 1, 1), date(2022, 12, 31)),
            valid_between=TaricDateRange(date(2022, 1, 1), date(2022, 6, 1))
        )

        ref_sub_quota_definition = factories.RefQuotaDefinitionFactory.create(
            ref_order_number__main_order_number=ref_main_quota_definition.ref_order_number,
            ref_order_number__coefficient=1.2,
            ref_order_number__relation_type=validators.SubQuotaType.EQUIVALENT,
            ref_order_number__valid_between=ref_main_quota_definition.ref_order_number.valid_between,
            valid_between=ref_main_quota_definition.valid_between
        )

        QuotaDefinitionFactory.create(
            order_number__order_number=ref_main_quota_definition.ref_order_number.order_number,
            order_number__valid_between=ref_main_quota_definition.ref_order_number.valid_between,
            valid_between=ref_main_quota_definition.valid_between,
            volume=ref_main_quota_definition.volume,
        )

        QuotaDefinitionFactory.create(
            order_number__order_number=ref_sub_quota_definition.ref_order_number.order_number,
            order_number__valid_between=ref_sub_quota_definition.ref_order_number.valid_between,
            valid_between=ref_sub_quota_definition.valid_between,
            volume=ref_sub_quota_definition.volume,
        )

        target = self.Target(ref_sub_quota_definition)

        assert not target.tap_association_exists()

    def test_get_tap_association_exists_fails_order_number_does_not_have_main_order_number(self):
        ref_sub_quota_definition = factories.RefQuotaDefinitionFactory.create()
        target = self.Target(ref_sub_quota_definition)
        assert not target.get_tap_association()

    def test_check_coefficient_returns_true(self):

        ref_main_quota_definition = factories.RefQuotaDefinitionFactory.create(
            ref_order_number__valid_between=TaricDateRange(date(2022, 1, 1), date(2022, 12, 31)),
            valid_between=TaricDateRange(date(2022, 1, 1), date(2022, 6, 1))
        )

        ref_sub_quota_definition = factories.RefQuotaDefinitionFactory.create(
            ref_order_number__main_order_number=ref_main_quota_definition.ref_order_number,
            ref_order_number__coefficient=1.2,
            ref_order_number__relation_type=validators.SubQuotaType.EQUIVALENT,
            ref_order_number__valid_between=ref_main_quota_definition.ref_order_number.valid_between,
            valid_between=ref_main_quota_definition.valid_between
        )

        tap_main_quota_definition = QuotaDefinitionFactory.create(
            order_number__order_number=ref_main_quota_definition.ref_order_number.order_number,
            order_number__valid_between=ref_main_quota_definition.ref_order_number.valid_between,
            valid_between=ref_main_quota_definition.valid_between,
            volume=ref_main_quota_definition.volume,
        )

        tap_sub_quota_definition = QuotaDefinitionFactory.create(
            order_number__order_number=ref_sub_quota_definition.ref_order_number.order_number,
            order_number__valid_between=ref_sub_quota_definition.ref_order_number.valid_between,
            valid_between=ref_sub_quota_definition.valid_between,
            volume=ref_sub_quota_definition.volume,
        )

        QuotaAssociationFactory.create(
            main_quota=tap_main_quota_definition,
            sub_quota=tap_sub_quota_definition,
            sub_quota_relation_type=validators.SubQuotaType.EQUIVALENT,
            coefficient=1.2
        )

        target = self.Target(ref_sub_quota_definition)

        assert target.tap_association_exists()
        assert target.check_coefficient()

    def test_check_coefficient_returns_false_no_association(self):

        ref_sub_quota_definition = factories.RefQuotaDefinitionFactory.create()
        target = self.Target(ref_sub_quota_definition)
        assert not target.check_coefficient()

    @pytest.mark.parametrize("test_name, measure_date_ranges,expected_result", [
        (
                "measure within quota definition validity but not fully covered",
                [
                    {
                        "start": date.today() + timedelta(days=-5),
                        "end": date.today() + timedelta(days=5),
                    }
                ],
                False
        ),
        (
                "multiple measures within quota definition validity but not fully covered",
                [
                    {
                        "start": date.today() + timedelta(days=-5),
                        "end": date.today() + timedelta(days=5),
                    },
                    {
                        "start": date.today() + timedelta(days=7),
                        "end": date.today() + timedelta(days=12),
                    }
                ],
                False
        ),
        (
                "exact match",
                [{
                    "start": date.today() + timedelta(days=-10),
                    "end": date.today() + timedelta(days=10),
                }],
                True
        ),
        (
                "complete coverage but extends before and after",
                [
                    {
                        "start": date.today() + timedelta(days=-20),
                        "end": date.today() + timedelta(days=0),
                    },
                    {
                        "start": date.today() + timedelta(days=1),
                        "end": date.today() + timedelta(days=20),
                    }
                ],
                True
        ),
        (
                "covered but extends before",
                [{
                    "start": date.today() + timedelta(days=-20),
                    "end": date.today() + timedelta(days=10),
                }],
                True
        ),
        (
                "covered but extends after",
                [{
                    "start": date.today() + timedelta(days=-10),
                    "end": date.today() + timedelta(days=25),
                }],
                True
        ),
        (
                "not covered",
                [],
                False
        ),

    ])
    def test_measures_cover_quota_definition_validity_period(self, test_name, measure_date_ranges, expected_result):
        comm_code = '0101010101'

        quota_definition_validity = TaricDateRange(date.today() + timedelta(days=-10), date.today() + timedelta(days=10))

        tap_quota_definition = QuotaDefinitionFactory.create(
            initial_volume=1200,
            valid_between=quota_definition_validity,
            order_number__order_number='054123',
            order_number__valid_between=TaricDateRange(date.today() + timedelta(days=-1000)),
        )

        ref_quota_definition = factories.RefQuotaDefinitionFactory.create(
            ref_order_number__order_number=tap_quota_definition.order_number.order_number,
            ref_order_number__valid_between=TaricDateRange(date.today() + timedelta(days=-1000)),
            volume=tap_quota_definition.initial_volume,
            valid_between=quota_definition_validity,
            commodity_code=comm_code,
            ref_order_number__reference_document_version__reference_document__area_id=tap_quota_definition.order_number.origins.first().area_id
        )

        tap_comm_code = GoodsNomenclatureFactory.create(
            item_id=comm_code,
            valid_between=TaricDateRange(date.today() + timedelta(days=-100), date.today() + timedelta(days=100))
        )

        for date_range in measure_date_ranges:
            MeasureFactory.create(
                goods_nomenclature=tap_comm_code,
                order_number=tap_quota_definition.order_number,
                valid_between=TaricDateRange(date_range['start'], date_range['end']),
                geographical_area=tap_quota_definition.order_number.origins.first(),
                measure_type__sid=143
            )

        target = self.Target(ref_quota_definition)

        assert target.measures_cover_quota_definition_validity_period() == expected_result

    def test_is_sub_quota_true(self):
        ref_main_quota_definition = factories.RefQuotaDefinitionFactory.create(
            ref_order_number__valid_between=TaricDateRange(date(2022, 1, 1), date(2022, 12, 31)),
            valid_between=TaricDateRange(date(2022, 1, 1), date(2022, 6, 1))
        )

        ref_sub_quota_definition = factories.RefQuotaDefinitionFactory.create(
            ref_order_number__main_order_number=ref_main_quota_definition.ref_order_number,
            ref_order_number__coefficient=1.2,
            ref_order_number__relation_type=validators.SubQuotaType.EQUIVALENT,
            ref_order_number__valid_between=ref_main_quota_definition.ref_order_number.valid_between,
            valid_between=ref_main_quota_definition.valid_between
        )

        target = self.Target(ref_sub_quota_definition)

        assert target.is_sub_quota()


@pytest.mark.reference_documents
class TestBaseOrderNumberCheck:
    target_class = BaseOrderNumberCheck

    class Target(BaseOrderNumberCheck):
        def run_check(self):
            pass

    class TargetSubclass(BaseOrderNumberCheck):
        def run_check(self):
            return super().run_check()

    def test_init(self, ref_order_number=None):
        with pytest.raises(TypeError) as e:
            if not ref_order_number:
                ref_order_number = factories.RefOrderNumberFactory.create()
            self.target_class(ref_order_number)
        assert "Can't instantiate abstract class BaseOrderNumberCheck with abstract method run_check" in str(e)

    def test_run_check(self):
        ref_order_number = factories.RefOrderNumberFactory.create()
        target = self.TargetSubclass(ref_order_number)

        assert target.run_check() is None

    def test_tap_order_number_match(self):
        ref_order_number = factories.RefOrderNumberFactory.create()
        tap_order_number = QuotaOrderNumberFactory.create(
            order_number=ref_order_number.order_number,
            valid_between=ref_order_number.valid_between
        )

        target = self.TargetSubclass(ref_order_number)

        assert target.tap_order_number() == tap_order_number

    def test_tap_order_number_calls_super_if_provided(self):
        ref_order_number = factories.RefOrderNumberFactory.create()

        tap_order_number = QuotaOrderNumberFactory.create(
            order_number=ref_order_number.order_number,
            valid_between=ref_order_number.valid_between
        )

        target = self.TargetSubclass(ref_order_number)

        assert target.tap_order_number(ref_order_number.order_number) == tap_order_number


@pytest.mark.reference_documents
class TestBaseQuotaSuspensionCheck:
    target_class = BaseQuotaSuspensionCheck

    class Target(BaseQuotaSuspensionCheck):
        def run_check(self):
            pass

    class TargetSubclass(BaseQuotaSuspensionCheck):
        def run_check(self):
            return super().run_check()

    def test_init(self):
        ref_quota_suspension = factories.RefQuotaSuspensionFactory.create()
        target = self.Target(ref_quota_suspension)
        assert target.dependent_on_passing_check is None
        assert target.ref_quota_suspension == ref_quota_suspension

    def test_tap_quota_definition_matches(self):
        ref_quota_suspension = factories.RefQuotaSuspensionFactory.create(
            valid_between=TaricDateRange(date(2022, 1, 1), date(2022, 6, 1))
        )

        tap_quota_suspension = QuotaSuspensionFactory.create(
            quota_definition__order_number__order_number=ref_quota_suspension.ref_quota_definition.ref_order_number.order_number,
            quota_definition__order_number__valid_between=ref_quota_suspension.ref_quota_definition.ref_order_number.valid_between,
            quota_definition__valid_between=ref_quota_suspension.ref_quota_definition.valid_between,
            valid_between=ref_quota_suspension.valid_between,
        )

        target = self.Target(ref_quota_suspension)

        assert target.tap_quota_definition() == tap_quota_suspension.quota_definition

    def test_tap_quota_definition_does_not_match(self):
        ref_quota_suspension = factories.RefQuotaSuspensionFactory.create(
            valid_between=TaricDateRange(date(2022, 1, 1), date(2022, 6, 1))
        )

        target = self.Target(ref_quota_suspension)

        assert target.tap_quota_definition() is None

    def test_tap_order_number_matches(self):
        ref_quota_suspension = factories.RefQuotaSuspensionFactory.create(
            valid_between=TaricDateRange(date(2022, 1, 1), date(2022, 6, 1))
        )

        tap_quota_suspension = QuotaSuspensionFactory.create(
            quota_definition__order_number__order_number=ref_quota_suspension.ref_quota_definition.ref_order_number.order_number,
            quota_definition__order_number__valid_between=ref_quota_suspension.ref_quota_definition.ref_order_number.valid_between,
            quota_definition__valid_between=ref_quota_suspension.ref_quota_definition.valid_between,
            valid_between=ref_quota_suspension.valid_between,
        )

        target = self.Target(ref_quota_suspension)
        assert target.tap_order_number() == tap_quota_suspension.quota_definition.order_number

    def test_tap_order_number_matches_when_order_number_provided(self):
        ref_quota_suspension = factories.RefQuotaSuspensionFactory.create(
            valid_between=TaricDateRange(date(2022, 1, 1), date(2022, 6, 1))
        )

        tap_quota_suspension = QuotaSuspensionFactory.create(
            quota_definition__order_number__order_number=ref_quota_suspension.ref_quota_definition.ref_order_number.order_number,
            quota_definition__order_number__valid_between=ref_quota_suspension.ref_quota_definition.ref_order_number.valid_between,
            quota_definition__valid_between=ref_quota_suspension.ref_quota_definition.valid_between,
            valid_between=ref_quota_suspension.valid_between,
        )

        target = self.Target(ref_quota_suspension)
        assert target.tap_order_number(tap_quota_suspension.quota_definition.order_number.order_number) == tap_quota_suspension.quota_definition.order_number

    def test_tap_suspension_matches(self):
        ref_quota_suspension = factories.RefQuotaSuspensionFactory.create(
            valid_between=TaricDateRange(date(2022, 1, 1), date(2022, 6, 1))
        )

        tap_quota_suspension = QuotaSuspensionFactory.create(
            quota_definition__order_number__order_number=ref_quota_suspension.ref_quota_definition.ref_order_number.order_number,
            quota_definition__order_number__valid_between=ref_quota_suspension.ref_quota_definition.ref_order_number.valid_between,
            quota_definition__valid_between=ref_quota_suspension.ref_quota_definition.valid_between,
            valid_between=ref_quota_suspension.valid_between,
        )

        target = self.Target(ref_quota_suspension)
        assert target.tap_suspension() == tap_quota_suspension

    def test_tap_suspension_does_not_exist(self):
        ref_quota_suspension = factories.RefQuotaSuspensionFactory.create(
            valid_between=TaricDateRange(date(2022, 1, 1), date(2022, 6, 1))
        )

        QuotaDefinitionFactory.create(
            order_number__order_number=ref_quota_suspension.ref_quota_definition.ref_order_number.order_number,
            order_number__valid_between=ref_quota_suspension.ref_quota_definition.ref_order_number.valid_between,
            valid_between=ref_quota_suspension.ref_quota_definition.valid_between,
        )

        target = self.Target(ref_quota_suspension)
        assert target.tap_suspension() is None


@pytest.mark.reference_documents
class TestBaseRateCheck:
    target_class = BaseRateCheck

    class Target(BaseRateCheck):
        def run_check(self):
            pass

    class TargetSubclass(BaseRateCheck):
        def run_check(self):
            return super().run_check()

    def test_init(self):
        ref_rate = factories.RefRateFactory.create()
        target = self.Target(ref_rate)
        assert target.ref_rate == ref_rate

    def test_tap_comm_code_matches(self):
        ref_rate = factories.RefRateFactory.create()

        tap_comm_code = SimpleGoodsNomenclatureFactory.create(
            item_id=ref_rate.commodity_code,
            suffix=80,
            valid_between=TaricDateRange(
                ref_rate.valid_between.lower + timedelta(days=-200),
                ref_rate.valid_between.upper + timedelta(days=200)),
        )

        target = self.Target(ref_rate)
        assert target.tap_comm_code() == tap_comm_code

    def test_tap_comm_code_does_not_match_if_validity_out(self):
        ref_rate = factories.RefRateFactory.create()

        SimpleGoodsNomenclatureFactory.create(
            item_id=ref_rate.commodity_code,
            suffix=80,
            valid_between=TaricDateRange(
                ref_rate.valid_between.lower + timedelta(days=1),
                ref_rate.valid_between.upper + timedelta(days=-1)),
        )

        target = self.Target(ref_rate)
        assert target.tap_comm_code() is None

    def test_tap_geo_area_matches(self):
        ref_rate = factories.RefRateFactory.create()

        tap_geo_area = GeographicalAreaFactory.create(
            area_id=ref_rate.reference_document_version.reference_document.area_id
        )

        target = self.Target(ref_rate)
        assert target.tap_geo_area() == tap_geo_area

    def test_tap_geo_area_no_match(self):
        ref_rate = factories.RefRateFactory.create()

        target = self.Target(ref_rate)
        assert target.tap_geo_area() is None

    def test_tap_geo_area_description_exists(self):
        ref_rate = factories.RefRateFactory.create()

        tap_geo_area_description = GeographicalAreaDescriptionFactory.create(
            described_geographicalarea__area_id=ref_rate.reference_document_version.reference_document.area_id
        )

        target = self.Target(ref_rate)
        assert target.tap_geo_area_description() == tap_geo_area_description.description

    def test_tap_geo_area_description_does_not_exist(self):
        ref_rate = factories.RefRateFactory.create()

        target = self.Target(ref_rate)
        assert target.tap_geo_area_description() is None

    def test_ref_doc_version_eif_date_returns_ref_doc_ver_eif_date(self):
        eif_date = date(2022, 1, 1)
        ref_rate = factories.RefRateFactory.create(
            reference_document_version__entry_into_force_date=eif_date,
        )

        target = self.Target(ref_rate)

        assert target.ref_doc_version_eif_date() == eif_date

    def test_ref_doc_version_eif_date_returns_todays_date_if_no_eif(self):
        ref_rate = factories.RefRateFactory.create(
            reference_document_version__entry_into_force_date=None,
        )

        target = self.Target(ref_rate)

        assert target.ref_doc_version_eif_date() == date.today()

    def test_tap_related_measures_match_rate_comm_code(self):
        item_id = '0123456789'
        validity_range = TaricDateRange(date(2022, 1, 1), date(2022, 6, 1))

        tap_measure = MeasureFactory.create(
            measure_type__sid=142,
            valid_between=validity_range,
            goods_nomenclature__item_id=item_id,
            goods_nomenclature__valid_between=validity_range
        )

        ref_rate = factories.RefRateFactory.create(
            reference_document_version__entry_into_force_date=None,
            reference_document_version__reference_document__area_id=tap_measure.geographical_area.area_id,
            valid_between=validity_range,
            commodity_code=item_id
        )

        target = self.Target(ref_rate)

        assert tap_measure in target.tap_related_measures()
        assert len(target.tap_related_measures()) == 1
        assert len(target.tap_related_measures(item_id)) == 1
        assert len(target.tap_related_measures('9876543210')) == 0

    def test_tap_related_measures_when_comm_code_not_on_tap(self):
        ref_rate = factories.RefRateFactory.create(
            reference_document_version__entry_into_force_date=None,
        )

        target = self.Target(ref_rate)

        assert len(target.tap_related_measures()) == 0

    def test_get_snapshot_returns_commodity_snapshot(self):
        item_id = '0123450000'
        validity_range = TaricDateRange(date(2022, 1, 1), date(2022, 6, 1))

        tap_measure = MeasureFactory.create(
            measure_type__sid=142,
            valid_between=validity_range,
            goods_nomenclature__item_id=item_id,
            goods_nomenclature__valid_between=validity_range
        )

        ref_rate = factories.RefRateFactory.create(
            reference_document_version__entry_into_force_date=None,
            reference_document_version__reference_document__area_id=tap_measure.geographical_area.area_id,
            valid_between=validity_range,
            commodity_code=item_id
        )

        target = self.Target(ref_rate)

        # without item_id specified
        assert type(target.get_snapshot()) == CommodityTreeSnapshot
        assert len(target.get_snapshot().commodities) == 1
        assert target.get_snapshot().commodities[0].item_id == item_id

        assert type(target.get_snapshot(item_id)) == CommodityTreeSnapshot
        assert len(target.get_snapshot(item_id).commodities) == 1
        assert target.get_snapshot(item_id).commodities[0].item_id == item_id

    def test_get_snapshot_returns_none_when_comm_code_does_not_exist(self):
        ref_rate = factories.RefRateFactory.create(
            reference_document_version__entry_into_force_date=None,
        )

        target = self.Target(ref_rate)

        assert target.get_snapshot() is None

    @pytest.mark.parametrize("test_name, comm_code_structure, expected_result", [
        (
                "direct children covered",
                {
                    'item_id': '0101010000',
                    'add_measure': False,
                    'indent': 1,
                    'children': [
                        {
                            'item_id': '0101010100',
                            'add_measure': True,
                            'indent': 2,
                            'children': []
                        },
                        {
                            'item_id': '0101010200',
                            'add_measure': True,
                            'indent': 2,
                            'children': []
                        }
                    ]
                },
                True
        ),
        (
                "not covered",
                {
                    'item_id': '0101010000',
                    'add_measure': False,
                    'indent': 1,
                    'children': []
                },
                False
        ),
        (
                "mix, children and grandchildren covered",
                {
                    'item_id': '0101000000',
                    'add_measure': False,
                    'indent': 1,
                    'children': [
                        {
                            'item_id': '0101010000',
                            'add_measure': False,
                            'indent': 2,
                            'children': [
                                {
                                    'item_id': '0101010100',
                                    'add_measure': True,
                                    'indent': 3,
                                    'children': []
                                },
                                {
                                    'item_id': '0101010200',
                                    'add_measure': True,
                                    'indent': 3,
                                    'children': []
                                },
                            ]
                        },
                        {
                            'item_id': '0101020000',
                            'add_measure': True,
                            'indent': 2,
                            'children': []
                        }
                    ]
                },
                True
        ),
        (
                "mix partial grandchildren covered",
                {
                    'item_id': '0101000000',
                    'add_measure': False,
                    'indent': 1,
                    'children': [
                        {
                            'item_id': '0101010000',
                            'add_measure': False,
                            'indent': 2,
                            'children': [
                                {
                                    'item_id': '0101010100',
                                    'add_measure': False,
                                    'indent': 3,
                                    'children': []
                                },
                                {
                                    'item_id': '0101010200',
                                    'add_measure': True,
                                    'indent': 3,
                                    'children': []
                                },
                            ]
                        },
                        {
                            'item_id': '0101020000',
                            'add_measure': True,
                            'indent': 2,
                            'children': []
                        }
                    ]
                },
                False
        ),
        (
                "direct children covered, multiple measures",
                {
                    'item_id': '0101010000',
                    'add_measure': False,
                    'indent': 1,
                    'children': [
                        {
                            'item_id': '0101010100',
                            'add_measure': True,
                            'measure_count': 2,
                            'indent': 2,
                            'children': []
                        },
                        {
                            'item_id': '0101010200',
                            'add_measure': True,
                            'indent': 2,
                            'children': []
                        }
                    ]
                },
                True
        ),
    ])
    def test_tap_recursive_comm_code_check(self, test_name, comm_code_structure, expected_result):
        validity_range = TaricDateRange(date(2022, 1, 1), date(2022, 6, 1))

        tap_geo_area = GeographicalAreaFactory.create()

        ref_rate = factories.RefRateFactory.create(
            reference_document_version__entry_into_force_date=None,
            reference_document_version__reference_document__area_id=tap_geo_area.area_id,
            valid_between=validity_range,
            commodity_code=comm_code_structure['item_id']
        )

        def create_comm_code_and_measure_if_required(data, validity, geo_area):
            tap_comm_code = GoodsNomenclatureFactory(
                item_id=data['item_id'],
                suffix=80,
                indent__indent=data['indent'],
                valid_between=validity,
            )

            if data['add_measure']:
                measure_count = 1
                if 'measure_count' in data.keys():
                    measure_count = data['measure_count']

                for i in range(measure_count):
                    MeasureFactory.create(
                        measure_type__sid=142,
                        valid_between=validity,
                        goods_nomenclature=tap_comm_code,
                        geographical_area=geo_area
                    )

        def recurse_comm_code_structure(structure, validity, geo_area):
            create_comm_code_and_measure_if_required(structure, validity, geo_area)

            for child in structure['children']:
                if len(child['children']) > 0:
                    recurse_comm_code_structure(child, validity, geo_area)
                else:
                    create_comm_code_and_measure_if_required(child, validity, geo_area)

        recurse_comm_code_structure(comm_code_structure, validity_range, tap_geo_area)

        target = self.Target(ref_rate)
        assert target.tap_recursive_comm_code_check(target.get_snapshot(), comm_code_structure['item_id']) is expected_result
