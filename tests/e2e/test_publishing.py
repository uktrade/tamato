import re

from playwright.sync_api import expect


def test_pause_packaging_queue(unpaused_queue, page):
    page.goto("/publishing/packaging-queue/")

    page.get_by_role("button", name="Stop CDS queue").click()

    expect(page.get_by_role("heading", name="CDS queue paused")).to_be_visible()
    expect(page.get_by_text("Warning queue stopped")).to_be_visible()
    expect(page.get_by_role("button", name="Start CDS queue")).to_be_visible()


def test_unpause_packaging_queue(paused_queue, page):
    page.goto("/publishing/packaging-queue/")

    page.get_by_role("button", name="Start CDS queue").click()

    expect(page.get_by_role("heading", name="Workbaskets queue")).to_be_visible()
    expect(page.get_by_role("button", name="Stop CDS queue")).to_be_visible()


def test_send_to_packaging_queue(
    unpaused_queue,
    workbasket_ready_for_queue,
    page,
):
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

    page.wait_for_timeout(5000)
    page.goto("publishing/packaging-queue/")
    packaged_workbasket = page.get_by_role("row").filter(
        has_text=f"{workbasket_ready_for_queue.id}",
    )
    expect(packaged_workbasket).to_be_visible()
