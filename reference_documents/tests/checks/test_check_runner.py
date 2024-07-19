from datetime import date

import pytest

from common.tests.factories import QuotaDefinitionFactory, MeasurementUnitFactory, MeasureFactory
from common.util import TaricDateRange
from reference_documents.check import check_runner
from reference_documents.check.base import BaseCheck, BaseQuotaDefinitionCheck, BaseOrderNumberCheck, BaseQuotaSuspensionCheck
from reference_documents.models import AlignmentReportCheckStatus
from reference_documents.tests import factories
from unittest import mock
from unittest.mock import patch
from reference_documents.check.ref_order_numbers import OrderNumberChecks  # noqa
from reference_documents.check.ref_quota_definitions import QuotaDefinitionExists  # noqa
from reference_documents.check.ref_quota_suspensions import QuotaSuspensionExists  # noqa
from reference_documents.check.ref_rates import RateExists  # noqa

pytestmark = pytest.mark.django_db


@pytest.mark.reference_documents
class TestChecks:
    target_class = check_runner.Checks

    def test_init(self):
        ref_doc_ver = factories.ReferenceDocumentVersionFactory.create()

        target = self.target_class(ref_doc_ver)

        assert target.reference_document_version == ref_doc_ver
        assert target.alignment_report is not None
        assert target.logger == check_runner.logger

    def test_get_checks_for(self):
        ref_doc_ver = factories.ReferenceDocumentVersionFactory.create()

        target = self.target_class(ref_doc_ver)

        assert len(target.get_checks_for(BaseCheck)) > 0
        assert len(target.get_checks_for(BaseQuotaDefinitionCheck)) > 0
        assert len(target.get_checks_for(BaseOrderNumberCheck)) > 0
        assert len(target.get_checks_for(BaseQuotaSuspensionCheck)) > 0

    def data_setup_for_test_run(self):
        valid_between = TaricDateRange(date(2020, 1, 1), date(2020, 12, 31))
        area_id = 'ZZ'

        # setup ref doc & version
        ref_doc_ver = factories.ReferenceDocumentVersionFactory.create(
            reference_document__area_id=area_id,
        )

        # setup rates
        factories.RefRateFactory.create(
            reference_document_version=ref_doc_ver,
            valid_between=valid_between
        )

        # setup order number
        order_number = factories.RefOrderNumberFactory.create(
            reference_document_version=ref_doc_ver,
            valid_between=valid_between
        )

        # setup quota definition
        quota_def = factories.RefQuotaDefinitionFactory.create(
            ref_order_number=order_number,
            valid_between=valid_between
        )

        # setup quota definition range
        quota_def_range = factories.RefQuotaDefinitionRangeFactory.create(
            ref_order_number=order_number,
            start_day=1,
            start_month=1,
            start_year=2020,
            end_day=31,
            end_month=12,
            end_year=2024,
        )

        # setup suspension
        factories.RefQuotaSuspensionFactory.create(
            ref_quota_definition=quota_def,
            valid_between=valid_between
        )

        # setup suspension range
        factories.RefQuotaSuspensionRangeFactory.create(
            ref_quota_definition_range=quota_def_range,
            start_day=1,
            start_month=3,
            start_year=2020,
            end_day=30,
            end_month=9,
            end_year=2024,
        )

        # setup TAP objects
        tap_quota_definition = QuotaDefinitionFactory.create(
            order_number__order_number=order_number.order_number,
            valid_between=valid_between,
            measurement_unit=MeasurementUnitFactory.create(
                description='Tonne'
            )
        )

        # tap measure
        tap_measure = MeasureFactory.create(
            geographical_area__area_id=area_id,
            goods_nomenclature__item_id=quota_def.commodity_code,
            goods_nomenclature__suffix=80,
            goods_nomenclature__valid_between=TaricDateRange(date(2000, 1, 1)),
            measure_type__sid=143,
            order_number=tap_quota_definition.order_number
        )

        return ref_doc_ver

    @patch(
        'reference_documents.check.ref_rates.RateExists.run_check',
    )
    @patch(
        'reference_documents.check.ref_order_numbers.OrderNumberChecks.run_check',
    )
    @patch(
        'reference_documents.check.ref_quota_suspensions.QuotaSuspensionExists.run_check',
    )
    @patch(
        'reference_documents.check.ref_quota_definitions.QuotaDefinitionExists.run_check',
    )
    def test_run(self, rate_exists_check_patch, order_number_checks_patch, quota_suspension_exists_check_patch, quota_definition_exists_patch):
        def side_effect(*args, **kwargs):
            return AlignmentReportCheckStatus.PASS, ''

        rate_exists_check_patch.side_effect = side_effect
        order_number_checks_patch.side_effect = side_effect
        quota_suspension_exists_check_patch.side_effect = side_effect
        quota_definition_exists_patch.side_effect = side_effect

        ref_doc_ver = self.data_setup_for_test_run()

        target = self.target_class(ref_doc_ver)
        target.run()

        assert rate_exists_check_patch.called
        assert order_number_checks_patch.called
        assert quota_suspension_exists_check_patch.called
        assert quota_definition_exists_patch.called

    @patch(
        'reference_documents.check.ref_rates.RateExists.run_check',
    )
    @patch(
        'reference_documents.check.ref_order_numbers.OrderNumberChecks.run_check',
    )
    @patch(
        'reference_documents.check.ref_quota_suspensions.QuotaSuspensionExists.run_check',
    )
    @patch(
        'reference_documents.check.ref_quota_definitions.QuotaDefinitionExists.run_check',
    )
    def test_run_does_not_call_if_parent_check_failed(
            self,
            rate_exists_check_patch,
            order_number_checks_patch,
            quota_suspension_exists_check_patch,
            quota_definition_exists_patch
    ):
        def mock_run_check_pass(*args, **kwargs):
            return AlignmentReportCheckStatus.PASS, ''

        def mock_run_check_fail(*args, **kwargs):
            return AlignmentReportCheckStatus.FAIL, ''

        rate_exists_check_patch.side_effect = mock_run_check_pass
        # order_number_checks_patch.side_effect = mock_run_check_fail
        # quota_suspension_exists_check_patch.side_effect = mock_run_check_pass
        # quota_definition_exists_patch.side_effect = mock_run_check_pass

        ref_doc_ver = self.data_setup_for_test_run()

        target = self.target_class(ref_doc_ver)
        target.run()

        assert rate_exists_check_patch.called
        assert order_number_checks_patch.called
        assert not quota_definition_exists_patch.called
        assert not quota_suspension_exists_check_patch.called

    @pytest.mark.skip(reason="test not implemented yet")
    def test_capture_check_result(self):
        pass
