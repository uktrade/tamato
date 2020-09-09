from django.contrib.auth.models import Permission
from pytest_bdd import given

from common.tests import factories
from common.tests.util import Dates
from workbaskets.validators import WorkflowStatus


@given("footnote NC000", target_fixture="footnote_NC000")
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


@given(
    'a valid user named "Bob" with permission to edit footnotes',
    target_fixture="user_bob",
)
def user_bob():
    bob = factories.UserFactory(username="Bob")
    bob.user_permissions.add(
        *list(
            Permission.objects.filter(
                content_type__app_label="footnotes",
                codename__in=[
                    "change_footnote",
                    "add_footnotedescription",
                    "change_footnotedescription",
                ],
            )
        )
    )
    return bob


@given("I am logged in as Bob", target_fixture="user_bob_login")
def user_bob_login(client, user_bob):
    client.force_login(user_bob)
