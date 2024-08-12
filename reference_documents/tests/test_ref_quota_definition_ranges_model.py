from datetime import date

import pytest

from common.util import TaricDateRange
from reference_documents.models import RefQuotaDefinition, ReferenceDocumentVersionStatus, RefQuotaDefinitionRange
from reference_documents.tests import factories

pytestmark = pytest.mark.django_db


@pytest.mark.reference_documents
class TestRefQuotaDefinitionRange:
    def test_init(self):
        target = RefQuotaDefinitionRange()

        assert target.ref_order_number is None
        assert target.commodity_code == ""

        assert target.start_day is None
        assert target.start_month is None
        assert target.start_year is None
        assert target.end_day is None
        assert target.end_month is None
        assert target.end_year is None

    def test_state_not_editable_prevents_save(self):
        target = factories.RefQuotaDefinitionRangeFactory(initial_volume=123)
        rdv = target.ref_order_number.reference_document_version

        assert rdv.status == ReferenceDocumentVersionStatus.EDITING
        assert rdv.editable()

        rdv.in_review()
        rdv.save(force_save=True)

        target.save()
        target.initial_volume = 123123
        target.refresh_from_db()

        rdv.published()
        rdv.save(force_save=True)

        target.initial_volume = 1231234
        target.save()

        target.refresh_from_db()

        assert rdv.status == ReferenceDocumentVersionStatus.PUBLISHED
        assert not rdv.editable()
        assert float(target.initial_volume) == float(123)

    def test__str__(self):
        target = factories.RefQuotaDefinitionRangeFactory()

        from_str = f'{target.start_day}/{target.start_month}'
        to_str = f'{target.end_day}/{target.end_month}'
        year_range = f'{target.start_year} - {target.end_year}'

        target_str = f"{target.ref_order_number.order_number} ({target.commodity_code}) yearly range: {from_str} : {to_str} for {year_range} {target.initial_volume} {target.measurement}, increment : {target.yearly_volume_increment}"

        assert str(target) == target_str

    def test_date_ranges(self):
        target = factories.RefQuotaDefinitionRangeFactory(
            start_day=1,
            start_month=1,
            start_year=2020,
            end_day=31,
            end_month=12,
            end_year=2024
        )

        rqdr_date_ranges = target.date_ranges()

        assert len(rqdr_date_ranges) == 5
        assert rqdr_date_ranges[0] == TaricDateRange(date(2020, 1, 1), date(2020, 12, 31))

    def test_date_ranges_no_end_date(self):
        target = factories.RefQuotaDefinitionRangeFactory(
            start_day=1,
            start_month=1,
            start_year=2020,
            end_day=31,
            end_month=12,
            end_year=None
        )

        rqdr_date_ranges = target.date_ranges()

        assert len(rqdr_date_ranges) == 8
        assert rqdr_date_ranges[0] == TaricDateRange(date(2020, 1, 1), date(2020, 12, 31))
