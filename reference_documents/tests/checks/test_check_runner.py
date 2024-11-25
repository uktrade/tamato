from datetime import date
from unittest.mock import patch

import pytest

from common.tests.factories import MeasureFactory
from common.tests.factories import MeasurementUnitFactory
from common.tests.factories import QuotaDefinitionFactory
from common.util import TaricDateRange
from reference_documents.check import check_runner
from reference_documents.check.base import BaseCheck
from reference_documents.check.base import BaseOrderNumberCheck
from reference_documents.check.base import BaseQuotaDefinitionCheck
from reference_documents.check.base import BaseQuotaSuspensionCheck
from reference_documents.check.ref_order_numbers import OrderNumberChecks  # noqa
from reference_documents.check.ref_quota_definitions import (  # noqa
    QuotaDefinitionChecks,
)
from reference_documents.check.ref_quota_suspensions import (  # noqa
    QuotaSuspensionChecks,
)
from reference_documents.check.ref_rates import RateChecks  # noqa
from reference_documents.models import AlignmentReportCheckStatus
from reference_documents.tests import factories

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
        area_id = "ZZ"

        # setup ref doc & version
        ref_doc_ver = factories.ReferenceDocumentVersionFactory.create(
            reference_document__area_id=area_id,
        )

        # setup rates
        factories.RefRateFactory.create(
            reference_document_version=ref_doc_ver,
            valid_between=valid_between,
        )

        # setup order number
        order_number = factories.RefOrderNumberFactory.create(
            reference_document_version=ref_doc_ver,
            valid_between=valid_between,
        )

        # setup quota definition
        quota_def = factories.RefQuotaDefinitionFactory.create(
            ref_order_number=order_number,
            valid_between=valid_between,
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
            valid_between=valid_between,
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
                description="Tonne",
            ),
        )

        # tap measure
        tap_measure = MeasureFactory.create(
            geographical_area__area_id=area_id,
            goods_nomenclature__item_id=quota_def.commodity_code,
            goods_nomenclature__suffix=80,
            goods_nomenclature__valid_between=TaricDateRange(date(2000, 1, 1)),
            measure_type__sid=143,
            order_number=tap_quota_definition.order_number,
        )

        return ref_doc_ver

    @patch(
        "reference_documents.check.ref_rates.RateChecks.run_check",
    )
    @patch(
        "reference_documents.check.ref_order_numbers.OrderNumberChecks.run_check",
    )
    @patch(
        "reference_documents.check.ref_quota_suspensions.QuotaSuspensionChecks.run_check",
    )
    @patch(
        "reference_documents.check.ref_quota_definitions.QuotaDefinitionChecks.run_check",
    )
    def test_run(
        self,
        rate_exists_check_patch,
        order_number_checks_patch,
        quota_suspension_exists_check_patch,
        quota_definition_exists_patch,
    ):
        def side_effect(*args, **kwargs):
            return AlignmentReportCheckStatus.PASS, ""

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

    def test_capture_check_result(self):
        ref_doc_ver = self.data_setup_for_test_run()
        target = self.target_class(ref_doc_ver)
        ref_rate = ref_doc_ver.ref_rates.first()

        result = target.capture_check_result(
            RateChecks(ref_rate),
            ref_rate=ref_rate,
            parent_has_failed_or_skipped_result=True,
        )
        assert result == AlignmentReportCheckStatus.SKIPPED

    def test_status_contains_failed_or_skipped(self):
        ref_doc_ver = self.data_setup_for_test_run()
        target = self.target_class(ref_doc_ver)

        statuses_with_skipped = [
            AlignmentReportCheckStatus.PASS,
            AlignmentReportCheckStatus.PASS,
            AlignmentReportCheckStatus.SKIPPED,
        ]

        statuses_with_failed = [
            AlignmentReportCheckStatus.PASS,
            AlignmentReportCheckStatus.PASS,
            AlignmentReportCheckStatus.FAIL,
        ]

        statuses_all_pass = [
            AlignmentReportCheckStatus.PASS,
            AlignmentReportCheckStatus.PASS,
        ]

        assert target.status_contains_failed_or_skipped(statuses_with_skipped) is True
        assert target.status_contains_failed_or_skipped(statuses_with_failed) is True
        assert target.status_contains_failed_or_skipped(statuses_all_pass) is False
