from datetime import date, timedelta

import pytest

from commodities.models import GoodsNomenclature
from commodities.models.dc import CommodityTreeSnapshot, CommodityCollectionLoader, SnapshotMoment
from common.models import Transaction
from common.tests.factories import QuotaOrderNumberFactory, GeographicalAreaFactory, GoodsNomenclatureFactory, QuotaDefinitionFactory, MeasureFactory, QuotaAssociationFactory
from common.util import TaricDateRange
from geo_areas.models import GeographicalArea, GeographicalAreaDescription
from quotas import validators
from quotas.models import QuotaOrderNumber
from reference_documents.check.base import BaseCheck, BaseQuotaDefinitionCheck, BaseOrderNumberCheck
from reference_documents.models import RefRate, RefOrderNumber, AlignmentReportCheckStatus
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
            volume=tap_quota_definition.initial_volume,
            valid_between=tap_quota_definition.valid_between,
        )
        target = self.Target(ref_quota_definition)
        assert target.ref_quota_definition.ref_order_number.order_number == tap_quota_definition.order_number.order_number
        assert target.ref_quota_definition.volume == tap_quota_definition.initial_volume
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

    def test_check_measure_validity_no_match(self):

        ref_quota_definition = factories.RefQuotaDefinitionFactory.create(
            ref_order_number__valid_between=TaricDateRange(date.today() + timedelta(days=-1000)),
        )

        target = self.Target(ref_quota_definition)

        assert len(target.measures()) == 0
        assert target._check_measure_validity(target.measures()) == []

    def test_check_measure_validity_match_not_continuous(self):
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
            valid_between=TaricDateRange(date.today(), date.today() + timedelta(days=5)),
            geographical_area=tap_quota_definition.order_number.origins.first(),
            measure_type__sid=143
        )

        MeasureFactory.create(
            goods_nomenclature=tap_measure_1.goods_nomenclature,
            order_number=tap_quota_definition.order_number,
            valid_between=TaricDateRange(date.today() + timedelta(days=12), date.today() + timedelta(days=20)),
            geographical_area=tap_measure_1.geographical_area,
            measure_type__sid=143
        )

        target = self.Target(ref_quota_definition)

        assert target.measures() == []

    def test_check_measure_validity_match_outside_order_number_validity_range(self):
        comm_code = '0101010101'

        tap_quota_definition = QuotaDefinitionFactory.create(
            initial_volume=1200,
            valid_between=TaricDateRange(date.today(), date.today() + timedelta(days=20)),
            order_number__order_number='054123',
            order_number__valid_between=TaricDateRange(date.today(), date.today() + timedelta(days=5)),
        )

        ref_quota_definition = factories.RefQuotaDefinitionFactory.create(
            ref_order_number__order_number=tap_quota_definition.order_number.order_number,
            ref_order_number__valid_between=TaricDateRange(date.today() + timedelta(days=-1000)),
            volume=tap_quota_definition.initial_volume,
            valid_between=tap_quota_definition.valid_between,
            commodity_code=comm_code,
            ref_order_number__reference_document_version__reference_document__area_id=tap_quota_definition.order_number.origins.first().area_id
        )

        MeasureFactory.create(
            goods_nomenclature__item_id=comm_code,
            goods_nomenclature__valid_between=TaricDateRange(date.today() + timedelta(days=-100)),
            order_number=tap_quota_definition.order_number,
            valid_between=TaricDateRange(date.today(), date.today() + timedelta(days=20)),
            geographical_area=tap_quota_definition.order_number.origins.first(),
            measure_type__sid=143
        )

        target = self.Target(ref_quota_definition)

        assert target.measures() == []

    def test_main_quota_matches_matches(self):
        ref_main_quota_definition = factories.RefQuotaDefinitionFactory.create()

        ref_sub_quota_definition = factories.RefQuotaDefinitionFactory.create(
            ref_order_number__main_order_number=ref_main_quota_definition.ref_order_number,
            ref_order_number__coefficient=1.2,
            ref_order_number__relation_type=validators.SubQuotaType.EQUIVALENT
        )

        tap_main_quota_definition = QuotaDefinitionFactory.create(
            order_number__order_number=ref_main_quota_definition.ref_order_number.order_number,
            order_number__valid_between=ref_main_quota_definition.valid_between
        )

        tap_sub_quota_definition = QuotaDefinitionFactory.create(
            order_number__order_number=ref_sub_quota_definition.ref_order_number.order_number,
            order_number__valid_between=ref_sub_quota_definition.valid_between
        )

        tap_association = QuotaAssociationFactory.create(
            main_quota=tap_main_quota_definition,
            sub_quota=tap_sub_quota_definition,
            sub_quota_relation_type=validators.SubQuotaType.EQUIVALENT,
            coefficient=1.2
        )

        target = self.Target(ref_sub_quota_definition)

        assert target.association_exists()


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
        assert target.tap_order_number() == tap_order_number


