import re
from datetime import datetime

from playwright.sync_api import expect


def test_create_a_new_footnote(empty_current_workbasket, footnote_type, page):
    page.goto(f"/footnotes/create/")
    expect(page.get_by_role("heading", name="Create a new footnote")).to_be_visible()

    page.get_by_label("Footnote type").select_option(value=str(footnote_type.pk))
    page.get_by_role("group", name="Start date").get_by_label("Day").fill(
        str(datetime.today().day),
    )
    page.get_by_role("group", name="Start date").get_by_label("Month").fill(
        str(datetime.today().month),
    )
    page.get_by_role("group", name="Start date").get_by_label("Year").fill(
        str(datetime.today().year),
    )
    page.get_by_label("Description").fill("Test description.")
    page.get_by_role("button", name="Save").click()

    expect(page).to_have_url(re.compile("footnotes/.+/confirm-create/"))
    expect(page).to_have_title("Footnote created | Tariff Application Platform ")
