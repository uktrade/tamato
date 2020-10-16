from django.contrib.auth.models import Permission
from pytest_bdd import given

from common.tests import factories


@given("footnote NC000", target_fixture="footnote_NC000")
def footnote_NC000(approved_workbasket, date_ranges):
    footnote = factories.FootnoteFactory(
        footnote_id="000",
        footnote_type=factories.FootnoteTypeFactory(
            footnote_type_id="NC",
            valid_between=date_ranges.no_end,
            workbasket=approved_workbasket,
        ),
        valid_between=date_ranges.normal,
        workbasket=approved_workbasket,
        description__description="This is NC000",
        description__valid_between=date_ranges.starts_with_normal,
    )
    factories.FootnoteDescriptionFactory(
        described_footnote=footnote,
        valid_between=date_ranges.ends_with_normal,
        workbasket=approved_workbasket,
    )
    return footnote


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
