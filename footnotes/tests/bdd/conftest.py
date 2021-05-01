from pytest_bdd import given

from common.tests import factories


@given("footnote NC000", target_fixture="footnote_NC000")
def footnote_NC000(date_ranges, approved_transaction):
    footnote = factories.FootnoteFactory.create(
        footnote_id="000",
        footnote_type=factories.FootnoteTypeFactory.create(
            footnote_type_id="NC",
            valid_between=date_ranges.no_end,
            transaction=approved_transaction,
        ),
        valid_between=date_ranges.normal,
        transaction=approved_transaction,
        description__description="This is NC000",
        description__validity_start=date_ranges.starts_with_normal.lower,
    )
    factories.FootnoteDescriptionFactory.create(
        described_footnote=footnote,
        validity_start=date_ranges.ends_with_normal.lower,
        transaction=approved_transaction,
    )
    return footnote
