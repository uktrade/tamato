from pytest_bdd import given

from common.tests import factories
from common.tests.util import Dates


@given("footnote NC000")
def footnote_NC000():
    t = factories.FootnoteTypeFactory(footnote_type_id="NC")
    f = factories.FootnoteFactory(footnote_id="000", footnote_type=t)
    factories.FootnoteDescriptionFactory(
        described_footnote=f,
        description="This is NC000",
        valid_between=Dates.starts_with_normal,
    )
    factories.FootnoteDescriptionFactory(
        described_footnote=f, valid_between=Dates.overlap_normal,
    )
    return f
