import re

from playwright.sync_api import expect

from common.tests.factories import FootnoteFactory


def test_create_a_new_workbasket(page):
    page.goto("/")
    page.get_by_role("link", name="Create a workbasket").click()

    expect(page).to_have_url(re.compile("/workbaskets/create/"))
    expect(page.get_by_role("heading", name="Create a new workbasket")).to_be_visible()

    page.get_by_label("TOPS/Jira number").fill("123")
    page.get_by_label("Description").fill("Test description.")
    page.get_by_role("button", name="Create").click()

    expect(page).to_have_url(re.compile("workbaskets/.+/confirm-create/"))
    expect(page.get_by_text("You have created a new workbasket")).to_be_visible()


def test_assign_worker_to_workbasket(page, user, empty_current_workbasket):
    page.goto("/workbaskets/current/")

    page.get_by_role("link", name="Assign workers").click()

    page.get_by_label("Assign user").fill(user.get_displayname())
    page.get_by_role("option", name=user.get_displayname()).click()
    page.get_by_role("button", name="Save").click()

    expect(page).to_have_url("/workbaskets/current/")
    expect(page.get_by_text(f"{user.get_displayname()}")).to_be_visible()


def test_assign_reviewer_to_workbasket(page, user, empty_current_workbasket):
    page.goto("/workbaskets/current/")

    page.get_by_role("link", name="Assign reviewers").click()

    page.get_by_label("Assign user").fill(user.get_displayname())
    page.get_by_role("option", name=user.get_displayname()).click()
    page.get_by_role("button", name="Save").click()

    expect(page).to_have_url("/workbaskets/current/")
    expect(page.get_by_text(f"{user.get_displayname()}")).to_be_visible()


def test_run_business_rules_on_workbasket(
    page,
    empty_current_workbasket,
    celery_worker,
):
    FootnoteFactory.create(transaction__workbasket=empty_current_workbasket)

    page.goto("/workbaskets/current/checks/")
    expect(page.get_by_text("Business rule check has not been run")).to_be_visible()

    page.get_by_role("button", name="Run business rules").click()
    page.reload()

    expect(page.get_by_text("Rule check in progress.")).to_be_visible()
    expect(page.get_by_role("button", name="Stop rule check")).to_be_visible()

    page.wait_for_timeout(10000)
    page.reload()
    expect(page.get_by_role("button", name="Send to packaging queue")).to_be_visible()
