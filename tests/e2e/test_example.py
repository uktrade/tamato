import re

from playwright.sync_api import Page
from playwright.sync_api import expect


def test_show_sign_in_page(page: Page):
    page.goto("http://localhost:8000/")

    # Expect a title "to contain" a substring.
    expect(page).to_have_title(re.compile("Sign In | Tariff Application Platform "))


def test_sign_in_page(page: Page):
    page.goto("http://localhost:8000/")

    expect(page.get_by_text("Username")).to_be_attached()
    expect(page.get_by_text("Password")).to_be_attached()
