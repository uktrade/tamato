from datetime import date
from decimal import Decimal

import pytest

from common.tests.factories import QuotaOrderNumberFactory, QuotaDefinitionFactory, GoodsNomenclatureFactory, MeasureFactory, MeasureComponentFactory, MeasureConditionComponentFactory, MeasureConditionFactory, \
    MeasurementFactory, AdditionalCodeFactory, ApprovedTransactionFactory
from common.util import TaricDateRange
from reference_documents.check.base import BaseQuotaDefinitionCheck
from reference_documents.check.ref_order_numbers import OrderNumberChecks
from reference_documents.check.ref_quota_definitions import QuotaDefinitionExists
from reference_documents.models import AlignmentReportCheckStatus
from reference_documents.tests import factories

pytestmark = pytest.mark.django_db


@pytest.mark.reference_documents
class TestQuotaDefinitionExists:

    def test_run_check_passed(self):
        valid_between = TaricDateRange(date(2020, 1, 1), date(2020, 12, 31))
        area_id = 'ZZ'

        # setup ref doc & version
        ref_doc_ver = factories.ReferenceDocumentVersionFactory.create(
            reference_document__area_id=area_id,
        )

        # setup order number
        ref_quota_definition = factories.RefQuotaDefinitionFactory.create(
            ref_order_number__reference_document_version=ref_doc_ver,
            ref_order_number__valid_between=valid_between,
            valid_between=valid_between,
            duty_rate='2.500% + 37.800 EUR / 100 kg'
        )
        tap_approved_transaction = ApprovedTransactionFactory()

        # setup TAP objects
        tap_quota_definition = QuotaDefinitionFactory.create(
            order_number__order_number=ref_quota_definition.ref_order_number.order_number,
            valid_between=valid_between,
            order_number__valid_between=valid_between,
            transaction=tap_approved_transaction
        )

        tap_goods_nomenclature = GoodsNomenclatureFactory.create(
            item_id=ref_quota_definition.commodity_code,
            valid_between=valid_between,
            transaction=tap_approved_transaction
        )

        tap_measure = MeasureFactory.create(
            measure_type__sid=143,
            valid_between=valid_between,
            goods_nomenclature=tap_goods_nomenclature,
            order_number=tap_quota_definition.order_number,
            geographical_area__area_id=area_id,
            transaction=tap_approved_transaction
        )

        cond = MeasureConditionFactory.create(
            dependent_measure=tap_measure,
            condition_code__code="V",
            component_sequence_number=11,
            duty_amount=Decimal("0"),
            monetary_unit__code="EUR",
            condition_measurement=MeasurementFactory.create(
                measurement_unit__code="DTN",
                measurement_unit__abbreviation="100 kg",
                measurement_unit_qualifier=None,
            ),
            action__code="1",
            dependent_measure__additional_code=AdditionalCodeFactory.create(),
            transaction=tap_approved_transaction
        )
        MeasureConditionComponentFactory.create(
            condition=cond,
            duty_expression__sid=1,
            duty_expression__prefix="",
            duty_amount=Decimal("2.5"),
            monetary_unit=None,
            transaction=tap_approved_transaction
        )
        MeasureConditionComponentFactory.create(
            condition=cond,
            duty_expression__sid=4,
            duty_expression__prefix="+",
            duty_amount=Decimal("37.8"),
            monetary_unit__code="EUR",
            component_measurement=MeasurementFactory.create(
                measurement_unit__code="DTN",
                measurement_unit__abbreviation="100 kg",
                measurement_unit_qualifier=None,
            ),
            transaction=tap_approved_transaction
        )

        cond = (
            type(cond)
            .objects.latest_approved()
            .with_reference_price_string()
            .get(pk=cond.pk)
        )

        target = QuotaDefinitionExists(ref_quota_definition=ref_quota_definition)
        assert cond.duty_sentence == "2.500% + 37.800 EUR / 100 kg"
        assert target.run_check() == (AlignmentReportCheckStatus.PASS, '')

    def test_run_check_fails_no_measure(self):
        valid_between = TaricDateRange(date(2020, 1, 1), date(2020, 12, 31))
        area_id = 'ZZ'

        # setup ref doc & version
        ref_doc_ver = factories.ReferenceDocumentVersionFactory.create(
            reference_document__area_id=area_id,
        )

        # setup order number
        ref_quota_definition = factories.RefQuotaDefinitionFactory.create(
            ref_order_number__reference_document_version=ref_doc_ver,
            ref_order_number__valid_between=valid_between,
            valid_between=valid_between
        )

        # setup TAP objects
        tap_quota_definition = QuotaDefinitionFactory.create(
            order_number__order_number=ref_quota_definition.ref_order_number.order_number,
            valid_between=valid_between,
            order_number__valid_between=valid_between,
        )

        goods_nomenclature = GoodsNomenclatureFactory.create(
            item_id=ref_quota_definition.commodity_code,
            valid_between=valid_between,
        )

        target = QuotaDefinitionExists(ref_quota_definition=ref_quota_definition)
        assert target.run_check() == (AlignmentReportCheckStatus.FAIL, 'FAIL - measure(s) spanning whole quota definition period not found')

    def test_run_check_fails_no_quota_definition(self):
        valid_between = TaricDateRange(date(2020, 1, 1), date(2020, 12, 31))
        area_id = 'ZZ'

        # setup ref doc & version
        ref_doc_ver = factories.ReferenceDocumentVersionFactory.create(
            reference_document__area_id=area_id,
        )

        # setup order number
        ref_quota_definition = factories.RefQuotaDefinitionFactory.create(
            ref_order_number__reference_document_version=ref_doc_ver,
            ref_order_number__valid_between=valid_between,
            valid_between=valid_between
        )

        goods_nomenclature = GoodsNomenclatureFactory.create(
            item_id=ref_quota_definition.commodity_code,
            valid_between=valid_between,
        )

        target = QuotaDefinitionExists(ref_quota_definition=ref_quota_definition)
        assert target.run_check() == (AlignmentReportCheckStatus.FAIL, 'FAIL - quota definition not found')

    def test_run_check_fails_no_goods_nomenclature(self):
        valid_between = TaricDateRange(date(2020, 1, 1), date(2020, 12, 31))
        area_id = 'ZZ'

        # setup ref doc & version
        ref_doc_ver = factories.ReferenceDocumentVersionFactory.create(
            reference_document__area_id=area_id,
        )

        # setup order number
        ref_quota_definition = factories.RefQuotaDefinitionFactory.create(
            ref_order_number__reference_document_version=ref_doc_ver,
            ref_order_number__valid_between=valid_between,
            valid_between=valid_between
        )

        target = QuotaDefinitionExists(ref_quota_definition=ref_quota_definition)
        assert target.run_check() == (AlignmentReportCheckStatus.FAIL, 'FAIL - commodity code not found')

    def test_run_check_fail_duty_sentence(self):
        valid_between = TaricDateRange(date(2020, 1, 1), date(2020, 12, 31))
        area_id = 'ZZ'

        # setup ref doc & version
        ref_doc_ver = factories.ReferenceDocumentVersionFactory.create(
            reference_document__area_id=area_id,
        )

        # setup order number
        ref_quota_definition = factories.RefQuotaDefinitionFactory.create(
            ref_order_number__reference_document_version=ref_doc_ver,
            ref_order_number__valid_between=valid_between,
            valid_between=valid_between,
            duty_rate='wonky duty rate'
        )
        tap_approved_transaction = ApprovedTransactionFactory()

        tap_quota_definition = QuotaDefinitionFactory.create(
            order_number__order_number=ref_quota_definition.ref_order_number.order_number,
            valid_between=valid_between,
            order_number__valid_between=valid_between,
            transaction=tap_approved_transaction
        )

        tap_goods_nomenclature = GoodsNomenclatureFactory.create(
            item_id=ref_quota_definition.commodity_code,
            valid_between=valid_between,
            transaction=tap_approved_transaction
        )

        MeasureFactory.create(
            measure_type__sid=143,
            valid_between=valid_between,
            goods_nomenclature=tap_goods_nomenclature,
            order_number=tap_quota_definition.order_number,
            geographical_area__area_id=area_id,
            transaction=tap_approved_transaction
        )

        target = QuotaDefinitionExists(ref_quota_definition=ref_quota_definition)
        assert target.run_check() == (AlignmentReportCheckStatus.FAIL, 'FAIL - duty rate does not match, expected wonky duty rate to be in ()')