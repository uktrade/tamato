from django.contrib.auth.models import Permission
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
        description__valid_between=date_ranges.starts_with_normal,
    )
    factories.FootnoteDescriptionFactory.create(
        described_footnote=footnote,
        valid_between=date_ranges.ends_with_normal,
        transaction=approved_transaction,
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
