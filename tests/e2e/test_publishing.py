import re

from playwright.sync_api import expect

from checks.tests.factories import TrackedModelCheckFactory
from common.tests import factories
from tasks.models import UserAssignment


def test_pause_packaging_queue(page, unpaused_queue):
    page.goto("/publishing/packaging-queue/")

    page.get_by_role("button", name="Stop CDS queue").click()

    expect(page.get_by_role("heading", name="CDS queue paused")).to_be_visible()
    expect(page.get_by_text("Warning queue stopped")).to_be_visible()
    expect(page.get_by_role("button", name="Start CDS queue")).to_be_visible()


def test_unpause_packaging_queue(page, paused_queue):
    page.goto("/publishing/packaging-queue/")

    page.get_by_role("button", name="Start CDS queue").click()

    expect(page.get_by_role("heading", name="Workbaskets queue")).to_be_visible()
    expect(page.get_by_role("button", name="Stop CDS queue")).to_be_visible()


def test_send_to_packaging_queue(
    page,
    empty_current_workbasket,
    unpaused_queue,
    celery_worker,
    settings,
):
    settings.ENABLE_PACKAGING_NOTIFICATIONS = False

    # Only fully assigned workbaskets can proceed through packaging queue
    factories.UserAssignmentFactory.create(
        assignment_type=UserAssignment.AssignmentType.WORKBASKET_WORKER,
        task__workbasket=empty_current_workbasket,
    )
    factories.UserAssignmentFactory.create(
        assignment_type=UserAssignment.AssignmentType.WORKBASKET_REVIEWER,
        task__workbasket=empty_current_workbasket,
    )

    # The workbasket must also have passed business rules check
    with empty_current_workbasket.new_transaction() as transaction:
        footnote = factories.FootnoteFactory.create(
            transaction=transaction,
            footnote_type__transaction=transaction,
        )
        TrackedModelCheckFactory.create(
            model=footnote,
            transaction_check__latest_tracked_model=footnote,
            transaction_check__transaction=footnote.transaction,
            successful=True,
        )

    page.goto("/workbaskets/current/checks/")
    page.get_by_role("link", name="Send to packaging queue").click()

    expect(page.get_by_role("heading", name="Send to packaging")).to_be_visible()

    page.get_by_label("Theme").fill("Test")
    page.get_by_label("Tops Jira").fill("www.example.org")
    page.get_by_role("button", name="Add to queue").click()

    expect(page).to_have_url(re.compile("publishing/.+/confirm-create/"))
    expect(
        page.get_by_role("heading", name="Workbasket queued at position"),
    ).to_be_visible()

    page.goto("publishing/packaging-queue/")
    page.wait_for_timeout(10000)
    page.reload()
    expect(page.locator('span:has-text("CDS NOTIFIED")')).to_be_visible()
