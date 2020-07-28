from pytest_bdd import given

from common.tests import factories
from common.tests.util import Dates
from workbaskets.models import WorkflowStatus


@given("footnote NC000")
def footnote_NC000():
    w = factories.WorkBasketFactory(status=WorkflowStatus.PUBLISHED)
    t = factories.FootnoteTypeFactory(footnote_type_id="NC", workbasket=w)
    f = factories.FootnoteFactory(
        footnote_id="000", footnote_type=t, valid_between=Dates.normal, workbasket=w
    )
    factories.FootnoteDescriptionFactory(
        described_footnote=f,
        description="This is NC000",
        valid_between=Dates.starts_with_normal,
        workbasket=w,
    )
    factories.FootnoteDescriptionFactory(
        described_footnote=f, valid_between=Dates.overlap_normal, workbasket=w
    )
    return f
