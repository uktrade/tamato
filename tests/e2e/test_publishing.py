from playwright.sync_api import expect


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
