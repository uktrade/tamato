import re

from playwright.sync_api import expect


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
